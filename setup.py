#!/usr/bin/env python
"""
deps:
*) pip install --upgrade pip wheel setuptools twine
publish:
1) #> python setup.py sdist bdist_wheel
2) #> twine upload dist/*   #<specific specific wheel if needed>; --repository <testpypi> or  --repository-url <testpypi-url>
"""
import os
from setuptools import setup, find_packages


def read(fname):
    fpath = os.path.join(os.path.dirname(__file__), fname)
    fd = open(fpath, 'r')
    data = fd.read()
    fd.close()
    return data


version = '0.3.1'  # keep this in sync with the last release tag!

setup(name='Evmlab',
      version=version,
      description='Ethereum EVM utilities',
      author='Martin Holst Swende',
      author_email='martin.swende@ethereum.org',
      license="GPLv3",
      keywords=["ethereum", "transaction", "debugger"],
      url="https://github.com/ethereum/evmlab/",
      download_url="https://github.com/ethereum/evmlab/tarball/v%s" % version,
      # generate rst from .md:  pandoc --from=markdown --to=rst README.md -o README.rst (fix diff section and footer)
      long_description=read("README.md") if os.path.isfile("README.md") else "",
      # for pypi.org; empty because we do not ship Readme.md with the package. may otherwise fail on install
      long_description_content_type='text/markdown',  # requires twine and recent setuptools
      packages=find_packages(),
      package_data={'evmlab.tools.reproducer': ["templates/*"]},
      install_requires=["requests",
                        "web3",
                        "eth-hash[pycryptodome]",
                        "rlp>=1.0",
                        "evmdasm"],
      extras_require={"consolegui": ["urwid"],
                      "abidecoder": ["ethereum-input-decoder"],
                      "docker": ["docker==3.0.0"],
                      "fuzztests": ["docker==3.0.0"],
                      }
      )
