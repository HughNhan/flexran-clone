#!/usr/bin/env python3
"""
Wrapper to read data from dpdk application console
"""
import os
import re
import sys
import time
from kubernetes import config
from kubernetes.client import Configuration
from kubernetes.client.api import core_v1_api
from kubernetes.client.rest import ApiException
from kubernetes.stream import stream


class ConsoleWapper:
    def __init__(self, api: core_v1_api, pod_name, namespace, exec_cmd, prompt):
        self.prompt = prompt
        self.handle = stream(api.connect_get_namespaced_pod_exec,
                             pod_name,
                             namespace,
                             command=exec_cmd,
                             stderr=True, stdin=True,
                             stdout=True, tty=True,
                             _preload_content=False)
        self.wait_for_prompt(None, 10)

    def run_cmd(self, cmd):
        """
        run cmd inside the dpdk app console,
        expect prompt after the app execute the cmd
        return value: std_out string
        """
        self.handle.write_stdin(cmd + "\n")
        return self.wait_for_prompt(cmd, 3)


    def wait_for_prompt(self, anchor, timeout):
        output = ""
        retry = 0
        count = 0
        while self.handle.is_open():
            if count > timeout:
                if retry == 0:
                    retry = 1
                    count = 0
                    self.handle.write_stdin("\n")
                    continue
                self.close()
                sys.exit("Failed to get prompt %s\n" %self.prompt)
            self.handle.update(timeout=1)
            if self.handle.peek_stdout():
                buf = self.handle.read_stdout()
                output += buf
                print("STDOUT: %s" %buf)
                if (anchor is None and self.prompt in output) or \
                   (anchor is not None and re.search(re.escape(anchor) + r'[\s\S]*' + re.escape(self.prompt), output)):
                    return output
            count += 1
            time.sleep(1)

    def close(self):
        time.sleep(1)
        self.handle.close()


class EthTool(ConsoleWapper):
    def __init__(self, api, pod_name, namespace):
        allowed_cpu_list = None
        resp = stream(api.connect_get_namespaced_pod_exec,
               pod_name,
               namespace,
               command=['/bin/sh', '-c', 'cat /proc/self/status | grep Cpus_allowed_list'],
               stderr=True, stdin=False,
               stdout=True, tty=True)
        match = re.search(r"Cpus_allowed_list:\s*(\S+)", resp)
        if match:
            allowed_cpu_list = match.group(1)
        if allowed_cpu_list is None:
            sys.exit("Failed to get the cpu list to run the dpdk application!")   
        #allowed_cpu_list = "1-3,41-43"
        super().__init__(api, pod_name,
                         namespace, ["dpdk-ethtool", "-l", allowed_cpu_list], "EthApp>")

    # return a dict, key: pci address, val: (portnum, mac address) tuple
    def get_pci_mac_map(self):
        """
        EthApp> drvinfo
        Port 0 driver: net_i40e (ver: DPDK 20.11.4-rc1)
        firmware-version: 6.01 0x800036de 1.1861.0
        bus-info: 0000:af:00.0
        EthApp> macaddr 0
        Port 0 MAC Address: ac:1f:6b:a5:93:a6
        EthApp> 
        """
        drvinfo = self.run_cmd("drvinfo")
        port_list = re.findall(r"Port (\d)", drvinfo)
        pci_list = re.findall(r"bus-info: (\S+)", drvinfo)
        print("port_list: %s; pci_list: %s\n" %(','.join(map(str, port_list)), ','.join(map(str, pci_list))))
        if len(port_list) != len(pci_list):
            self.close()
            sys.exit(1)
        pci_mac_map = {}
        for port_pci_tuple in zip(port_list, pci_list):
            print("port_pci_tuple: %s\n" %(','.join(map(str, port_pci_tuple))))
            macinfo = self.run_cmd("macaddr %s" %port_pci_tuple[0])
            try:
                mac = re.findall(r'MAC Address: (\S+)', macinfo)[0]
                pci_mac_map[port_pci_tuple[1]] = (port_pci_tuple[0], mac)
            except Exception as e:
                err_str = "Failed to find mac address from macinfo: %s" %macinfo
                print(err_str)
                raise Exception(err_str) from e
        return pci_mac_map

    # input: execpted pci:mac dictionary
    def set_pci_mac(self, pci_mac_setting):
        pci_map = self.get_pci_mac_map()
        for pci, mac in pci_mac_setting.items():
            try:
                port, current_mac = pci_map[pci]
            except Exception as e:
                err_str = "%s not found" %pci
                print(err_str)
                raise Exception(err_str) from e
            if current_mac != mac:
                self.run_cmd("macaddr %s %s" %(port, mac))

    def close(self):
        self.run_cmd("quit")
        time.sleep(1)
        super().close()

def get_pod_env_variable(api, pod_name: str, namespace: str, env_var: str) -> str:
    resp = stream(api.connect_get_namespaced_pod_exec,
               pod_name,
               namespace,
               command=['printenv', env_var],
               stderr=True, stdin=False,
               stdout=True, tty=True)
    return resp

if __name__ == '__main__':
    """
    The following test code requires:
    pod named 'dpdk' is already running in default namespace
     at least one ethernet port already bound to dpdk deriver, either vfio or uio
    """
    parser = argparse.ArgumentParser(
        description='Update dpdk port mac address on pod.')
    parser.add_argument('-p', '--pod', metavar='pod', type=str,
        required=True,
        help='the name of the pod')
    parser.add_argument('-namespace', '--namespace', type=str,
        required=False, default='default',
        help='the namespace of the pod')
    parser.add_argument('-mac', '--mac', type=str,
        required=False, default='00:11:22:33:00:00,00:11:22:33:00:10'
        help='comma seperated mac addresses')
    args = parser.parse_args()
    maclist = args.mac.split(',')
    for mac in maclist:
        if not re.match(r'([\da-fA-F]{2}:){2}[\da-fA-F]{2}', mac):
            sys.exit("invalid mac address: %s" % mac)

    config.load_kube_config()
    try:
        c = Configuration().get_default_copy()
    except AttributeError:
        c = Configuration()
        c.assert_hostname = False
    Configuration.set_default(c)
    core_v1 = core_v1_api.CoreV1Api()
    pci_list = get_pod_env_variable(core_v1, args.pod, args.namespace, 'PCIDEVICE_OPENSHIFT_IO_INTELNICS0').split(',')
    if len(pci_list) != len(maclist):
        sys.exit("The number of mac address and VF is different")
    try:
       pod_ethtool = EthTool(core_v1, args.pod, args.namespace)
       for i, mac in enumerate(maclist):
           pci_mac = {pci_list[i]: mac}
           pod_ethtool.set_pci_mac(pci_mac)
       pci_mac_map = pod_ethtool.get_pci_mac_map()
       print(pci_mac_map)
    except:
       print("failed to handle the dpdk app")
       retval = 1
    else:
       retval = 0
    finally:
       pod_ethtool.close()
    sys.exit(retval)
