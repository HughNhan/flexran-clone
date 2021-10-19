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
RESULTS_DIR = 'results'

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
    parser.add_argument('-r', '--restart', default=False, action='store_true',
        help='a flag which will cause the pod to restart (useful for between each test)')

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
    restart = args.restart

    config.load_kube_config()
    try:
        c = Configuration().get_default_copy()
    except AttributeError:
        c = Configuration()
        c.assert_hostname = False
    Configuration.set_default(c)
    core_v1 = core_v1_api.CoreV1Api()

    #check_and_start_pod(pod_name, core_v1, restart)
    check_pod(pod_name, core_v1)

    if files:
        copy_files(pod_name, destination, files)
    if directories:
        copy_directories(pod_name, destination, directories)
    exec_updates(pod_name, core_v1, destination, testmac, l1, testfile, cfg,
                 no_sibling)

    exec_commands(pod_name, core_v1, pod_name, testmac, l1, testfile)

def copy_files(pod_name, destination, files):
    print('\nCopying files to pod \'' + pod_name + '\':')
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

def check_pod(name, api_instance):
    resp = None
    try:
        resp = api_instance.read_namespaced_pod(name=name,
                                                namespace='default')
    except ApiException as e:
        if e.status != 404:
            print("Unknown error: %s" % e)
            exit(1)
    if not resp or resp.status.phase != 'Running':
        print("Pod %s does not exist. Exiting..." % name)
        exit(1)

def check_and_start_pod(name, api_instance, restart):
    resp = None
    try:
        resp = api_instance.read_namespaced_pod(name=name,
                                                namespace='default')
    except ApiException as e:
        if e.status != 404:
            print("Unknown error: %s" % e)
            exit(1)
    #print(resp.status.phase)
    if (resp and resp.status.phase != 'Running') or restart:
        print("Pod %s exists but but will be restarted. Deleting it..." % name)
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

    update_command = "./autotest.py" + " --testfile " + testfile + " --cfg " + cfg.split('/')[-1]

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
        print("Finished updating files on pod.\n")
    else:
        print(output)
        sys.exit(1)

def exec_commands(name, api_instance, pod_name, testmac, l1, testfile):
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
        "cd " + l1,
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
        print("l1app ready\n")
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
        "cd " + testmac,
        "./l2.sh --testfile=" + testfile,
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

    l1_output = output

    testmac_resp.run_forever(5)
    output = testmac_resp.read_stdout()
    if "welcome" in output:
        print("Testmac ready\n")
    else:
        print(output)
        sys.exit(1)

    print('Running tests...')

    testmac_output = ''

    while testmac_resp.is_open():
        testmac_resp.run_forever(3)
        testmac_output = testmac_output + testmac_resp.read_stdout()
        l1_output = l1_output + resp.read_stdout()
        result = re.search(r"All Tests Completed.*\n", testmac_output)
        if result:
            print('Checking directory status...')
            directory_exits = os.path.isdir(RESULTS_DIR)
            if not directory_exits:
                os.makedirs(RESULTS_DIR)
                print('Created results directory')
            else:
                print('Results directory exits')

            test_dir = (testfile.split('/')[-1]).split('.')[0]
            directory_exits = os.path.isdir(test_dir)
            if not directory_exits:
                os.makedirs(RESULTS_DIR)
                print('Created results/' + test_dir + ' directory')
            else:
                print('results/' + test_dir + ' directory exits')

            print(result.group())
            print("Copying stat file (l1_mlog_stats.txt) to results directory...")

            copy_output = subprocess.check_output(
                    ['oc', 'cp', pod_name + ':' + l1 + '/l1_mlog_stats.txt', "./" + RESULTS_DIR + '/' + test_dir + "/l1_mlog_stats.txt"])
            #print(output)
            print("Writing l1 output (l1.txt) to results directory...")
            l1_out = open('./' + RESULTS_DIR + '/' + test_dir + '/l1.txt', 'w')
            out = l1_out.write(l1_output)
            l1_out.close()

            print("Writing testfile output (testmac.txt) to results directory...")
            test_output = open('./' + RESULTS_DIR + '/' + test_dir + '/testmac.txt', 'w')
            out = test_output.write(testmac_output)
            test_output.close()

            print("Completed.")
            break

    resp.write_stdin("exit\n")
    time.sleep(1)
    testmac_resp.write_stdin("exit\n")
    resp.close()
    testmac_resp.close()

if __name__ == '__main__':
    main()
