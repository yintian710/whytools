# -*- coding: utf-8 -*-
"""
@File    : encrypt.py
@Author  : yintian
@Date    : 2025/7/23 16:39
@Software: PyCharm
@Desc    : 
"""
import base64
import json
from hashlib import md5 as raw_md5

from ytools.utils.magic import json_or_eval


def md5(obj, encoding=None):
    if not isinstance(obj, (str, bytes)):
        obj = json.dumps(obj, default=str, indent=0).encode(encoding=encoding)
    if isinstance(obj, str):
        obj = obj.encode(encoding=encoding)

    return raw_md5(obj).hexdigest()


def to_b64(obj, encoding=None):
    if not isinstance(obj, (str, bytes)):
        obj = json.dumps(obj, default=str, indent=0).encode(encoding=encoding)
    if isinstance(obj, str):
        obj = obj.encode(encoding=encoding)
    return base64.b64encode(obj).decode(encoding=encoding)


def from_b64(obj, fmt=True, encoding=None):
    obj = base64.b64decode(obj)
    if callable(fmt):
        return callable(obj)
    elif fmt:
        if encoding:
            obj = obj.decode(encoding=encoding)
        return json_or_eval(obj)
    return obj


if __name__ == '__main__':
    pass
