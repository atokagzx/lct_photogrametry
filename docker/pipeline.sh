#!/bin/bash

xhost +local:docker || true

ROOT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
docker run \
      -e "DISPLAY" \
      -e "QT_X11_NO_MITSHM=1" \
      -v "/tmp/.X11-unix:/tmp/.X11-unix:rw" \
      -e XAUTHORITY \
      -e "XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR}" \
      -v $ROOT_DIR:/root/workspace \
      -v $ROOT_DIR/cache:/root/.cache \
      --net=host \
      --privileged \
      --name lct_photogrametry lct_photogrametry-img 