# run flexran from podman

podman run --name flexran -d --cap-add SYS_ADMIN --cap-add IPC_LOCK --cap-add SYS_NICE --mount 'type=bind,src=/sys,dst=/sys' --mount 'type=bind,src=/dev/hugepages,destination=/dev/hugepages' flexran:latest sleep infinity
