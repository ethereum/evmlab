# Taken from https://github.com/paritytech/parity-ethereum/blob/master/docker/alpine/Dockerfile
FROM alpine:edge AS builder

# show backtraces
ENV RUST_BACKTRACE 1

RUN apk add --no-cache \
  build-base \
  cargo \
  cmake \
  eudev-dev \
  linux-headers \
  perl \
  rust git

RUN git clone https://github.com/paritytech/parity-ethereum /parity
WORKDIR /parity
RUN cargo build --release --target x86_64-alpine-linux-musl --verbose -p evmbin
RUN strip target/x86_64-alpine-linux-musl/release/parity-evm


FROM alpine:edge

# show backtraces
ENV RUST_BACKTRACE 1

RUN apk add --no-cache \
  libstdc++ \
  eudev-libs \
  libgcc

RUN addgroup -g 1000 parity \
  && adduser -u 1000 -G parity -s /bin/sh -D parity

USER parity
COPY --chown=parity:parity --from=builder /parity/target/x86_64-alpine-linux-musl/release/parity-evm ./

#ENTRYPOINT ["./parity"]
