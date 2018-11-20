# Build stage 
FROM alpine:latest as builder
RUN apk add --no-cache \
        git \
        cmake \
        g++ \
        make \
        linux-headers
#        leveldb-dev --repository http://dl-cdn.alpinelinux.org/alpine/edge/testing/
RUN git clone --recursive https://github.com/ethereum/aleth --single-branch --depth 1
RUN mkdir /build
RUN cd /build && cmake /aleth -DHUNTER_JOBS_NUMBER=$(nproc)
RUN cd /build && make -j $(nproc)
#RUN cd /build && cmake --build .

FROM alpine:latest
RUN apk add --no-cache \
        libstdc++ \
        leveldb --repository http://dl-cdn.alpinelinux.org/alpine/edge/testing/
COPY --from=builder /build/test/testeth /usr/bin/testeth

ENTRYPOINT ["/usr/bin/testeth"]
