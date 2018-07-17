#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""
Reproducer - Ethereum Transaction Reproducer
"""
import logging
from evmlab.tools import reproducer


if __name__ == '__main__':
    logging.basicConfig(format='[%(filename)s - %(funcName)20s() ][%(levelname)8s] %(message)s',
                        level=logging.DEBUG)
    reproducer.main()
