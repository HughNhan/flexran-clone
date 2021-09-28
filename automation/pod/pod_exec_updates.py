#!/usr/bin/env python3
"""
Exec flexran test suite in a flexran container
"""

import argparse
import re
import subprocess
import sys
import time
import yaml

from kubernetes import config
from kubernetes.client import Configuration
from kubernetes.client.api import core_v1_api
from kubernetes.client.rest import ApiException
from kubernetes.stream import stream

DEBUG = False

def main():
    # Get the command line arguments from the user.
    parser = argparse.ArgumentParser(
        description='Execute updates of testfile and configuration on pod.')
    parser.add_argument('-p', '--pod', metavar='pod', type=str,
        required=True,
        help='the name of the pod')
    parser.add_argument('-d', '--dest', metavar='destination', type=str,
        required=True,
        help='the destination directory on the pod')
    parser.add_argument('-testmac', '--testmac_dir',
        metavar='testmac_directory', type=str, required=True,
        help='the testmac directory on the pod')
    parser.add_argument('-l1', '--l1_dir',
        metavar='l1_directory', type=str, required=True,
        help='the l1 directory on the pod')
    parser.add_argument('-t', '--testfile', metavar='testfile', type=str,
        required=True,
        help='the path to the testfile to be updated')
    parser.add_argument('-c', '--cfg', metavar='cfg', type=str,
        required=True,
        help='the configuration file to update threads')
    parser.add_argument('-n', '--no_sibling', default=False,
        action='store_true',
        help='optional no_sibling flag')
    parser.add_argument('-f', '--file', action='append', metavar='file',
        type=str, required=False, help='the file(s) to be copied to the pod')
    parser.add_argument('-dir', '--dir', action='append', metavar='directory',
        type=str, required=False,
        help='the directory(ies) to be copied to the pod (requires rsync or ' +
             'tar on pod)')

    args = parser.parse_args()
    pod_name = args.pod
    destination = args.dest
    testmac = args.testmac_dir
    l1 = args.l1_dir
    testfile = args.testfile
    cfg = args.cfg
    no_sibling = args.no_sibling
    files = args.file
    directories = args.dir

    config.load_kube_config()
    try:
        c = Configuration().get_default_copy()
    except AttributeError:
        c = Configuration()
        c.assert_hostname = False
    Configuration.set_default(c)
    core_v1 = core_v1_api.CoreV1Api()

    check_and_start_pod(pod_name, core_v1)
    if files:
        copy_files(pod_name, destination, files)
    if directories:
        copy_directories(pod_name, destination, directories)
    exec_updates(pod_name, core_v1, destination, testmac, l1, testfile, cfg,
                 no_sibling)

<<<<<<< HEAD
    exec_commands(pod_name, core_v1, pod_name, testmac, l1, testfile)

def copy_files(pod_name, destination, files):
    print('\nCopying files to pod \'' + pod_name + '\':')
=======
    #exec_commands(pod_name, core_v1)

def copy_files(pod_name, destination, files):
    print('Copying files to pod \'' + pod_name + '\':')
>>>>>>> b340eba... Large update: Updating code to take paths to configs, updating for exec on pods
    for file in files:
        output = subprocess.check_output(
                ['oc', 'cp', file, pod_name + ':' + destination])
        print(file)
    return

# NOTE: Need to enable rsync or tar on pod.
def copy_directories(pod_name, destination, directories):
    print('Copying directories to pod \'' + pod_name + '\':')
    for directory in directories:
        output = subprocess.check_output(
                ['oc', 'rsync', directory, pod_name + ':' + destination])
        print(directory)
    return

def check_and_start_pod(name, api_instance):
    resp = None
    try:
        resp = api_instance.read_namespaced_pod(name=name,
                                                namespace='default')
    except ApiException as e:
        if e.status != 404:
            print("Unknown error: %s" % e)
            exit(1)
<<<<<<< HEAD
    #print(resp.status.phase)
    if resp and resp.status.phase != 'Running':
        print("Pod %s exists but is not running. Deleting it..." % name)
        resp = api_instance.delete_namespaced_pod(name=name,
                                                namespace='default')
        while True:
            try:
                resp = api_instance.read_namespaced_pod(name=name,
                                                        namespace='default')
            except:
                break
            time.sleep(1)

    if not resp or resp.status.phase != 'Running':
        print("Pod %s does not exist. Creating it..." % name)
        with open("pod_flexran_n3000.yaml", "r") as f:
=======

    if not resp:
        print("Pod %s does not exist. Creating it..." % name)
        with open("pod_flexran_sw.yaml", "r") as f:
>>>>>>> b340eba... Large update: Updating code to take paths to configs, updating for exec on pods
            pod_manifest = yaml.safe_load(f)
        resp = api_instance.create_namespaced_pod(body=pod_manifest,
                                                  namespace='default')
        while True:
            resp = api_instance.read_namespaced_pod(name=name,
                                                    namespace='default')
            if resp.status.phase != 'Pending':
                break
            time.sleep(1)
        print("Done.")
    return

def exec_updates(name, api_instance, destination, testmac,
                 l1, testfile, cfg, no_sibling):
    # Calling exec interactively
    exec_command = ['/bin/sh']
    resp = stream(api_instance.connect_get_namespaced_pod_exec,
                  name,
                  'default',
                  command=exec_command,
                  stderr=True, stdin=True,
                  stdout=True, tty=True,
                  _preload_content=False)

<<<<<<< HEAD
    update_command = "./autotest.py" + " --testfile " + testfile + " --cfg " + cfg

=======
    update_command = "./autotest.py --testmac_dir " + testmac + " --l1_dir " + \
                     l1 + " --testfile " + testfile + " --cfg " + cfg
    print(update_command)
>>>>>>> b340eba... Large update: Updating code to take paths to configs, updating for exec on pods
    if no_sibling:
        update_command = update_command + ' --no_sibling'

    # Is there a generic way to install these dependencies? VENV? pip3 freeze
    commands = [
        'pip3 install lxml',
        'pip3 install dataclasses',
        "cd " + destination,
        update_command,
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
    if "Files updated." in output:
        if DEBUG:
            print(output)
<<<<<<< HEAD
        print("Finished updating files on pod.\n")
=======
        print("Finished updating files on pod")
>>>>>>> b340eba... Large update: Updating code to take paths to configs, updating for exec on pods
    else:
        print(output)
        sys.exit(1)

<<<<<<< HEAD
def exec_commands(name, api_instance, pod_name, testmac, l1, testfile):
=======
def exec_commands(name, api_instance):
>>>>>>> b340eba... Large update: Updating code to take paths to configs, updating for exec on pods
    # Calling exec interactively
    exec_command = ['/bin/sh']
    resp = stream(api_instance.connect_get_namespaced_pod_exec,
                  name,
                  'default',
                  command=exec_command,
                  stderr=True, stdin=True,
                  stdout=True, tty=True,
                  _preload_content=False)
    commands = [
        "source /opt/flexran/auto/env.src",
<<<<<<< HEAD
        "cd " + l1,
=======
        "cd /opt/flexran/bin/nr5g/gnb/l1",
>>>>>>> b340eba... Large update: Updating code to take paths to configs, updating for exec on pods
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
<<<<<<< HEAD
        print("l1app ready\n")
=======
        print("l1app ready")
>>>>>>> b340eba... Large update: Updating code to take paths to configs, updating for exec on pods
    else:
        print(output)
        sys.exit(1)

    testmac_resp = stream(api_instance.connect_get_namespaced_pod_exec,
                  name,
                  'default',
                  command=exec_command,
                  stderr=True, stdin=True,
                  stdout=True, tty=True,
                  _preload_content=False)
    commands = [
        "source /opt/flexran/auto/env.src",
<<<<<<< HEAD
        "cd " + testmac,
        "./l2.sh --testfile=" + testfile,
=======
        "cd /opt/flexran/bin/nr5g/gnb/testmac",
        "./l2.sh --testfile=cascade_lake-sp/clxsp_mu1_100mhz_4x4_hton.cfg",
>>>>>>> b340eba... Large update: Updating code to take paths to configs, updating for exec on pods
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

<<<<<<< HEAD
    l1_output = output

    testmac_resp.run_forever(5)
    output = testmac_resp.read_stdout()
    if "welcome" in output:
        print("Testmac ready\n")
=======
    testmac_resp.run_forever(5)
    output = testmac_resp.read_stdout()
    if "welcome" in output:
        print("testmac ready")
>>>>>>> b340eba... Large update: Updating code to take paths to configs, updating for exec on pods
    else:
        print(output)
        sys.exit(1)

<<<<<<< HEAD
    print('Running tests...')

    testmac_output = ''

    while testmac_resp.is_open():
        testmac_resp.run_forever(3)
        testmac_output = testmac_output + testmac_resp.read_stdout()
        l1_output = l1_output + resp.read_stdout()
        result = re.search(r"All Tests Completed.*\n", testmac_output)
        if result:
            print(result.group())
            print("Copying stat file (l1_mlog_stats.txt) to current directory...")
            copy_output = subprocess.check_output(
                    ['oc', 'cp', pod_name + ':' + l1 + '/l1_mlog_stats.txt', "./l1_mlog_stats.txt"])
            #print(output)
            print("Writing l1 output (l1.txt) to current directory...")
            l1_out = open('l1.txt', 'w')
            out = l1_out.write(l1_output)
            l1_out.close()

            print("Writing testfile output (testmac.txt) to current directory...")
            test_output = open('testmac.txt', 'w')
            out = test_output.write(testmac_output)
            test_output.close()

            print("Completed.")
=======
    while testmac_resp.is_open():
        testmac_resp.run_forever(3)
        output = testmac_resp.read_stdout()
        result = re.search(r"All Tests Completed.*\n", output)
        if result:
            print(result.group())
>>>>>>> b340eba... Large update: Updating code to take paths to configs, updating for exec on pods
            break

    resp.write_stdin("exit\n")
    time.sleep(1)
    testmac_resp.write_stdin("exit\n")
    resp.close()
    testmac_resp.close()

if __name__ == '__main__':
    main()
