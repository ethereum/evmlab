#! /usr/bin/env python
# -*- coding: utf-8 -*-
# Author : <github.com/tintinweb>
import json
import evmlab.tools.statetests.rndval as rndval


def load_settings():
    # load settings from RandomCodeOptions.json and directly write to class attribs
    #  - eg. Address.addresses {}
    # todo: configparser or json
    raise NotImplementedError


def walk_iterable(d, prn):
    if isinstance(d, dict):
        for k, v in d.items():
            if isinstance(v, dict):
                walk_iterable(d=v, prn=prn)
            elif isinstance(v, list):
                walk_iterable(d=v, prn=prn)
            else:
                prn(d, k)  # provide dict and key for substitutaion
    elif isinstance(d, list):
        for k, v in enumerate(d):
            if isinstance(v, dict):
                walk_iterable(d=v, prn=prn)
            elif isinstance(v, list):
                walk_iterable(d=v, prn=prn)
            else:
                prn(d, k)  # provide dict and key for substitutaion


def get_classes():
    for cls in (getattr(rndval,_) for  _ in dir(rndval) if _.startswith("Rnd") and not _.endswith("Type") ):
        if hasattr(cls, "placeholder"):
            yield cls


def process_template(d):
    placeholders = {cls.placeholder:cls for cls in get_classes()}

    def substitute(d,k):
        sub = placeholders.get(d[k])  # substitute with rnd class, otherwise keep value
        if sub:
            d[k] = sub()

    walk_iterable(d, substitute)
    return d


class RandomTestsJsonEncoder(json.JSONEncoder):
    """ Custom JSONEncoder to encode rndval objects to str """
    def default(self, obj):
        if isinstance(obj, rndval._RndBase):
            return str(obj)
        return super(RandomTestsJsonEncoder, self).default(obj)