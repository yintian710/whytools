# -*- coding: utf-8 -*-
"""
@File    : cache.py
@Date    : 2025/5/8 下午2:39
@Author  : yintian
@Desc    : 线程安全的缓存管理器
"""
import threading
import time
from typing import Any

from ytools.utils.cache_utils import CacheItem


class CacheManager(dict):
    def __init__(
            self,
            *args,
            **kwargs
    ):
        self.default_expire_time = kwargs.pop('expire_time', None)
        self.default_max_count = kwargs.pop('max_count', None)
        super().__init__(*args, **kwargs)
        self._lock = threading.Lock()

    def __setitem__(self, key: str, value: Any) -> None:
        """重写字典的设置方法，设置默认过期时间和使用次数限制"""
        key = str(key)
        with self._lock:
            if isinstance(value, CacheItem):
                super().__setitem__(key, value)
            else:
                super().__setitem__(key, CacheItem(key, value, expire_time=self.default_expire_time,
                                                   max_count=self.default_max_count))

    def __getitem__(self, key: str) -> CacheItem:
        """重写字典的获取方法，增加过期和使用次数检查"""
        with self._lock:
            key = str(key)
            if key not in self:
                return CacheItem(None, None, is_empty=True)

            cache_item: CacheItem = super().__getitem__(key)
            if not cache_item.can_use():
                del self[key]
                return CacheItem(None, None, is_empty=True)

            cache_item.use()
            return cache_item

    def clean(self) -> None:
        """清理所有过期的缓存项"""
        with self._lock:
            expired_keys = [
                key for key, item in self.items()
                if not item.can_use()
            ]
            for key in expired_keys:
                del self[key]

    def set_expire(self, cache_id, expire_time=None, max_count=None):
        if cache_id not in self:
            return
        expire_time is not None and self.set_expire_time(cache_id, expire_time)
        max_count is not None and self.set_max_count(cache_id, max_count)

    def set_max_count(self, cache_id, max_count):
        if cache_id not in self:
            return
        cache_item: CacheItem = super().__getitem__(cache_id)
        cache_item.set_max_count(max_count)

    def set_expire_time(self, cache_id, expire_time):
        if cache_id not in self:
            return
        cache_item: CacheItem = super().__getitem__(cache_id)
        cache_item.set_expire_time(expire_time)


if __name__ == '__main__':
    cm = CacheManager()
    cm['1'] = 3
    cm.set_expire('1', 6, 10)
    cm.pop('1', None)
    for i in range(10):
        print(cm['1'].value)
        time.sleep(1)
