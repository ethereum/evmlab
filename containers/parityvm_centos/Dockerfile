# From https://github.com/paritytech/parity-ethereum/blob/master/scripts/docker/centos/Dockerfile.build
FROM centos:latest AS builder

WORKDIR /build

#ADD . /build/parity-ethereum

RUN yum -y update && \
    yum install -y systemd-devel git make gcc-c++ gcc file binutils && \
    curl -L "https://cmake.org/files/v3.12/cmake-3.12.0-Linux-x86_64.tar.gz" -o cmake.tar.gz && \
    tar -xzf cmake.tar.gz && \
    cp -r cmake-3.12.0-Linux-x86_64/* /usr/ && \
    curl https://sh.rustup.rs -sSf | sh -s -- -y && \
    PATH=/root/.cargo/bin:$PATH && \
    RUST_BACKTRACE=1 && \
    rustc -vV && \
    cargo -V && \
    gcc -v && \
    g++ -v && \
    cmake --version

RUN git clone https://github.com/paritytech/parity-ethereum /parity
WORKDIR /parity
RUN    PATH=/root/.cargo/bin:$PATH && \
	 cargo build --release --verbose -p evmbin
RUN    PATH=/root/.cargo/bin:$PATH && \
	strip /parity/target/release/parity-evm

FROM centos:latest
# show backtraces
ENV RUST_BACKTRACE 1


#USER parity
COPY --from=builder /parity/target/release/parity-evm ./

#ENTRYPOINT ["./parity"]


