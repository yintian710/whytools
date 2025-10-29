# -*- coding: utf-8 -*-
"""
@File    : sign.py
@Author  : yintian
@Date    : 2025/10/29 14:38
@Software: PyCharm
@Desc    : 
"""
import uuid

from ytools.utils.encrypt import md5


def get_own_id():
    node = uuid.getnode()
    return md5(str(node))


if __name__ == '__main__':
    pass
