from ethereum/client-go:alltools-latest as geth


from jfloff/alpine-python:recent-onbuild
COPY --from=geth /usr/local/bin/evm /evm
ADD . /app/ 

CMD ["bash"]
