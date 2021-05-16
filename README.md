## How to compile

The compile step: https://gist.githubusercontent.com/jianzzha/e824b28c174172e8d90f3c2cba900e1d/raw/62a4808e8fb3972416e64829737cdd259e01a470/gistfile1.txt

## How to run flexran from podman for software FEC test

```podman run --name flexran -d --cap-add SYS_ADMIN --cap-add IPC_LOCK --cap-add SYS_NICE --mount 'type=bind,src=/sys,dst=/sys' --mount 'type=bind,src=/dev/hugepages,destination=/dev/hugepages' flexran:latest sleep infinity```

From terminal 1, run ```podman exec -it flexran sh```. The start directory is /opt/auto, run ```./setup.sh```. This will drop into the  PHY console.

Or instead of running the pod in deamon mode, one can directly drop into the PHY console in this way:
```podman run --name flexran -it --cap-add SYS_ADMIN --cap-add IPC_LOCK --cap-add SYS_NICE --mount 'type=bind,src=/sys,dst=/sys' --mount 'type=bind,src=/dev/hugepages,destination=/dev/hugepages' flexran:latest ./setup.sh```

From terminal 2, run ```podman exec -it flexran sh```. The start directory is /opt/auto, run ```./setup.sh l2```. This will drop into the TESTMAC console. From the console, do ```runall 0``` to kick off the test.

## How to run flexran from Openshift for software FEC test

```
cat <<EOF  | oc create -f -
apiVersion: v1 
kind: Pod 
metadata:
  name: flexran
spec:
  restartPolicy: Never
  containers:
  - name: flexran 
    image: 192.168.222.1:5000/flexran 
    imagePullPolicy: Always 
    command:
      - sleep
      - "36000" 
    securityContext:
      privileged: true
    volumeMounts:
    - mountPath: /dev/hugepages
      name: hugepage
    - mountPath: /sys
      name: sys
    - mountPath: /lib/modules
      name: modules
    - mountPath: /dev
      name: dev
    resources:
      limits:
        hugepages-1Gi: 16Gi
        memory: 16Gi
        cpu: 8
      requests:
        hugepages-1Gi: 16Gi
        memory: 16Gi
        cpu: 8
  volumes:
  - name: hugepage
    emptyDir:
      medium: HugePages
  - name: sys
    hostPath:
      path: /sys
  - name: modules
    hostPath:
      path: /lib/modules
  - name: dev
    hostPath:
      path: /dev
  nodeSelector:
    node-role.kubernetes.io/worker-cnf: ""
EOF
```

After the pod is started, on terminal 1 run ```oc exec -it flextan sh```. This will start in /opt/auto directory. Kickoff the PHY by ```./setup.sh```.

on terminal 2 run ```oc exec -it flexran sh```. This will start in /opt/auto directory. Kick off the TESTMAC by ```./setup.sh l2```. From the TESTMAC console, execute ```runall 0``` to start the test.

To prevent the worker node from stalling during the test, two enviroment variables are supported. To raise the rcuc priority to 20 and ksoftirqd to 11, in the pod yaml env section, set rcuc=20 and ksoftirqd=11.  
