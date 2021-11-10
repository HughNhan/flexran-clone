#!/usr/bin/env python3
"""
Exec flexran test suite in a flexran container
"""

import argparse
import datetime
import os
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
    parser.add_argument('-c', '--cfg', metavar='cfg', type=str,
        required=True,
        help='the configuration file to update threads, define paths, and get tests')
    parser.add_argument('-n', '--no_sibling', default=False,
        action='store_true',
        help='optional no_sibling flag')
    parser.add_argument('-f', '--file', action='append', metavar='file',
        type=str, required=False, help='the file(s) to be copied to the pod')
    parser.add_argument('-dir', '--dir', action='append', metavar='directory',
        type=str, required=False,
        help='the directory(ies) to be copied to the pod (requires rsync or ' +
             'tar on pod)')
    #parser.add_argument('-r', '--restart', default=False, action='store_true',
    #    help='a flag which will cause the pod to restart (useful for between each test)')
    parser.add_argument('-x', '--xran', default=False, action='store_true',
        help='a flag indicating xran test mode')
    parser.add_argument('-phystart', '--phystart', default=False,
        required=False, action='store_true',
        help='a flag indicating quick phystart in xran mode (phystart 4 0 100007)')
    parser.add_argument('-namespace', '--namespace', type=str,
        required=True,
        help='the namespace of the pod')
    parser.add_argument('-timeout', '--timeout', type=int,
        required=True,
        help='the timeout (in seconds) for the test')

    # Parse arguments.
    args = parser.parse_args()
    pod_name = args.pod
    destination = args.dest
    cfg = args.cfg
    no_sibling = args.no_sibling
    files = args.file
    directories = args.dir
    #restart = args.restart
    xran = args.xran
    phystart = args.phystart
    pod_namespace = args.namespace
    timeout = args.timeout

    # Get Kube configuration.
    config.load_kube_config()
    try:
        c = Configuration().get_default_copy()
    except AttributeError:
        c = Configuration()
        c.assert_hostname = False
    Configuration.set_default(c)
    core_v1 = core_v1_api.CoreV1Api()

    #check_and_start_pod(pod_name, core_v1, restart, , pod_namespace)
    # Check the pod is running, exit otherwise.
    check_pod(pod_name, core_v1, pod_namespace)

    if files:
        copy_files(pod_name, destination, files)
    if directories:
        copy_directories(pod_name, destination, directories)

    test_list = get_tests_from_yaml(cfg)
    architecture_dir = get_architecture_from_yaml(cfg, xran)

    l1 = get_l1_from_yaml(cfg)
    testmac = get_testmac_from_yaml(cfg)

    # Update the testfiles and xml configurations on the pod.
    exec_updates(pod_name, core_v1, destination, testmac, l1, test_list, cfg,
                 no_sibling, architecture_dir, xran, phystart, pod_namespace)

    for testfile in test_list:
        print('--------------------------------------------------------------' +
              '------------------\nRunning test: ' + testfile + '\n----------' +
              '--------------------------------------------------------------' +
              '--------')
        if xran:
            testfile = l1 + '/' + testfile
        else:
            testfile = testmac + '/' + architecture_dir + '/' + testfile
        # Run the test on the pod.
        exec_tests(pod_name, core_v1, pod_name, testmac, l1, testfile, xran, pod_namespace, timeout)

# A method to get the tests from the YAML file, taking in the path to the YAML
# config file and returning the list of tests.
def get_tests_from_yaml(cfg):
    try:
        f = open(cfg, 'r')
        config_yaml = yaml.safe_load(f)
        f.close()
    except:
        sys.exit("Can't open or parse %s" %(cfg))

    if 'Tests' in config_yaml and config_yaml['Tests'] is not None:
        return config_yaml['Tests']
    else:
        print('No tests in config...')
        return []

# A method to get the cpu architecture directory from the YAML file, taking in
# the path to the YAML config file and returning the directory. The xran flag
# is also passed in, as this does not apply to xran tests.
def get_architecture_from_yaml(cfg, xran):
    try:
        f = open(cfg, 'r')
        config_yaml = yaml.safe_load(f)
        f.close()
    except:
        sys.exit("Can't open or parse %s" %(cfg))

    if xran:
        print("No architecture directory required for xran tests")
        return
    else:
        if 'Arch_dir' in config_yaml:
            return config_yaml['Arch_dir']
        else:
            print('No architecture directory in config...')
            exit(1)

# A method to get the l1 directory from the YAML file, taking in the path to
# the YAML config file and returning the path.
def get_l1_from_yaml(cfg):
    try:
        f = open(cfg, 'r')
        config_yaml = yaml.safe_load(f)
        f.close()
    except:
        sys.exit("Can't open or parse %s" %(cfg))

    if 'Cfg_file_paths' in config_yaml:
        for index in config_yaml['Cfg_file_paths']:
            for config_name in config_yaml['Cfg_file_paths'][index]:
                if config_name[0:6] == 'phycfg':
                    if config_yaml['Cfg_file_paths'][index][config_name][-1] == '/':
                        return config_yaml['Cfg_file_paths'][index][config_name][:-1]
                    else:
                        return config_yaml['Cfg_file_paths'][index][config_name]
    else:
        print('No config files in config...')
        exit(1)

# A method to get the testmac directory from the YAML file, taking in the path
# to the YAML config file and returning the path.
def get_testmac_from_yaml(cfg):
    try:
        f = open(cfg, 'r')
        config_yaml = yaml.safe_load(f)
        f.close()
    except:
        sys.exit("Can't open or parse %s" %(cfg))

    if 'Cfg_file_paths' in config_yaml:
        for index in config_yaml['Cfg_file_paths']:
            for config_name in config_yaml['Cfg_file_paths'][index]:
                if config_name[0:7] == 'testmac':
                    if config_yaml['Cfg_file_paths'][index][config_name][-1] == '/':
                        return config_yaml['Cfg_file_paths'][index][config_name][:-1]
                    else:
                        return config_yaml['Cfg_file_paths'][index][config_name]
    else:
        print('No config files in config...')
        exit(1)

# A method to copy a list of files from the host to the pod at the passed
# destination. This is used to move the scripts, configuration files, etc. to
# the pod.
def copy_files(pod_name, destination, files):
    print('\nCopying files to pod \'' + pod_name + '\':')
    for file in files:
        output = subprocess.check_output(
                ['oc', 'cp', file, pod_name + ':' + destination])
        print(file)
    return

# A method to copy a list of directories from the host to the pod at the passed
# destination. This is used to move the scripts, configuration files, etc. to
# the pod.
# NOTE: Need to enable rsync on pod.
def copy_directories(pod_name, destination, directories):
    print('Copying directories to pod \'' + pod_name + '\':')
    for directory in directories:
        output = subprocess.check_output(
                ['oc', 'rsync', directory, pod_name + ':' + destination])
        print(directory)
    return

# A method to check if the pod is running. Exit if it does not exist, as the
# assumption is that the pod will be running and configured for tests before
# this script is called.
def check_pod(name, api_instance, pod_namespace):
    resp = None
    try:
        resp = api_instance.read_namespaced_pod(name=name,
                                                namespace=pod_namespace)
    except ApiException as e:
        if e.status != 404:
            print("Unknown error: %s" % e)
            exit(1)
    if not resp or resp.status.phase != 'Running':
        print("Pod %s does not exist. Exiting..." % name)
        exit(1)

# A method to check if the pod is running and start it if needed. Unlike
# check_pod above, this does not exit, it will attempt to start the pod. This
# is unused in the current end-to-end automation as this is handled before this
# script is called.
def check_and_start_pod(name, api_instance, restart, pod_namespace):
    resp = None
    try:
        resp = api_instance.read_namespaced_pod(name=name,
                                                namespace=pod_namespace)
    except ApiException as e:
        if e.status != 404:
            print("Unknown error: %s" % e)
            exit(1)
    #print(resp.status.phase)
    if (resp and resp.status.phase != 'Running') or restart:
        print("Pod %s exists but but will be restarted. Deleting it..." % name)
        resp = api_instance.delete_namespaced_pod(name=name,
                                                namespace=pod_namespace)
        while True:
            try:
                resp = api_instance.read_namespaced_pod(name=name,
                                                        namespace=pod_namespace)
            except:
                break
            time.sleep(1)

    if not resp or resp.status.phase != 'Running':
        print("Pod %s does not exist. Creating it..." % name)
        with open("pod_flexran_n3000.yaml", "r") as f:
            pod_manifest = yaml.safe_load(f)
        resp = api_instance.create_namespaced_pod(body=pod_manifest,
                                                  namespace=pod_namespace)
        while True:
            resp = api_instance.read_namespaced_pod(name=name,
                                                    namespace=pod_namespace)
            if resp.status.phase != 'Pending':
                break
            time.sleep(1)
        print("Done.")
    return

# A method to execute updates to the testfiles and xml configurations on the
# pod.
def exec_updates(name, api_instance, destination, testmac,
                 l1, test_list, cfg, no_sibling, architecture_dir, xran,
                 phystart, pod_namespace):
    commands = [
        'pip3 install lxml',
        'pip3 install dataclasses',
        "cd " + destination,
    ]

    run_commands_on_pod(name, api_instance, commands, pod_namespace)

    for testfile in test_list:
        if xran:
            testfile = l1 + '/' + testfile
        else:
            testfile = testmac + '/' + architecture_dir + '/' + testfile
        update_command = "./autotest.py" + " --testfile " + testfile + " --cfg " + cfg.split('/')[-1]

        if xran and phystart:
            update_command = update_command + ' --phystart'

        if no_sibling:
            update_command = update_command + ' --no_sibling'

        # Is there a generic way to install these dependencies? VENV? pip3 freeze
        commands = [
            update_command,
        ]

        output = run_commands_on_pod(name, api_instance, commands, pod_namespace)
        if "Files updated." in output:
            if DEBUG:
                print(output)
            print("Finished updating files on pod.\n")
        else:
            print(output)
            sys.exit(1)

# A method which can run a list of commands on the pod.
def run_commands_on_pod(name, api_instance, commands, pod_namespace):
    exec_command = ['/bin/sh']
    resp = stream(api_instance.connect_get_namespaced_pod_exec,
                  name,
                  pod_namespace,
                  command=exec_command,
                  stderr=True, stdin=True,
                  stdout=True, tty=True,
                  _preload_content=False)

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
    return output

# A method to execute the given test on the pod.
def exec_tests(name, api_instance, pod_name, testmac, l1, testfile, xran, pod_namespace, timeout):
    # Calling exec interactively
    exec_command = ['/bin/sh']
    resp = stream(api_instance.connect_get_namespaced_pod_exec,
                  name,
                  pod_namespace,
                  command=exec_command,
                  stderr=True, stdin=True,
                  stdout=True, tty=True,
                  _preload_content=False)

    commands = [
        "source /opt/flexran/auto/env.src",
        "cd " + l1,
    ]
    if xran:
        commands.append("./l1.sh -oru")
    else:
        commands.append("./l1.sh -e")

    while resp.is_open():
        if commands:
            c = commands.pop(0)
            print("Running command... %s\n" % c)
            resp.write_stdin(c + "\n")
            time.sleep(1)
            resp.write_stdin("\n")
        else:
            break
    # NOTE: This time might need adjusting, run_forever(5) ran into some
    #       crashing issues which we think have to do with timing.
    resp.run_forever(10)
    output = resp.read_stdout()
    if "welcome" in output:
        print("l1app ready\n")
    else:
        print(output)
        sys.exit(1)

    testmac_resp = stream(api_instance.connect_get_namespaced_pod_exec,
                  name,
                  pod_namespace,
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
        print("Testmac failed to start!\n")
        print(output)
        write_to_files(testfile, '', xran, l1, pod_name, l1_output, testmac_output)
        sys.exit(1)

    print('Running tests...')

    testmac_output = ''

    last_update = 0
    timed_out = False
    while testmac_resp.is_open():
        testmac_resp.run_forever(3)
        testmac_output = testmac_output + testmac_resp.read_stdout()
        l1_output = l1_output + resp.read_stdout()
        result = re.search(r"All Tests Completed.*\n", testmac_output)
        seg_fault = re.search(r"Segmentation Fault!*\n", testmac_output)
        core_os_terminal = re.search(r".*\#", testmac_output)

        if testmac_output:
            last_update = time.time()
        elif time.time() - last_update >= timeout:
            print('Testmac timed out without update!\n')
            timed_out = True

        if result or seg_fault or core_os_terminal or timed_out:
            write_to_files(testfile, result, xran, l1, pod_name, l1_output, testmac_output)
            break

    resp.write_stdin("exit\r\n")
    testmac_resp.write_stdin("exit\r\n")
    time.sleep(5)
    resp.close()
    testmac_resp.close()

def write_to_files(testfile, result, xran, l1, pod_name, l1_output, testmac_output):
    print('Checking directory status...')
    directory_exits = os.path.isdir(RESULTS_DIR)
    if not directory_exits:
        os.makedirs(RESULTS_DIR)
        print('Created results directory')
    else:
        print('Results directory exits')

    test_dir = RESULTS_DIR + '/' + (testfile.split('/')[-1]).split('.')[0]
    directory_exits = os.path.isdir(test_dir)
    if not directory_exits:
        os.makedirs(test_dir)
        print('Created ' + test_dir + ' directory')
    else:
        print(test_dir + ' directory exits')

    time_dir = test_dir + '/' + datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    directory_exits = os.path.isdir(time_dir)
    if not directory_exits:
        os.makedirs(time_dir)
        print('Created ' + time_dir + ' directory')
    else:
        print(time_dir + ' directory exits')

    print(result.group())
    print("Copying stat file (l1_mlog_stats.txt) to results directory...")

    if xran:
        mlog_path = l1.split('l1')[0] + 'l1' + '/l1_mlog_stats.txt'
    else:
        mlog_path = l1 + '/l1_mlog_stats.txt'
    copy_output = subprocess.check_output(
            ['oc', 'cp', pod_name + ':' + mlog_path, "./" + time_dir + "/l1_mlog_stats.txt"])

    #print(output)
    print("Writing l1 output (l1.txt) to results directory...")
    l1_out = open('./' + time_dir + '/l1.txt', 'w')
    out = l1_out.write(l1_output)
    l1_out.close()

    print("Writing testfile output (testmac.txt) to results directory...")
    test_output = open('./' + time_dir + '/testmac.txt', 'w')
    out = test_output.write(testmac_output)
    test_output.close()

    print("Completed.")

    return

if __name__ == '__main__':
    main()