#!/usr/bin/python3

import sys, yaml
from typing import Dict, List
import lxml.etree as LET
from dataclasses import dataclass, field
from cpu import CpuResource


@dataclass
class CfgThread:

    cfg_file_name: str = field(init=False, default=None)
    thread_id: int = field(init=False, default=None)
    thread_name: str = field(init=False, default=None)
    thread_pri: int = field(init=False, default=None)
    init: bool =  field(init=True, default=False)

    def fill_cfg(self, file_name: str, thread_id: int, thread_name: str, pri: int):
        init = True
        self.cfg_file_name = file_name
        self.thread_id = thread_id
        self.thread_name = thread_name
        self.thread_pri = pri
    
    def get_xml_text_value_str(self) -> str :
        return(str(self.thread_id) + ", " + str(self.thread_pri) + ", 0")


class CfgThreadData:
    phycfg_timer_cfg_xml = 'phycfg_timer.xml'
    testmac_cfg_xml = 'testmac_cfg.xml'

    dict_list_cfg_threads: Dict[str, List[CfgThread]] = {}
    dict_thread_name_id: Dict[str, int] = {} 
    monk_cpu_id = 0

    @classmethod 
    def get_mock_cpu_id(cls):
        cls.monk_cpu_id +=1
        return cls.monk_cpu_id

    @classmethod 
    def load_thread_cfg(cls, cfg_file_name: str, thread_name: str, thread_id: int, pri: int):
        #print(cfg_file_name, ": ", thread_name, "pri: ", pri)
        if thread_name not in cls.dict_thread_name_id.keys():
            id = thread_id 
            cls.dict_thread_name_id[thread_name] = id

        athread = CfgThread() 
        athread.fill_cfg(cfg_file_name, cls.dict_thread_name_id[thread_name], thread_name, pri)
        if cfg_file_name not in cls.dict_list_cfg_threads.keys():
            cls.dict_list_cfg_threads[cfg_file_name] = [athread] 
        else:
            cls.dict_list_cfg_threads[cfg_file_name].append(athread)


    @classmethod
    def read_and_update_threads_cfg_xml(cls, cfg_file_name: str, threads: List[CfgThread]):
        assert(cfg_file_name == cls.phycfg_timer_cfg_xml or cfg_file_name == cls.testmac_cfg_xml)

        try:
            with open(cfg_file_name, encoding="utf8") as f:

                xml_tree = LET.parse(f)

                root = xml_tree.getroot()
                root_threads = root.find('Threads')
                #print(LET.tostring(root_threads, encoding="unicode", pretty_print = True))

                for thread in threads:
                    xml_thread = root_threads.find(thread.thread_name)
                    if xml_thread == None:
                        print("Cound not find the existing thread configuration")
                        continue

                    xml_thread.text = thread.get_xml_text_value_str()
                    #print("Update thread: ", thread.thread_name, thread.get_xml_text_value_str())
                
                xml_tree.write(cfg_file_name)
        except:
            sys.exit("Could not open file: "(cfg_file_name))


    @classmethod
    def process_threads_cfg_into_xml(cls):
        for file in cls.dict_list_cfg_threads.keys():
            cls.read_and_update_threads_cfg_xml(file, cls.dict_list_cfg_threads[file])


    @classmethod
    def read_threads_yaml(cls, threads_cfg_yaml, cpu_resource: CpuResource):
        try:
            with open(threads_cfg_yaml, "r") as fsrc:

                try:
                    yaml_data = yaml.safe_load(fsrc)
                except Exception as e:
                    sys.exit("Could not parse the yaml file: %s" %e)

                if "Threads" in yaml_data.keys():
                    yaml_threads = yaml_data["Threads"]

                    #print(yaml_threads)
                    for num in yaml_threads:
                        #print (num, ": ", yaml_threads[num])
                        cfg_objs = yaml_threads[num]
                        thread_id = cpu_resource.allocate_whole_core()
                        for cfg in cfg_objs:
                            #print(cfg, ": ", cfg_objs[cfg])
                            threads = cfg_objs[cfg]
                            for thread in threads:
                                #print(thread, ": ", threads[thread]["pri"])
                                cfg_name = cfg + ".xml"
                                cls.load_thread_cfg(cfg_name, thread, thread_id, threads[thread]["pri"])

        except Exception as e:
            sys.exit("Could not open the file: %s" %e)

    @classmethod
    def update_threads_cfg_xml(cls, yaml_file_name, cpu_resource: CpuResource):
        cls.read_threads_yaml(yaml_file_name, cpu_resource)
        cls.process_threads_cfg_into_xml()


'''
def main(name, argv):
    CfgThreadData.update_threads_cfg_xml()


if __name__ == '__main__':
    main(sys.argv[0], sys.argv[1:])
'''
