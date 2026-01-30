# -*- coding: utf-8 -*-
"""
@File    : __init__.py.py
@Date    : 2024/4/15 下午7:28
@Author  : yintian
@Desc    : 
"""

from ytools.log import logger
from ytools.version import get_version
from ytools.utils.magic import empty

__version__ = get_version(path=__file__)

G = T = C = None


def init_var(name: str):
    global G, T, C
    match name:
        case 'G':
            from ytools.utils.variable import VariableG
            G = VariableG()
        case 'T':
            from ytools.utils.variable import VariableT
            T = VariableT()
        case 'C':
            from ytools.utils.variable import VariableC
            C = VariableC()
        case _:
            print(f"请输入: G/T/C")


if __name__ == '__main__':
    pass
