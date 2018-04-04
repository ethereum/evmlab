#!/bin/bash

docker_repo="holiman"
#docker_repo="cdetrio"

# (cd geth && docker build --no-cache . -t $docker_repo/gethvm && docker push $docker_repo/gethvm)
# (cd parity && docker build --no-cache . -t $docker_repo/parityvm && docker push $docker_repo/parityvm)
# (cd testeth && docker build --no-cache . -t $docker_repo/testeth && docker push $docker_repo/testeth)
(cd hera && docker build . -t $docker_repo/hera) ##  && docker push $docker_repo/testeth)

# build ethereumjs docker images
# (cd ethereumjs && docker build --no-cache . -t jwasinger/ethereumjs-vm)
# build geth docker image
#(cd std-geth && docker build --no-cache . -t $docker_repo/std-gethvm)
# build cpp docker image
#(cd std-cpp-ethereum && docker build --no-cache . -t $docker_repo/std-cppvm )
# build parity docker image
#(cd std-parity && docker build --no-cache . -t $docker_repo/std-parityvm)
# build python docker image
#(cd pyethereum && docker build --no-cache . -t $docker_repo/std-pyethvm)
