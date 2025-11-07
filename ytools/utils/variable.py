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
            import sys
            import importlib
            import types

            # 先尝试从 builtins 获取
            try:
                type_obj = getattr(builtins, self._type_path)
                object.__setattr__(self, '_type_cache', type_obj)
                return type_obj
            except AttributeError:
                pass

            # 检查是否已经在 sys.modules 中
            if self._type_path in sys.modules:
                type_obj = sys.modules[self._type_path]
                object.__setattr__(self, '_type_cache', type_obj)
                return type_obj

            # 如果路径包含点号，分离模块和类名
            if '.' in self._type_path:
                module_path, class_name = self._type_path.rsplit('.', 1)

                # 检查模块是否已加载
                if module_path in sys.modules:
                    module = sys.modules[module_path]
                    if hasattr(module, class_name):
                        type_obj = getattr(module, class_name)
                        object.__setattr__(self, '_type_cache', type_obj)
                        return type_obj

            # 检查是否有子模块已加载（可以推断父模块/包存在）
            # 例如：如果 ytools.utils.counter 已加载，那么 ytools 和 ytools.utils 也应该可访问
            prefix = self._type_path + '.'
            for mod_name in sys.modules:
                if mod_name.startswith(prefix):
                    # 找到子模块，需要创建所有缺失的父模块
                    parts = self._type_path.split('.')
                    for i in range(len(parts)):
                        partial_path = '.'.join(parts[:i+1])
                        if partial_path not in sys.modules:
                            parent_mod = types.ModuleType(partial_path)
                            parent_mod.__package__ = partial_path if i < len(parts) - 1 else '.'.join(parts[:i])
                            sys.modules[partial_path] = parent_mod

                    # 返回请求的模块
                    type_obj = sys.modules[self._type_path]
                    object.__setattr__(self, '_type_cache', type_obj)
                    return type_obj

            # 使用 load_object 加载
            try:
                # 延迟导入以避免循环依赖
                from ytools.utils.magic import load_object
                type_obj = load_object(self._type_path, strict=True)
                object.__setattr__(self, '_type_cache', type_obj)
                return type_obj
            except (ImportError, Exception) as load_obj_error:
                # 如果 load_object 失败，尝试手动解析
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
                    # 提供更详细的错误信息
                    raise ValueError(
                        f"无法加载类型 '{self._type_path}'\n"
                        f"  - load_object 错误: {load_obj_error}\n"
                        f"  - importlib 错误: {e}\n"
                        f"提示：请确保模块已安装且所有依赖满足，或先手动导入模块"
                    )

        return self._type_cache

    def _try_load_type_path(self, path: str):
        """
        尝试加载类型路径，如果成功返回 True，否则返回 False

        使用智能检测策略：
        1. 优先检查已加载的模块
        2. 使用 find_spec 检查模块文件是否存在
        3. 如果类名首字母大写，更倾向于认为是类型路径

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

            import importlib
            import importlib.util
            import sys

            # 优先检查完整路径是否在 sys.modules 中
            if path in sys.modules:
                return True

            # 如果是带点的路径，分离模块和类名
            if '.' in path:
                module_path, class_name = path.rsplit('.', 1)

                # 检查模块是否已经加载
                if module_path in sys.modules:
                    module = sys.modules[module_path]
                    # 检查类名是否存在
                    if hasattr(module, class_name):
                        return True
                    # 如果模块已加载但没有这个属性，检查是否有子模块
                    if (path + '.') in ''.join(sys.modules.keys()):
                        # 有子模块，说明这个路径是有效的包/模块
                        return True
                    return False

                # 使用 find_spec 检查模块是否存在
                try:
                    spec = importlib.util.find_spec(module_path)
                    if spec is None:
                        return False

                    # 如果类名首字母大写，很可能是类名，尝试导入验证
                    if class_name[0].isupper():
                        try:
                            module = importlib.import_module(module_path)
                            return hasattr(module, class_name)
                        except (ImportError, ModuleNotFoundError, ValueError):
                            # 导入失败但 spec 存在且类名大写，仍认为可能是有效路径
                            return True
                    else:
                        # 类名小写，可能是子模块，尝试导入
                        try:
                            importlib.import_module(path)
                            return True
                        except (ImportError, ModuleNotFoundError, ValueError):
                            return False
                except (ImportError, ModuleNotFoundError, ValueError):
                    return False
            else:
                # 没有点号，说明是模块名
                # 使用 find_spec 检查模块是否存在
                try:
                    spec = importlib.util.find_spec(path)
                    if spec is None:
                        return False

                    # 尝试导入
                    try:
                        importlib.import_module(path)
                        return True
                    except (ImportError, ModuleNotFoundError, ValueError):
                        # 模块存在但导入失败（可能缺少依赖），仍认为是有效路径
                        return True
                except (ImportError, ModuleNotFoundError, ValueError):
                    return False
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
