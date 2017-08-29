#Download base image ubuntu 14.04
FROM ubuntu:14.04

# Update Ubuntu Software repository
RUN     apt-get update \
    &&  apt-get install git -y \
    #&&  cd /home && git clone --depth 1 --recursive https://github.com/ethereum/cpp-ethereum.git \
    &&  cd /home && git clone --depth 1 --recursive https://github.com/cdetrio/cpp-ethereum --branch evmlab-trace --single-branch \
    &&  git clone --depth 1 --recursive https://github.com/winsvega/solidity.git \
    &&  apt-get install curl libboost-all-dev libleveldb-dev libcurl4-openssl-dev libmicrohttpd-dev libminiupnpc-dev libgmp-dev -y \
    &&  cd cpp-ethereum && ./scripts/install_cmake.sh --prefix /usr/local \
    &&  ./scripts/install_deps.sh \
    &&  mkdir build && cd build && cmake .. -DSTATIC_LINKING=1 && make \
    &&  cp ./test/testeth ../../testeth \
    &&  cd /home/solidity \
    &&  ./scripts/install_deps.sh \
    &&  mkdir build && cd build && cmake .. -DSTATIC_LINKING=1 && make \
    &&  cp ./lllc/lllc /bin/lllc \
    &&  cd /home && rm -r /home/cpp-ethereum && rm -r /home/solidity \
    &&  apt-get remove curl libboost-all-dev libcurl4-openssl-dev libmicrohttpd-dev libminiupnpc-dev libgmp-dev -y \
    &&  apt-get autoremove -y \
    &&  apt purge

ENTRYPOINT ["/home/testeth"]