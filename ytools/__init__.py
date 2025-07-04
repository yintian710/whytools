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

if __name__ == '__main__':
    pass
