# -*- coding: utf-8 -*-
"""
@File    : cache.py
@Date    : 2025/5/8 下午2:39
@Author  : yintian
@Desc    : 线程安全的缓存管理器
"""
import threading
import time
from itertools import count
from typing import Any, Optional

from ytools import logger
from ytools.utils.date import Arrow


class CacheItem:
    expire_time: Optional[float] = None
    max_uses: Optional[int] = None

    def __init__(self, cache_id, value: Any, expire_time: Optional[float] = None, max_uses: Optional[int] = None, is_empty=False):
        self.is_empty = is_empty
        self.id = cache_id
        self.value = value
        self.set_expire_time(expire_time)
        self.set_max_uses(max_uses)
        self._use_count = count()
        self.use_count = next(self._use_count)
        self.create_time = time.time()

    def __bool__(self):
        return self.is_empty is not None

    def use(self):
        self.use_count = next(self._use_count)

    def check_expired(self) -> bool:
        if self.expire_time is None:
            return True
        return time.time() < self.expire_time

    def check_uses(self):
        if self.max_uses is not None and self.use_count >= self.max_uses:
            return False
        return True

    def can_use(self) -> bool:
        return self.check_expired() and self.check_uses()

    def set_max_uses(self, uses):
        if uses is None:
            return
        if isinstance(uses, int) and uses > 0:
            self.max_uses = uses
        else:
            self.max_uses = None
        logger.debug(f"{self.id} 设置最大使用次数为: {self.max_uses}")

    def set_expire_time(self, expire_time):
        if expire_time is None:
            return
        if isinstance(expire_time, int):
            if expire_time > 10 ** 10:
                self.expire_time = Arrow.get(expire_time).ts(10)
            elif expire_time > 0:
                self.expire_time = Arrow.now().shift(seconds=expire_time).ts(10)
            else:
                self.expire_time = None
        else:
            try:
                self.expire_time = Arrow.get(expire_time).ts(10)
            except Exception as e:
                logger.error(f"{self.id} 设置过期时间 {expire_time} 失败, 错误: {e}")
                self.expire_time = None
        logger.debug(f"{self.id} 设置过期时间为: {self.expire_time}")


class CacheManager(dict):
    def __init__(self, *args, **kwargs):
        self.default_expire_time = kwargs.pop('expire_time', None)
        self.default_max_uses = kwargs.pop('max_uses', None)
        super().__init__(*args, **kwargs)
        self._lock = threading.Lock()

    def __setitem__(self, key: str, value: Any) -> None:
        """重写字典的设置方法，设置默认过期时间和使用次数限制"""
        key = str(key)
        with self._lock:
            if isinstance(value, CacheItem):
                super().__setitem__(key, value)
            else:
                super().__setitem__(key, CacheItem(key, value, expire_time=self.default_expire_time, max_uses=self.default_max_uses))

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

    def set_expire(self, cache_id, expire_time=None, max_uses=None):
        if cache_id not in self:
            return
        expire_time is not None and self.set_expire_time(cache_id, expire_time)
        max_uses is not None and self.set_max_uses(cache_id, max_uses)

    def set_max_uses(self, cache_id, max_uses):
        if cache_id not in self:
            return
        cache_item: CacheItem = super().__getitem__(cache_id)
        cache_item.set_max_uses(max_uses)

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
