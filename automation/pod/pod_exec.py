"""
Exec flexran test suite in a flexran container
"""

import sys
import re
import time
import yaml

from kubernetes import config
from kubernetes.client import Configuration
from kubernetes.client.api import core_v1_api
from kubernetes.client.rest import ApiException
from kubernetes.stream import stream


def exec_commands(api_instance):
    name = 'flexran-du'
    namespace = 'flexran-test'
    resp = None
    try:
        resp = api_instance.read_namespaced_pod(name=name,
                                                namespace=namespace)
    except ApiException as e:
        if e.status != 404:
            print("Unknown error: %s" % e)
            exit(1)

    if not resp:
        print("Pod %s does not exist. Creating it..." % name)
        with open("pod_flexran_acc100.yaml", "r") as f:
            pod_manifest = yaml.safe_load(f)
        resp = api_instance.create_namespaced_pod(body=pod_manifest,
                                                  namespace=namespace)
        while True:
            resp = api_instance.read_namespaced_pod(name=name,
                                                    namespace=namespace)
            if resp.status.phase != 'Pending':
                break
            time.sleep(1)
        print("Done.")

    # Calling exec interactively
    exec_command = ['/bin/sh']
    resp = stream(api_instance.connect_get_namespaced_pod_exec,
                  name,
                  namespace,
                  command=exec_command,
                  stderr=True, stdin=True,
                  stdout=True, tty=True,
                  _preload_content=False)
    commands = [
        "source /opt/flexran/auto/env.src",
        "cd /opt/flexran/bin/nr5g/gnb/l1",
        "./l1.sh -e",
    ]
    
    while resp.is_open():
        if commands:
            c = commands.pop(0)
            print("Running command... %s\n" % c)
            resp.write_stdin(c + "\n")
            time.sleep(1)
            resp.write_stdin("\n")
        else:
            break

    resp.run_forever(5)
    output = resp.read_stdout()
    if "welcome" in output:
        print("l1app ready")
    else:
        print(output)
        sys.exit(1)

    testmac_resp = stream(api_instance.connect_get_namespaced_pod_exec,
                  name,
                  namespace,
                  command=exec_command,
                  stderr=True, stdin=True,
                  stdout=True, tty=True,
                  _preload_content=False)
    commands = [
        "source /opt/flexran/auto/env.src",
        "cd /opt/flexran/bin/nr5g/gnb/testmac",
        "./l2.sh --testfile=cascade_lake-sp/clxsp_mu1_100mhz_4x4_hton.cfg",
    ]
    
    while testmac_resp.is_open():
        if commands:
            c = commands.pop(0)
            print("Running command... %s\n" % c)
            testmac_resp.write_stdin(c + "\n")
            time.sleep(1)
            testmac_resp.write_stdin("\n")
        else:
            break

    testmac_resp.run_forever(5)
    output = testmac_resp.read_stdout()
    if "welcome" in output:
        print("testmac ready")
    else:
        print(output)
        sys.exit(1)
    
    while testmac_resp.is_open():
        testmac_resp.run_forever(3)
        output = testmac_resp.read_stdout()
        result = re.search(r"All Tests Completed.*\n", output)
        if result:
            print(result.group())
            break

    resp.write_stdin("exit\n")
    time.sleep(1)
    testmac_resp.write_stdin("exit\n")
    resp.close()
    testmac_resp.close()



def main():
    config.load_kube_config()
    try:
        c = Configuration().get_default_copy()
    except AttributeError:
        c = Configuration()
        c.assert_hostname = False
    Configuration.set_default(c)
    core_v1 = core_v1_api.CoreV1Api()

    exec_commands(core_v1)


if __name__ == '__main__':
    main()
