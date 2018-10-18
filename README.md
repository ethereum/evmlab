[![Build Status](https://api.travis-ci.org/ethereum/evmlab.svg?branch=master)](https://travis-ci.org/ethereum/evmlab/)

# EVM lab utilities

This package contains various tools to interact with the Ethereum virtual machine.


Please refer to the [Wiki](https://github.com/ethereum/evmlab/wiki) for more information and howto's.


![screenshot](https://raw.githubusercontent.com/holiman/evmlab/master/docs/example2.png)


## Installation

#### From source:

Consider creating a virtualenv.

    #> virtualenv -p python3 .env3
    #> . .env3/bin/activate
    #> python3 -m pip install -r requirements.txt
    #> python3 setup.py install
    #> python3 -m evmlab  # verify installation

#### From PIP:


    #> python3 -m pip install evmlab[consolegui,abidecoder,docker]
    #> python3 -m evmlab  # verify installation

EVMLab comes with a commandline utility that can be invoked by calling `python3 -m evmlab <subcommand> <args>`


# Running it

The easiest way to get it working is to use a docker image. 

```
docker build . -t evmlab && docker run -it evmlab
```

The docker image should also be available at hub.docker.com, as an automated build:

```
docker pull holiman/evmlab && docker run -it holiman/evmlab
```
