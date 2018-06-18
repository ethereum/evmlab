#!/usr/bin/env python

from distutils.core import setup

version = '0.1'

setup(name='Evmlab',
      version=version,
      description='Ethereum EVM utilities',
      author='Martin Holst Swende',
      author_email='martin.swende@ethereum.org',
      license="GPLv3",
      keywords=["ethereum", "transaction", "debugger"],
      url="https://github.com/holiman/evmlab/",
      download_url="https://github.com/holiman/evmlab/tarball/v%s"%version,
      packages=['evmlab',
                'evmlab.tools',
                'evmlab.tools.reproducer'],
      package_data={'evmlab.tools.reproducer':["templates/*"]},
      install_requires=["requests", "web3", "eth-hash[pycryptodome]", "rlp>=1.0"],
      extras_require={"consolegui": ["urwid"],
                      "abidecoder": ["ethereum-input-decoder"],
                      "docker": ["docker==3.0.0"]}
      )
