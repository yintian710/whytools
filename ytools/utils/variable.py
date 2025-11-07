# -*- coding: utf-8 -*-
"""
@File    : variable.py
@Author  : yintian
@Date    : 2025/6/18 14:18
@Software: PyCharm
@Desc    :
"""
import builtins
import time
from threading import Lock, local
from typing import Dict, Any, Type


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


class TypedAccessor:
    """
    类型感知的属性访问器，支持 G._type.attr 语法
    """

    def __init__(self, parent: 'VariableG', type_path: str):
        """
        初始化类型访问器

        :param parent: 父级 VariableG 对象
        :param type_path: 类型路径，如 'int', 'list', 'collections.Counter' 等
        """
        object.__setattr__(self, '_parent', parent)
        object.__setattr__(self, '_type_path', type_path)
        object.__setattr__(self, '_type_cache', None)

    def _get_type(self) -> Type:
        """
        获取类型对象，优先从 builtins 获取，否则使用 load_object 加载

        :return: 类型对象
        """
        if self._type_cache is None:
            # 先尝试从 builtins 获取
            try:
                type_obj = getattr(builtins, self._type_path)
                object.__setattr__(self, '_type_cache', type_obj)
                return type_obj
            except AttributeError:
                pass

            # 使用 load_object 加载
            try:
                # 延迟导入以避免循环依赖
                from ytools.utils.magic import load_object
                type_obj = load_object(self._type_path, strict=True)
                object.__setattr__(self, '_type_cache', type_obj)
                return type_obj
            except ImportError:
                # 如果无法导入 magic，尝试手动解析
                import importlib
                try:
                    if '.' in self._type_path:
                        module_path, class_name = self._type_path.rsplit('.', 1)
                        module = importlib.import_module(module_path)
                        type_obj = getattr(module, class_name)
                    else:
                        type_obj = importlib.import_module(self._type_path)
                    object.__setattr__(self, '_type_cache', type_obj)
                    return type_obj
                except Exception as e:
                    raise ValueError(f"无法加载类型 '{self._type_path}': {e}")
            except Exception as e:
                raise ValueError(f"无法加载类型 '{self._type_path}': {e}")

        return self._type_cache

    def _try_load_type_path(self, path: str):
        """
        尝试加载类型路径，如果成功返回 True，否则返回 False

        :param path: 类型路径
        :return: 是否成功加载
        """
        try:
            # 先尝试从 builtins 获取
            try:
                getattr(builtins, path)
                return True
            except AttributeError:
                pass

            # 使用手动解析
            import importlib
            if '.' in path:
                module_path, class_name = path.rsplit('.', 1)
                module = importlib.import_module(module_path)
                getattr(module, class_name)
                return True
            else:
                importlib.import_module(path)
                return True
        except Exception:
            return False

    def __getattr__(self, name: str):
        """
        获取属性值，如果不存在则返回类型的默认值（调用类型的无参构造函数）

        如果属性可以作为类型路径的一部分，返回新的 TypedAccessor

        :param name: 属性名
        :return: 属性值或新的 TypedAccessor
        """
        if name.startswith('_'):
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

        # 先尝试构建新的类型路径并验证是否有效
        new_type_path = f"{self._type_path}.{name}"
        if self._try_load_type_path(new_type_path):
            # 如果类型路径有效，返回新的 TypedAccessor
            return TypedAccessor(self._parent, new_type_path)

        # 否则当作普通属性访问，获取类型
        type_cls = self._get_type()

        # 从父对象获取当前值（直接使用变量名作为键，实现全局类型检查）
        current = self._parent._map.get(name)

        if current is None:
            # 不存在，创建并存储类型的默认值
            try:
                default_value = type_cls()
                self._parent._map[name] = CacheItem(default_value)
                return default_value
            except Exception as e:
                raise TypeError(f"无法创建类型 '{self._type_path}' 的默认实例: {e}")
        else:
            # 已存在，检查类型
            if current.expired or current.update(use=False):
                self._parent._map.pop(name, None)
                # 已过期，创建并存储新的默认值
                try:
                    default_value = type_cls()
                    self._parent._map[name] = CacheItem(default_value)
                    return default_value
                except Exception as e:
                    raise TypeError(f"无法创建类型 '{self._type_path}' 的默认实例: {e}")

            value = current.value
            if not isinstance(value, type_cls):
                raise TypeError(
                    f"变量 '{name}' 的类型不匹配: 期望 {type_cls.__name__}, "
                    f"实际 {type(value).__name__}"
                )
            return value

    def __setattr__(self, name: str, value: Any):
        """
        设置属性值，会检查类型是否匹配

        :param name: 属性名
        :param value: 属性值
        """
        if name.startswith('_'):
            object.__setattr__(self, name, value)
            return

        # 获取类型
        type_cls = self._get_type()

        # 使用与 __getattr__ 相同的键策略（直接使用变量名）
        current = self._parent._map.get(name)

        if current is not None and not current.expired:
            # 已存在且未过期，检查类型
            if not isinstance(current.value, type_cls):
                raise TypeError(
                    f"变量 '{name}' 的类型不匹配: 期望 {type_cls.__name__}, "
                    f"实际 {type(current.value).__name__}"
                )

        # 检查新值的类型
        if not isinstance(value, type_cls):
            raise TypeError(
                f"设置的值类型不匹配: 期望 {type_cls.__name__}, "
                f"实际 {type(value).__name__}"
            )

        # 设置值
        self._parent._map[name] = CacheItem(value)

    def __repr__(self):
        return f"<TypedAccessor [type: {self._type_path}]>"


class VariableG:
    def __init__(self):
        self._map: Dict[str, CacheItem] = {}
        self._lock = Lock()
        self.__setitem__ = self.setattr

    def __getattr__(self, item):
        # 支持 _type 语法，如 G._int.a 表示类型感知访问
        if item.startswith('_') and len(item) > 1:
            # 去掉前缀 _ 作为类型路径
            type_path = item[1:]
            return TypedAccessor(self, type_path)

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
