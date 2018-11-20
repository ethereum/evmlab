#
# Omnitest docker image
# 
# The idea behind this docker image, is to be used to assist during creation of tests. 
# It should spin up a web server, where the user can drag-n-drop and click to create prestate
# accounts, etc, and add code snippets. 
#
# This is then sent to the server, which can translate from general statetest into statetests, 
# and execute the statetests on geth or parity or testeth, and give traces back (as feedback) to 
# the user, for validation purposes. 
#
# The server should be able to handle both lll, solidity and (some form of) assembly. 



from ethereum/client-go:alltools-latest as geth
from holiman/testeth:latest as testeth
from holiman/parityvm:latest as parity


from jfloff/alpine-python:recent-onbuild
#FROM alpine:latest


RUN addgroup -g 1000 testuser && adduser -u 1000 -G testuser -s /bin/sh -D testuser

# Add geth evm

COPY --from=geth /usr/local/bin/evm /evm

# Add parity parity-evm
ENV RUST_BACKTRACE 1
RUN apk add --no-cache \
  # libstdc++ is needed by both testeth and parity
  libstdc++ \
  eudev-libs \
  libgcc


COPY --chown=testuser:testuser --from=parity /parity-evm /parity-evm


# Add testeth, requries libstdc++

#RUN apk add --no-cache libstdc++
COPY --from=testeth /usr/bin/testeth /testeth

# Todo: add lllc (lll compiler)


