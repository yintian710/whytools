# -*- coding: utf-8 -*-
"""
@File    : encrypt.py
@Author  : yintian
@Date    : 2025/7/23 16:39
@Software: PyCharm
@Desc    : 
"""
import base64
import hashlib
import json
import sys
from hashlib import md5 as raw_md5

from ytools.utils.magic import json_or_eval
from ytools.utils.magic_for_class import CustomMeta

default_encoding = sys.getdefaultencoding()


def md5(obj, encoding=default_encoding):
    if not isinstance(obj, (str, bytes)):
        obj = json.dumps(obj, default=str, indent=0).encode(encoding=encoding)
    if isinstance(obj, str):
        obj = obj.encode(encoding=encoding)

    return raw_md5(obj).hexdigest()


def to_b64(obj, encoding=default_encoding):
    if not isinstance(obj, (str, bytes)):
        obj = json.dumps(obj, default=str, indent=0).encode(encoding=encoding)
    if isinstance(obj, str):
        obj = obj.encode(encoding=encoding)
    return base64.b64encode(obj).decode(encoding=encoding)


def from_b64(obj, fmt=True, encoding=default_encoding):
    obj = base64.b64decode(obj)
    if callable(fmt):
        return callable(obj)
    elif fmt:
        if encoding:
            obj = obj.decode(encoding=encoding)
        return json_or_eval(obj)
    return obj


class SaltBase64(metaclass=CustomMeta, singleton=True):
    def __init__(self, key: str, encoding='utf-8'):
        self.encoding = encoding
        self.key = key.encode(self.encoding)

    def _generate_salt(self, data: bytes) -> bytes:
        """生成基于密钥和数据的盐值"""
        salt_input = self.key + data
        salt_hash = hashlib.sha256(salt_input).digest()
        return salt_hash[:8]  # 使用前8字节作为盐值

    def encrypt(self, data: bytes) -> bytes:
        """加密：XOR(明文, 盐值) -> Base64"""
        salt = self._generate_salt(data)

        # XOR加密
        encrypted_data = bytes(a ^ b for a, b in zip(data, salt * ((len(data) // len(salt)) + 1)))

        # 组合盐值和加密数据
        combined = salt + encrypted_data

        # Base64编码
        return base64.b64encode(combined)

    def decrypt(self, encrypted_b64: bytes) -> bytes:
        """解密：Base64 -> XOR(密文, 盐值)"""
        # Base64解码
        combined = base64.b64decode(encrypted_b64)

        # 提取盐值和加密数据
        salt_size = 8
        salt = combined[:salt_size]
        encrypted_data = combined[salt_size:]

        # XOR解密
        decrypted_data = bytes(a ^ b for a, b in zip(encrypted_data, salt * ((len(encrypted_data) // len(salt)) + 1)))

        return decrypted_data.decode(self.encoding, errors='ignore').encode(encoding=self.encoding)


#
if __name__ == '__main__':
    print(md5('123'))
