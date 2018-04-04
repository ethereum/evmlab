FROM ubuntu:xenial

RUN apt update -y && apt install -y \
        git \
        cmake \
        g++ \
        make \
        libleveldb-dev libsnappy-dev \
        curl \
        sudo

RUN curl -sL https://deb.nodesource.com/setup_8.x | sudo -E bash - && \
    apt install -y \
        nodejs \
        bash jq bc \
        python3 \
        python

#RUN git clone --recursive https://github.com/ethereum/cpp-ethereum --branch develop --single-branch --depth 1
RUN git clone https://github.com/jwasinger/cpp-ethereum --branch ewasm-json-trace --single-branch
RUN cd cpp-ethereum && git submodule update --init
RUN cd cpp-ethereum/hera && git fetch origin && git checkout evm-trace

RUN cd cpp-ethereum && echo "{}"                                         \
          | jq ".+ {\"repo\":\"$(git config --get remote.origin.url)\"}" \
          | jq ".+ {\"branch\":\"$(git rev-parse --abbrev-ref HEAD)\"}"  \
          | jq ".+ {\"commit\":\"$(git rev-parse HEAD)\"}"               \
          > /cpp-ethereum-version.json

RUN cd cpp-ethereum/hera && echo "{}"                                    \
          | jq ".+ {\"repo\":\"$(git config --get remote.origin.url)\"}" \
          | jq ".+ {\"branch\":\"$(git rev-parse --abbrev-ref HEAD)\"}"  \
          | jq ".+ {\"commit\":\"$(git rev-parse HEAD)\"}"               \
          > /hera-version.json

RUN mkdir -p build
RUN cd build && cmake ../cpp-ethereum -DCMAKE_BUILD_TYPE=RelWithDebInfo -DHERA=ON -DHERA_DEBUGGING=ON -DHERA_EVM2WASM=ON -DHERA_EVM2WASM_EVM_TRACE=ON
RUN cd build && make -j8
RUN cd build && make install

RUN cp cpp-ethereum/scripts/jsonrpcproxy.py /jsonrpcproxy.py
ADD ewasm-testnet-cpp-config.json /ewasm-testnet-cpp-config.json

# ADD cpp-eth.sh /cpp-eth.sh

#USER builder
#WORKDIR /home/builder

# Export the usual networking ports to allow outside access to the node
EXPOSE 8545 30303

# ENTRYPOINT ["/build/test/testeth"]
