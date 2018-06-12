#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
Opviewer - Ethereum Transaction Debugger
"""
import logging

import evmlab.tools.opviewer
from evmlab.tools import opviewer


if __name__ == '__main__':
    logging.basicConfig(format='[%(filename)s - %(funcName)20s() ][%(levelname)8s] %(message)s',
                        level=logging.INFO)
    opviewer.main()
