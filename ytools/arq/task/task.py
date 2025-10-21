# -*- coding: utf-8 -*-
"""
@File    : task.py
@Author  : yintian
@Date    : 2025/10/21 10:35
@Software: PyCharm
@Desc    : 
"""
import json
from itertools import count
from uuid import uuid4

from ytools.arq import setting
from ytools.utils import magic
from ytools.utils.encrypt import SaltBase64


class Task:
    _score = count()

    def __init__(self, data, client, task_id=None, fmt=False, **kwargs):
        if fmt and setting.OBJ_DATA:
            data = magic.json_or_eval(data)
        self.data = data
        self.task_id = task_id or str(uuid4())
        self.client = client
        self.score = kwargs.get('score') or next(Task._score)

    def encode_data(self, data=None):
        data = data or self.data
        if not isinstance(data, (str, bytes)):
            data = json.dumps(data, ensure_ascii=False, default=str).encode(setting.DEFAULT_ENCODING)
        elif isinstance(data, str):
            data = data.encode(setting.DEFAULT_ENCODING)
        else:
            data = data

        if encrypt := setting.ENCRYPT:
            if callable(encrypt):
                return encrypt(data, mode="encrypt")
            else:
                return SaltBase64(key=str(encrypt), encoding=setting.DEFAULT_ENCODING).encrypt(data)
        return data

    def decode_data(self, data=None):
        data = data or self.data
        if isinstance(data, str):
            data = data.encode(setting.DEFAULT_ENCODING)
        elif isinstance(data, bytes):
            data = data
        else:
            raise TypeError("data 应为 str/bytes")
        if encrypt := setting.ENCRYPT:
            if callable(encrypt):
                data = encrypt(data, mode="decrypt")
            else:
                data = SaltBase64(key=str(encrypt), encoding=setting.DEFAULT_ENCODING).decrypt(data)
        if setting.OBJ_DATA:
            data = magic.json_or_eval(data.decode(setting.DEFAULT_ENCODING))
        return data


if __name__ == '__main__':
    pass
