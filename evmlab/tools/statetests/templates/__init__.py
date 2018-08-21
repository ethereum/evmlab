#! /usr/bin/env python
# -*- coding: utf-8 -*-
# Author : <github.com/tintinweb>
import copy
from . import text_based, object_based


def new(template):
    return copy.deepcopy(template)


__ALL__ = ["placeholder_based", "object_based", "new"]
