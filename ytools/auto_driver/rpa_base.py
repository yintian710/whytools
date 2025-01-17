# -*- coding: utf-8 -*-
"""
@File    : rpa_base.py
@Date    : 2025/1/17 14:40
@Author  : yintian
@Desc    : 
"""
import re
import threading
import time
from random import uniform

from ytools import logger
from ytools.utils.magic import result


class RPAControl:
    _call_end = []
    _call_kwargs = []
    node = []

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    @staticmethod
    def start_thread(target, t_args=None, t_kwargs=None, **kwargs):
        t = threading.Thread(
            target=target,
            args=t_args or (),
            kwargs=t_kwargs or {},
            **kwargs
        )
        t.start()
        return t

    def where(self) -> str:
        pass

    def to(self, tow: str, where='', default=None, force=False, call_args=None, call_kwargs=None):
        if not where:
            where = self.where()
        if not default:
            de = self.get_func(f'^to_{tow}$')
            if de:
                default = de[0]['func']
            else:
                default = lambda: logger.debug(f'当前处于 {where}, 想要去 {tow}')
        if not force and self.check_node(where, tow):
            logger.debug(f'当前为非强制前往 {tow}, 但是已经处于 {where}, 所以放弃行为')
            return
        func = default
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if callable(attr) and attr_name == f'{where}_to_{tow}':
                func = getattr(self, attr_name)
                if callable(func):
                    break
        return result(
            func=func,
            args=[
                *(call_args or [])
            ],
            kwargs={
                'where': where,
                'tow': tow,
                **(call_kwargs or {}),
                **locals()
            }
        )

    def call(self, where: str = '', default=None, suffix="", call_args=None, call_kwargs=None, try_count=3, end="", force=True):
        if end:
            if not self._call_end or (self._call_end[-1] != end):
                self._call_end.append(end)
        self._call_kwargs = {
            'where': where, 'default': default, 'suffix': suffix, 'call_args': call_args, 'call_kwargs': call_kwargs,
            'try_count': try_count, 'end': end, 'force': force,
        }
        if not default:
            default = lambda: logger.debug(
                f'当前处于 {where}' if not suffix else f'当前处于 {where}, 寻找 {suffix} 失败'
            )
        for i in range(try_count):
            if where:
                break
            where = self.where()
        if not where:
            if force:
                self.where_in_none(
                    **self._call_kwargs
                )
            else:
                logger.debug(f'当前处于深空')
            return
        if check_node := self.check_node(where):
            logger.debug(f'当前-{where} 达到或超过任务终点-{check_node}, 结束任务')
            return
        func = default
        if suffix:
            patten = f'where_in_(.*?)_for_{suffix}$'
        else:
            patten = 'where_in_(.*)$'
        for func_dict in self.get_func(patten):
            su = func_dict['su']
            su_options = su.split('_or_')
            if where in su_options:
                func = func_dict['func']
                break
        logger.debug(f'当前处于 {where}, 执行 - {func.__name__}')
        return result(
            func=func,
            args=[
                *(call_args or [])
            ],
            kwargs={
                'where': where,
                **(call_kwargs or {}),
                **locals()
            }
        )

    def check(self, *args, **kwargs):
        funcs = self.get_func('^check_for')
        log_flag = kwargs.get('log_flag', False)
        for func in funcs:
            func_name = func['func_name']
            func = func['func']
            result(
                func=func,
                args=args,
                kwargs=kwargs
            )
            log_flag and logger.debug(f'执行 {func_name}')

    def clear_call(self):
        self._call_end = []
        self._call_kwargs = {}

    def confused(self, where='', confused_pre='', force=False, *args, **kwargs):
        confused_type = '_'.join(filter(bool, [confused_pre, 'confused'], ))
        self.call(where=where, suffix=confused_type, call_args=args, call_kwargs=kwargs, force=force)

    def get_func(self, name_patten):
        res = []
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if not callable(attr):
                continue
            su = re.findall(name_patten, attr_name)
            if not su:
                continue
            res.append({"func_name": attr_name, "func": attr, "su": su[0]})
        return res

    def check_node(self, now_node, _check_node=None):
        if now_node not in self.node:
            return False
        if not _check_node and not self._call_end:
            return False
        check_node = _check_node or self._call_end[-1]
        for node in self.node:
            if check_node == node:
                not _check_node and self._call_end.pop(-1)
                return check_node
            if now_node == node:
                break
        return False

    def run(self):
        self.call()

    @staticmethod
    def deal_error(error, error_cls=Exception, error_type='ignore'):
        if error_type == 'ignore':
            logger.error(error)
        else:
            if isinstance(error, Exception):
                raise error
            raise error_cls(error)

    @staticmethod
    def sleep(t1=1.0, t2=1.0):
        time.sleep(t1 + uniform(0, t2))

    def where_in_none(self, *args, **kwargs):
        logger.debug(f'当前位置无法识别')
        time.sleep(30)
        kwargs['end'] = ''
        self.call(*args, **kwargs)


if __name__ == '__main__':
    pass
