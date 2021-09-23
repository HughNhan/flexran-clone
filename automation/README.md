###Flexran automation steps

1. OCP cluster install
   a. ocp_cluster_install.sh
   b. ocp_cluster_cleanup.sh


2. Performance operator install and setup 
   performance profile and MCP
   a. performance_operator_install.sh
   b. performance_operator_cleanup.sh


3. SRIOV operatoer install, network policy setup, bastion SRIOV setup 
   performance profile and MCP
   a. sriov_operator_install.sh
   b. sriov_operator_cleanup.sh


4. PTP operator install and setup 
   a. ptp_operator_install.sh
   b. ptp_operator_cleanup.sh

  
5. pod setup 
   a. pod_create.sh
   b. pod_destroy.sh

6. Exec l1 and testmac
   a. exec_li_testmac.sh
  

7. Process test results and collect artifacts
   a. process_test_results.sh
   b. collect_artifacts.sh

8. Clean up 
   cleanup.sh

### directory of pod
Files scripts will be copied to flexran pod
   