# Docker container spec for building the master branch of go-ethereum.
#
# The build process it potentially longer running but every effort was made to
# produce a very minimalistic container that can be reused many times without
# needing to constantly rebuild.
FROM alpine:latest

# Build go-ethereum on the fly and delete all build tools afterwards
RUN \
  apk add --update bash jq go git make gcc musl-dev              \
  	  ca-certificates linux-headers                           
RUN git clone --depth 1 https://github.com/ethereum/go-ethereum 
RUN (cd go-ethereum && build/env.sh go run build/ci.go install ./cmd/evm)
RUN cp /go-ethereum/build/bin/evm /evm 
RUN cd go-ethereum                                             && \
  echo "{}"                                                      \
  | jq ".+ {\"repo\":\"$(git config --get remote.origin.url)\"}" \
  | jq ".+ {\"branch\":\"$(git rev-parse --abbrev-ref HEAD)\"}"  \
  | jq ".+ {\"commit\":\"$(git rev-parse HEAD)\"}"               \
	> /version.json                                            && \
  apk del go git make gcc musl-dev linux-headers              && \
  rm -rf /go-ethereum && rm -rf /var/cache/apk/*

ADD . /
ENTRYPOINT ["/evm"]
RUN cat version.json && cat README.md
