## How to run flexran from podman for software FEC test

```podman run --name flexran -d --cap-add SYS_ADMIN --cap-add IPC_LOCK --cap-add SYS_NICE --mount 'type=bind,src=/sys,dst=/sys' --mount 'type=bind,src=/dev/hugepages,destination=/dev/hugepages' flexran:latest sleep infinity```

From terminal 1, run ```podman exec -it flexran sh```. The start directory is /opt/auto, run ```./setup.sh```. This will drop into the  PHY console.

From terminal 2, run ```podman exec -it flexran sh```. The start directory is /opt/auto, run ```./l2.sh```. This will drop into the TESTMAC console. From the console, do ```runall 0``` to kick off the test.
