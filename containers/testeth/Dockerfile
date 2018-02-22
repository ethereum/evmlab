# Build stage 
FROM alpine:latest as builder
RUN apk add --no-cache \
        git \
        cmake \
        g++ \
        make \
        linux-headers \
        leveldb-dev --repository http://dl-cdn.alpinelinux.org/alpine/edge/testing/
RUN git clone --recursive https://github.com/ethereum/testeth --branch develop --single-branch --depth 1
RUN mkdir /build
# See https://github.com/ethereum/cpp-ethereum/issues/4834
RUN cd /build && cmake /testeth -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_BUILD_TYPE=RelWithDebInfo -DTOOLS=OFF
#RUN cd /build && cmake /testeth -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_BUILD_TYPE=RelWithDebInfo -DTOOLS=OFF -DEVM_OPTIMIZE=0 -DSTATIC_LINKING=1
RUN cmake --version
RUN cd /build && make -j1 && make install; exit 0
RUN cd /build && cp -r deps/lib64/libbinaryen.a deps/lib/; cp -r deps/lib64/libmpir.a deps/lib/
RUN cd /build && make -j1 && make install

# Install stage 
FROM alpine:latest
RUN apk add --no-cache \
        libstdc++ \
        leveldb --repository http://dl-cdn.alpinelinux.org/alpine/edge/testing/
COPY --from=builder /build/test/testeth /usr/bin/testeth

#ENTRYPOINT ["/usr/bin/testeth"]
