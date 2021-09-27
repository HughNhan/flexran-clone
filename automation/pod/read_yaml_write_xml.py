#!/usr/bin/python3

from io import TextIOWrapper
from re import I
import sys, yaml, os
from typing import Any, Dict, List
import lxml.etree as LET
from dataclasses import dataclass, field
from cpu import CpuResource

#function to read env variable
def get_env_variable(evn_variable_name: str) -> str:
    return os.environ.get(evn_variable_name)

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


@dataclass
class CfgDpdk:

    cfg_file_name: str = field(init=False, default=None)
    mem_size_str: str = field(init=False, default=None) 
    mem_size_val: int = field(init=False, default=None)

    base_band_fec_mode_str: str = "dpdkBasebandFecMode" 
    base_band_fec_mode_val: int = field(init=False, default=None)
    base_band_device_str: str = "dpdkBasebandDevice"
    base_band_device_val: str = field(init=False, default="0000:1f:00.1")

class CfgData:
    # file paths 
    dict_cfgfile_paths: Dict[str, str] = {}

    # thread cfgs
    dict_list_cfg_threads: Dict[str, List[CfgThread]] = {}
    dict_thread_name_id: Dict[str, int] = {} 
    monk_cpu_id = 0

    # dpdk cfgs
    #phycfg_timer_cfg_xml = 'phycfg_timer.xml'
    #phycfg_timer_cfg_xml = 'pod_testmac.xml'
    env_acc_mode_str: str = "PCIDEVICE_INTEL_COM_INTEL_FEC_ACC100" 
    dict_list_cfg_dpdks: Dict[str, List[CfgDpdk]] = {}

    #start of methods for thread config
    @classmethod 
    def get_mock_cpu_id(cls) -> int:
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
        assert(cfg_file_name in cls.dict_cfgfile_paths.keys())

        try:
            with open(cls.dict_cfgfile_paths[cfg_file_name] + cfg_file_name, encoding="utf8") as f:

                parser = LET.XMLParser(recover=True)
                xml_tree = LET.parse(f, parser) 

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
                
                xml_tree.write(cls.dict_cfgfile_paths[cfg_file_name] + cfg_file_name)

        except Exception as e:
            sys.exit("Could not open the thread xml file: %s" %e)


    @classmethod
    def process_threads_cfg_into_xml(cls):
        for file in cls.dict_list_cfg_threads.keys():
            cls.read_and_update_threads_cfg_xml(file, cls.dict_list_cfg_threads[file])


    @classmethod
    def read_threads_yaml(cls, yaml_data: Any, cpu_resource: CpuResource):
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


    #end of methods for thread config

    #start of methods for dpdk config
    @classmethod
    def read_dpdks_yaml(cls, yaml_data: Any):
            yaml_dpdks = yaml_data["Dpdk_cfgs"]
            dpdks = yaml_data["Dpdk_cfgs"]

            #print(yaml_threads)
            for num in dpdks:
                #print (num, ": ", yaml_threads[num])
                cfg_objs = dpdks[num]
                for cfg in cfg_objs:
                    dpdk = cfg_objs[cfg]
                    cfg_name = cfg + ".xml"
                    for dpdk_field in dpdk:
                        cls.load_dpdk_cfg(cfg_name, dpdk_field, dpdk[dpdk_field])

    @classmethod
    def load_dpdk_cfg(cls, cfg_file: str, cfg_field: str, cfg_val: int):
        a_dpdk_cfg = CfgDpdk()
        a_dpdk_cfg.cfg_file_name = cfg_file
        a_dpdk_cfg.mem_size_str = cfg_field
        a_dpdk_cfg.mem_size_val = cfg_val

        env_value = get_env_variable(cls.env_acc_mode_str)
        if(env_value is None):
            a_dpdk_cfg.base_band_fec_mode_val = 0
        else:
            a_dpdk_cfg.base_band_fec_mode_val = 1
            a_dpdk_cfg.base_band_device_val = env_value
            #print("env value ", env_value)


        if cfg_file not in cls.dict_list_cfg_dpdks.keys():
            cls.dict_list_cfg_dpdks[cfg_file] = [a_dpdk_cfg] 
        else:
            cls.dict_list_cfg_dpdks[cfg_file].append(a_dpdk_cfg)

    @classmethod
    def update_dpdk_cfg_xml(cls, cfg_file_name: str, dpdks: List[CfgDpdk]):
        assert(cfg_file_name in cls.dict_cfgfile_paths.keys())

        try:
            with open(cls.dict_cfgfile_paths[cfg_file_name] + cfg_file_name, encoding="utf8") as f:

                parser = LET.XMLParser(recover=True)
                xml_tree = LET.parse(f, parser) 

                root = xml_tree.getroot()
                root_dpdks = root.find('DPDK')
                #print(LET.tostring(root_threads, encoding="unicode", pretty_print = True))

                for dpdk in dpdks:
                    xml_dpdk_mem_size = root_dpdks.find(dpdk.mem_size_str)
                    if xml_dpdk_mem_size == None:
                        print("Cound not find the existing dpdk memory size config")
                    else: 
                        xml_dpdk_mem_size.text = str(dpdk.mem_size_val)
                        #print("Update thread: ", thread.thread_name, thread.get_xml_text_value_str())

                    #update the mode
                    xml_dpdk_fec_mode = root_dpdks.find(CfgDpdk.base_band_fec_mode_str)
                    if xml_dpdk_fec_mode == None:
                        print("Cound not find the existing dpdk fec mode config")
                    else:
                        xml_dpdk_fec_mode.text = str(dpdk.base_band_fec_mode_val)
                    
                    xml_dpdk_device = root_dpdks.find(CfgDpdk.base_band_device_str)
                    if xml_dpdk_device == None:
                        print("Cound not find the existing dpdk device config")
                    else:
                        #print("dpdk device value: ", dpdk.base_band_device_val)
                        xml_dpdk_device.text = dpdk.base_band_device_val

                xml_tree.write(cls.dict_cfgfile_paths[cfg_file_name] + cfg_file_name)

        except Exception as e:
            sys.exit("Could not open the dpdk xml file: %s" %e)

    @classmethod
    def process_update_dpdk_cfg_xml(cls):
        for cfg_file in cls.dict_list_cfg_dpdks.keys():
            cls.update_dpdk_cfg_xml(cfg_file, cls.dict_list_cfg_dpdks[cfg_file]);

    #end of methods for dpdk config

    #start of commond methods
    @classmethod
    def read_cfg_yaml(cls, cfg_yaml, cpu_resource: CpuResource):

        #print("read_cfg_yaml: ", cfg_yaml)
        try:
            with open(cfg_yaml) as fsrc:

                try:
                    yaml_data = yaml.safe_load(fsrc)
                except Exception as e:
                    sys.exit("Could not parse the yaml file: %s" %e)

                if "Cfg_file_paths" in yaml_data.keys():
                    cls.read_cfg_file_paths_yaml(yaml_data)
                else:
                    sys.exit("Could not find file path bloack in yaml file: %s" %cfg_yaml)

                if "Threads" in yaml_data.keys():
                    cls.read_threads_yaml(yaml_data, cpu_resource)

                if "Dpdk_cfgs" in yaml_data.keys():
                    cls.read_dpdks_yaml(yaml_data)

        except Exception as e:
            sys.exit("Could not open the cfg yaml file: %s " %e)


    @classmethod
    def read_cfg_file_paths_yaml(cls, yaml_data: Any):
        #print("read_cfg_file_paths_yaml")
        yaml_cfg_file_paths = yaml_data["Cfg_file_paths"]
        for num in yaml_cfg_file_paths:
            for file_name in yaml_cfg_file_paths[num]:
                cls.dict_cfgfile_paths[file_name + ".xml"] = yaml_cfg_file_paths[num][file_name] 
        print(cls.dict_cfgfile_paths)           
 
    @classmethod
    def process_cfg_xml(cls, yaml_file_name, cpu_resource: CpuResource):
        #print("yaml file is: ", yaml_file_name)
        cls.read_cfg_yaml(yaml_file_name, cpu_resource)
        cls.process_threads_cfg_into_xml()
        cls.process_update_dpdk_cfg_xml()

    #end of commond methods

'''
def main(name, argv):
    #CfgThreadData.update_threads_cfg_xml()
    CfgDpdkData.process_dpdk_cfg("threads.yaml")


if __name__ == '__main__':
    main(sys.argv[0], sys.argv[1:])
'''