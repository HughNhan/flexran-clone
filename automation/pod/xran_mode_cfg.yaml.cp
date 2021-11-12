Cfg_file_paths:
  1: 
    phycfg_xran: cfg_examples/
  2: 
    xrancfg_sub6_oru: cfg_examples/
  3: 
    testmac_cfg: cfg_examples/
    

Threads:
  1:
    phycfg_xran:
      systemThread:
        pri: 0
      FpgaDriverCpuInfo:
        pri: 0
      FrontHaulCpuInfo:
        pri: 0
    testmac_cfg:
      systemThread:
        pri: 0
      runThread:
        pri: 89
      urllcThread:
        pri: 90
  2:
    phycfg_xran:
      timerThread:
        pri: 96 
      radioDpdkMaster:
        pri: 99
  3:
    test_mode: xran
    xrancfg_sub6_oru:
      xRANThread:
        pri: 94
      xRANWorker:
        pri: 95
        format: core_mask
  4:
    testmac_cfg:
      wlsRxThread:
        pri: 90



Dpdk_cfgs:
  1:
    phycfg_xran:
      dpdkMemorySize: 4096
      dpdkEnvModeStr: PCIDEVICE_INTEL_COM_INTEL_FEC_5G
  2:
    xrancfg_sub6_oru:
      test_mode: xran

