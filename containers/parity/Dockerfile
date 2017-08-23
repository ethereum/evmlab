# Docker container spec for building the master branch of parity.
FROM ubuntu:16.04

# Build parity on the fly and delete all build tools afterwards
RUN \
  # Install parity from sources
  apt-get -y update                                        && \
  apt-get install -y bash jq bc curl git make g++ gcc file    \
  binutils pkg-config openssl libssl-dev libudev-dev       && \
  curl -sSf https://static.rust-lang.org/rustup.sh         |  \
  sh -s -- --disable-sudo
RUN  git clone --depth 1 https://github.com/paritytech/parity
RUN cd parity && cargo build --release -p evmbin
RUN cd parity && echo "{}"                                                      \
  | jq ".+ {\"repo\":\"$(git config --get remote.origin.url)\"}" \
  | jq ".+ {\"branch\":\"$(git rev-parse --abbrev-ref HEAD)\"}"  \
  | jq ".+ {\"commit\":\"$(git rev-parse HEAD)\"}"               \
  > /version.json                                       && \
	cd / && cp /parity/target/release/parity-evm /parity-evm && \
	rm -rf parity && \
  /usr/local/lib/rustlib/uninstall.sh                  && \
  apt-get remove -y curl git make g++ gcc file binutils pkg-config openssl libssl-dev && \
  rm -rf /root/.cargo

ADD . /
ENTRYPOINT ["/parity-evm"]
RUN cat version.json && cat README.md

