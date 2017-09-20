# Docker container spec for building the develop branch of pythereum.
FROM frolvlad/alpine-python3:latest

RUN \
  apk add --update bash jq git curl python3-dev musl-dev gcc make openssl-dev   \
         bsd-compat-headers g++ autoconf automake pkgconfig libtool libffi-dev gmp-dev && \
  curl -sSf https://bootstrap.pypa.io/get-pip.py -o get-pip.py               && \
  python3 get-pip.py                                                         && \
  git clone --depth 1 https://github.com/ethereum/pyethereum                 && \
  cd pyethereum                                                              && \
  python3 setup.py install                                                   && \
  echo "{}"                                                                    \
      | jq ".+ {\"repo\":\"$(git config --get remote.origin.url)\"}"           \
      | jq ".+ {\"branch\":\"$(git rev-parse --abbrev-ref HEAD)\"}"            \
      | jq ".+ {\"commit\":\"$(git rev-parse HEAD)\"}"                         \
      > /version.json                                                       && \
  apk del git make gcc g++ musl-dev curl pkgconfig libtool automake autoconf

ADD run_statetest.py /run_statetest.py

ADD . /
RUN cat version.json
ENTRYPOINT ["python3"]
