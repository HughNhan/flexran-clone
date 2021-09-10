#!/usr/bin/python3

from cpu import CpuResource

class ProcessTestfile:

    # A function to take the setcore maps in the config file and allocate
    # relevant cpus on the current machine, creating a new map and writing it
    # in place, always allocating siblings.
    #
    # References:
    #   https://stackoverflow.com/questions/38935169/convert-elements-of-a-list-into-binary
    #   https://stackoverflow.com/questions/21409461/binary-list-from-indices-of-ascending-integer-list
    @classmethod
    def update_testfile(cls, rsc, testfile):
        print('Updating testfile...')
        try:
            f = open(testfile, 'r')
            cfg = list(f)
            f.close()
        except:
            sys.exit("can't open %s" %(cfg))
        line_index = 0
        for line in cfg:
            if 'setcore' in line:
                setcore_index = line.index('setcore')
                # The number of cpus (cores or threads, depening on hyperthreading, needed.)
                # Take the string, convert to hex, convert to binary, count the 1s.
                num_cpus = (bin(int(line[setcore_index + len('setcore'):].strip(), 16))[2:]).count('1')
                # Allocate siblings based on the current setcore.
                cpus = rsc.allocate_siblings(num_cpus)
                # Create a list of binary digits based off CPU indices.
                new_setcore_list = [int(i in cpus) for i in range(max(cpus)+1)]
                # Revere the list, then create the binary number.
                new_setcore_list.reverse()
                new_setcore_binary = 0
                for digit in new_setcore_list:
                    new_setcore_binary = 2 * new_setcore_binary + digit
                # Create the hex representation and replace the old setcore
                new_setcore_hex = ' ' + hex(new_setcore_binary) + '\n'
                cfg[line_index] = line.replace(line[setcore_index + len('setcore'):], new_setcore_hex)

            line_index += 1

        # Write the new configuration to the same file.
        try:
            f = open(testfile, 'w')
            f.writelines(cfg)
        except:
            sys.exit("can't write %s" %(cfg))
        print('New testfile written.')
        f.close()
