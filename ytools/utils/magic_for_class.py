# -*- coding: utf-8 -*-
"""
@File    : magic_for_class.py
@Author  : yintian
@Date    : 2025/5/26 11:03
@Software: PyCharm
@Desc    : 
"""
import functools
import inspect
import json


class CustomMeta(type):
    _instances = {}

    def __new__(mcs, name, bases, attrs, **kwargs):
        # 获取单例参数和包装前缀
        singleton = kwargs.get('singleton', False)
        wrappers = kwargs.get('wrappers', '_when_')
        fix = kwargs.get('fix', {})
        # 存储 kwargs 以便 __call__ 使用
        attrs['__cls_kwargs'] = {'singleton': singleton, 'wrappers': wrappers, 'fix': fix}
        # 不修改方法，仅创建类
        cls = super().__new__(mcs, name, bases, attrs)
        return cls

    def __call__(cls, *args, **kwargs):
        # 获取单例参数和包装前缀
        cls_kwargs = getattr(cls, '__cls_kwargs', {})
        singleton = cls_kwargs.get('singleton', False)
        wrappers = cls_kwargs.get('wrappers', '_when_')
        fix = cls_kwargs.get('fix', {})

        def when_match(ins, attr_name):
            attr_value = getattr(ins, attr_name)
            if not callable(attr_value):
                return False
            wrapper_name = f'{wrappers}{attr_name}'
            wrapper_func = getattr(ins, wrapper_name, None)
            if wrapper_func and callable(wrapper_func):
                return True
            return False

        def when_fix(ins, attr_name):
            attr_value = getattr(ins, attr_name)
            wrapper_name = f'{wrappers}{attr_name}'
            wrapper_func = getattr(ins, wrapper_name)
            setattr(ins, attr_name, wrapper_func(attr_value))

        fix['when'] = {
            "match": when_match,
            "fix": when_fix
        }

        def get_key():
            if isinstance(singleton, str):
                if singleton == 'all':
                    # 使用所有参数生成键
                    init_signature = inspect.signature(cls.__init__)
                    bound_args = init_signature.bind(None, *args, **kwargs)
                    bound_args.apply_defaults()
                    param_dict = {k: v for k, v in bound_args.arguments.items() if k != 'self'}
                    # 使用 json.dumps 序列化，sort_keys 保证顺序一致，default=str 处理不可序列化对象
                    return json.dumps({'class': cls.__name__, 'params': param_dict}, sort_keys=True, default=str)
                elif singleton.startswith('key_'):
                    key_name = singleton[4:]
                    return json.dumps(
                        {'class': cls.__name__, 'key': kwargs.get(key_name, args[0] if args else cls.__name__)},
                        sort_keys=True, default=str)
                else:
                    return singleton
            elif isinstance(singleton, (list, tuple)):
                param_dict = {k: kwargs.get(k, '') for k in singleton}
                return json.dumps({'class': cls.__name__, 'params': param_dict}, sort_keys=True, default=str)
            return cls.__name__

        def new_ins():
            ins = type.__call__(cls, *args, **kwargs)
            for attr_name in dir(ins):
                for fd in fix.values():
                    if fd['match'](ins, attr_name):
                        fd['fix'](ins, attr_name)
            return ins

        # 检查单例
        if singleton:
            key = get_key()
            if key not in cls._instances:
                instance = new_ins()
                # 动态包装方法
                cls._instances[key] = instance
            instance = cls._instances[key]
        else:
            instance = new_ins()
        return instance

