# -*- coding: utf-8 -*-
"""
@File    : variable.py
@Author  : yintian
@Date    : 2025/6/18 14:18
@Software: PyCharm
@Desc    : 
"""
import time
from threading import Lock, local
from typing import Dict, Any


class CacheItem:
    expired = False

    def __init__(self, value, max_count: int = 0, expire_ts: int = 0):
        self._value = value
        self.start_time = time.time()
        self.max_count = max_count
        self.expire_ts = expire_ts
        self.use_count = 0

    @property
    def value(self):
        if not self.update():
            return self._value

    def update(self, use=True):
        if not self.expired:
            if use:
                self.use_count += 1
            if self.expire_ts and self.expire_ts + self.start_time > time.time():
                self.expired = True
            if 0 < self.max_count <= self.use_count:
                self.expired = True
        return self.expired

    def set_expire(self, max_count=0, expire_ts=0):
        max_count > 0 and setattr(self, 'max_count', max_count)
        expire_ts > 0 and setattr(self, 'expire_ts', expire_ts)

    def __repr__(self):
        return f"<CacheItem [value: {self._value}| expired: {self.expired}]>"


class VariableG:
    def __init__(self):
        self._map: Dict[str, CacheItem] = {}
        self._lock = Lock()
        self.__setitem__ = self.setattr

    def __getattr__(self, item):
        if item in self._map:
            return self[item]
        return None

    def setattr(self, key, value):
        return self.__setitem__(key, value)

    def __setitem__(self, key, value):
        self._map[key] = CacheItem(value)

    def __getitem__(self, key):
        item = self._map.get(key)
        if item is None:
            return None
        if item.update(use=False):
            self._map.pop(key)
            return None
        return item.value

    def set(self, key: str, value: Any, **kwargs):
        self._map[key] = CacheItem(value, **kwargs)

    def set_expire(self, key, max_count=0, expire_ts=0):
        if item := self._map.get(key):
            item.set_expire(max_count, expire_ts)

    def delete(self, key):
        self._map.pop(key, None)

    def __enter__(self):
        self._lock.acquire()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._lock.release()

    def __repr__(self):
        return f"<VariableG [map: {self._map}]>"


class VariableT(local, VariableG):
    def __init__(self):
        super().__init__()
        self._lock = None

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def __repr__(self):
        return f"<VariableT [map: {self._map}]>"
