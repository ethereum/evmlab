from node:alpine

WORKDIR /ethereum

RUN apk update && apk upgrade && apk add --no-cache g++ python python-dev git make bash && git clone https://github.com/ethereumjs/ethereumjs-vm && cd ethereumjs-vm  && npm install

ENTRYPOINT ["node", "/ethereum/ethereumjs-vm/tests/tester.js" ]
