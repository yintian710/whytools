# -*- coding: utf-8 -*-
"""
@File    : cache_utils.py
@Date    : 2025/10/1 15:31
@Author  : yintian
@Desc    : 
"""
import time
from functools import update_wrapper
from itertools import count
from threading import Lock
from typing import Callable, Union, Optional, Any

from ytools import logger
from ytools.utils.date import Arrow


class CacheItem:
    expire_time: Optional[float] = None
    max_count: Optional[int] = None

    def __init__(
            self,
            cache_id,
            value: Any,
            expire_time: Optional[float] = None,
            max_count: Optional[int] = None,
            is_empty=False
    ):
        self.is_empty = is_empty
        self.id = cache_id
        self.value = value
        self.set_expire_time(expire_time)
        self.set_max_count(max_count)
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
        if self.max_count is not None and self.use_count >= self.max_count:
            return False
        return True

    def can_use(self) -> bool:
        return self.check_expired() and self.check_uses()

    def set_max_count(self, uses):
        if uses is None:
            return
        if isinstance(uses, int) and uses > 0:
            self.max_count = uses
        else:
            self.max_count = None
        logger.debug(f"{self.id} 设置最大使用次数为: {self.max_count}")

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


class CacheSpace:
    class Item:
        _value: Any = None

        def __init__(self, name, space, **kwargs):
            self.name = name
            self.space = space
            for k, v in kwargs.items():
                setattr(self, k, v)

        def get(self):
            pass

        def use(self):
            pass

        def check_use(self):
            return True

    def __init__(self, **kwargs):
        self._cache = {}
        self._lock = Lock()

    def __getitem__(self, item):
        with self._lock:
            if item not in self._cache:
                self._cache[item] = self.Item(item, self)
            return self._cache[item]

    def __iter__(self):
        return self._cache.keys()

    def __delitem__(self, key):
        self._cache.pop(key, None)


class LocalCache(CacheSpace):
    class Item(CacheSpace.Item):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self._use_count = count()
            self.use_count = next(self._use_count)

        def use(self):
            self.use_count = next(self._use_count)

        def check_use(self):
            pass

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class RedisCache(CacheSpace):
    pass


class Cache:
    _mode: str = None
    _space: CacheSpace
    __space = {
        "local": LocalCache,
        "redis": RedisCache
    }

    def __init__(self, mode="local", cache_options=None):
        self.mode: str = mode
        self._space = self.__space[mode](**(cache_options or {}))

    @property
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, value):
        assert not self._mode, f"无法修改缓存模式"
        assert value in self.__space, f"模式设置错误，mode 支持以下类型：{'、'.join(self.__space.keys())}"
        self._mode = value

    def __getitem__(self, item):
        return self._space[item]

    def __iter__(self):
        return self._space.__iter__()

    def __delitem__(self, key):
        self._space.__delitem__(key)

    def make_cache(self, key, expire_time=0, expire_count=0):
        pass

    @staticmethod
    def get_key(self, keys, func, *args, **kwargs):
        return keys

    def wrapper(self, func, maxsize=128, keys="", expire_time=0, expire_count=0) -> Callable:
        def get_cache(*args, **kwargs):
            key = self.get_key(keys, func, *args, **kwargs)
            if key not in self:
                pass

        if maxsize == 0:
            def inner(*args, **kwargs):
                key = self.get_key(keys, func, *args, **kwargs)
                cache = self[key]
        pass

    def __call__(self, maxsize: Union[Callable, int, None] = 128, keys=""):
        def inner(_func):
            wrapper_ = self.wrapper(_func, maxsize, keys)
            return update_wrapper(wrapper_, _func)

        if callable(maxsize):
            func, maxsize = maxsize, 128
            decoration = inner(func)
        elif isinstance(maxsize, (int, None)):
            maxsize = max(0, maxsize)
            decoration = inner
        elif maxsize is not None:
            raise TypeError(f"")
        return decoration


if __name__ == '__main__':
    pass
