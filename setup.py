#!/usr/bin/env python

from distutils.core import setup

setup(name='Evmlab',
      version='0.1',
      description='Ethereum EVM utilities',
      author='Martin Holst Swende',
      author_email='martin.swende@ethereum.org',
      keywords=["ethereum", "transaction", "debugger"],
      url="https://github.com/holiman/evmlab/",
      #download_url="https://github.com/holiman/evmlab/tarball/<tag>",
      packages=['evmlab'],
      install_requires=["requests", "web3", "urwid", "eth-hash[pycryptodome]", "rlp>=1.0", "docker==3.0.0"],
      )
