from ethereum/client-go:alltools-latest as geth


from jfloff/alpine-python:recent-onbuild
COPY --from=geth /usr/local/bin/evm /evm
ADD . /app/ 

#ENTRYPOINT ["/bin/sh","-c","/bin/bash"]
#CMD ["python3", "app/opviewer.py","--hash","0x9dbf0326a03a2a3719c27be4fa69aacc9857fd231a8d9dcaede4bb083def75ec","-g","/evm","--no-docker"]
CMD "./app/dockerboot.sh"
