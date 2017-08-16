#!/bin/bash
#(cd geth && docker build --no-cache . -t holiman/gethvm && docker push holiman/gethvm)
#(cd parity && docker build --no-cache . -t holiman/parityvm && docker push holiman/parityvm)
(cd testeth && docker build --no-cache . -t holiman/testeth && docker push holiman/testeth)

