# Docker container spec for building a parity branch for standardized vm traces
FROM ubuntu:16.04 as builder

# Build parity on the fly and delete all build tools afterwards
RUN \
  apt-get -y update                                        && \
  apt-get install -y bash jq bc curl git make g++ gcc file    \
  binutils pkg-config openssl libssl-dev libudev-dev
RUN curl https://sh.rustup.rs -sSf | sh -s -- -y
ENV PATH /root/.cargo/bin:$PATH
RUN  git clone --depth 1 https://github.com/paritytech/parity
#RUN git clone --depth 1 --branch evmlab-trace https://github.com/cdetrio/parity
RUN cd parity && cargo build --release -p evmbin
RUN cd parity && echo "{}"                                       \
  | jq ".+ {\"repo\":\"$(git config --get remote.origin.url)\"}" \
  | jq ".+ {\"branch\":\"$(git rev-parse --abbrev-ref HEAD)\"}"  \
  | jq ".+ {\"commit\":\"$(git rev-parse HEAD)\"}"               \
  > /version.json                                             && \
  cd / && cp /parity/target/release/parity-evm /parity-evm    && \
  rm -rf parity && rustup self uninstall -y                   && \
  apt-get remove -y curl git make g++ gcc file binutils pkg-config openssl libssl-dev && \
  rm -rf /root/.cargo


from ubuntu:16.04
RUN apt-get -y update && apt-get install -y libssl-dev libudev-dev
COPY --from=builder /parity-evm /parity-evm
COPY --from=builder /version.json /version.json
ADD . /
#ENTRYPOINT ["/parity-evm"]
RUN cat version.json
