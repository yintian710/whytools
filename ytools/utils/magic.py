# -*- coding: utf-8 -*-
"""
@File    : magic.py
@Date    : 2024/4/16 下午8:17
@Author  : yintian
@Desc    : 
"""
import ast
import importlib
import inspect
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import Literal, Any, List, Union, Generator, Dict, Callable
from urllib import parse

import better_exceptions
import importlib_metadata
from loguru import logger

from ytools.error import ResultError

better_exceptions.MAX_LENGTH = None
exec_formatter = better_exceptions.ExceptionFormatter(
    colored=False,
    theme=better_exceptions.THEME,
    max_length=better_exceptions.MAX_LENGTH,
    pipe_char=better_exceptions.PIPE_CHAR,
    cap_char=better_exceptions.CAP_CHAR
)

PACKAGE_REGEX = re.compile(r"([a-zA-Z0-9_\-]+)([<>=]*)(.*)")

# 一般而言, 是一个以 simple 结尾的 url
PIPY_REGEX = re.compile(r"https?://.*/simple/?$")
PYPI_MIRROR = {
    "TUNA": "https://pypi.tuna.tsinghua.edu.cn/simple",
    "USTC": "http://pypi.mirrors.ustc.edu.cn/simple/",
    "Aliyun": "http://mirrors.aliyun.com/pypi/simple/",
    "Tencent": "https://mirrors.cloud.tencent.com/pypi/simple/",
    "Huawei": "https://repo.huaweicloud.com/repository/pypi/simple/",
    "pypi": "https://pypi.org/simple/"
}


def require(
        package_spec: str,
        action: Literal["raise", "fix"] = "fix",
        mirror_sources: str = "TUNA",
        pip_kwargs: Dict[str, str] = None
) -> str:
    """
    依赖 python 包

    :param action: 依赖操作, 若为 fix 则自动下载对应包,
    :param package_spec: pymongo==4.6.0 / pymongo
    :param mirror_sources : pip 源, 内置有 "TUNA", "USTC", "Aliyun", "Tencent", "Huawei", "pypi", 可以传自己的源进来
    :param pip_kwargs: pip 的一些参数, 如 --trusted-host, 单独的参数可以使用 {"--upgrade": ""} 这种方式
    :return: 安装的包版本号
    """
    # 分离包名和版本规范
    package_spec = re.sub(r"\s+", "", package_spec)
    match = PACKAGE_REGEX.match(package_spec)
    mirror_sources = PYPI_MIRROR.get(mirror_sources, mirror_sources)
    pip_kwargs = pip_kwargs or {}

    assert match, ValueError(f"无效的包规范: {package_spec}")
    assert not mirror_sources or PIPY_REGEX.match(mirror_sources), ValueError(f"无效的镜像源: {mirror_sources}")
    mirror_sources and pip_kwargs.setdefault('-i', mirror_sources)
    package, operator, required_version = match.groups()

    try:
        # 获取已安装的包版本
        installed_version = importlib_metadata.version(package)
        # 检查是否需要安装或更新
        from ytools.utils.package import parse as version_parse  # noqa
        if required_version and not eval(
                f'version_parse({installed_version!r}) {operator} version_parse({required_version!r})'):
            raise importlib_metadata.PackageNotFoundError
        else:
            return installed_version

    except importlib_metadata.PackageNotFoundError:

        # 包没有安装或版本不符合要求
        install_command = package_spec if required_version else package
        cmd = [sys.executable, "-m", "pip", "install"]
        for k, v in pip_kwargs.items():
            k and cmd.append(k)
            v and cmd.append(v)
        cmd.append(install_command)
        if action == "raise":
            raise importlib_metadata.PackageNotFoundError(f"依赖包不符合要求, 请使用以下命令安装: {' '.join(cmd)}")
        else:
            logger.debug(f"依赖包不符合要求, 自动修正, 命令: {' '.join(cmd)}")
            subprocess.check_call(cmd)
            return importlib_metadata.version(package)


def load_object(path, reload=False, from_path=False, strict=True, __env__=None):
    """
    加载给定绝对对象路径的对象，并返回它。
    对象可以是类、函数、变量或实例的导入路径，
    如果 ``path`` 不是字符串，而是可调用对象，
    例如类或函数，则按原样返回。

    :param __env__:
    :param strict:
    :param from_path: 从绝对路径中加载
    :param reload: 是否重载模块
    :param path: 模块的路径
    :return:

    """

    __env__ = __env__ or {**globals(), **locals()}

    def _load(o):

        try:
            return eval(o, __env__)
        except:  # noqa
            try:
                _ret = importlib.import_module(o)
                reload and inspect.ismodule(_ret) and importlib.reload(_ret)
                return _ret

            except Exception as e:
                if strict:
                    raise ValueError(f"加载对象失败: {raw}")
                else:
                    return e

    if not isinstance(path, str):
        return path

    if from_path:
        base_dir = os.getcwd()
        if path.__contains__(base_dir):
            sons = path.replace(base_dir, "").split(".")[0].replace("/", ".")
        else:
            i = 0
            for i, s in enumerate(path):
                try:
                    assert base_dir[i] == s
                except AssertionError:
                    sons = path[i:].split(".")[0].replace("/", ".")
                    break
            else:
                sons = os.path.basename(path.split(".")[0])
        spec2 = importlib.util.spec_from_file_location(sons, path)  # noqa
        odm = importlib.util.module_from_spec(spec2)  # noqa
        spec2.loader.exec_module(odm)
        return odm
    else:
        if not re.search(r'[a-zA-Z.]+', path):
            return path

        raw = path
        # 获取调用参数
        if path.__contains__('?'):
            path, para = path.split('?', 1)
            args, kwargs = [], string2argv(para)
        else:
            args, kwargs = [], {}
        if re.match(r'lambda .*?', path):
            parent, sons, attrs = path, "", ""
        else:
            # 拆分模块与方法
            if path.__contains__(":"):
                path, attrs = path.split(":")
            else:
                path, attrs = path, ""

            parent, sons = path.rsplit(".", 1) if path.__contains__(".") else (path, "")
        # 导入父级模块
        ret = _load(parent)
        if isinstance(ret, Exception):
            return raw
        # 导入子集模块
        for attr in filter(bool, [*sons.split("."), *attrs.split(".")]):
            try:
                ret = getattr(ret, attr)
            except:  # noqa
                if strict:
                    raise ValueError(f"加载对象失败: {raw}")
                else:
                    return raw
        else:
            if raw.__contains__('?') and callable(ret):
                return result(
                    func=ret,
                    args=args,
                    kwargs=kwargs,
                    strict=True
                )
            else:
                return ret


class Prepare:
    def __init__(self, func: Union[str, Callable], args=None, kwargs=None, annotations=None, namespace=None):
        if isinstance(func, str):
            func = load_object(func, strict=True)
        self.func = func
        self.args: List = list(args) if args else []
        self.kwargs: dict = kwargs or {}
        self.parameters = inspect.signature(self.func).parameters
        self.annotations = annotations or {}
        self.namespace = namespace or {}

    def set_kwargs(self, key, value, force=False):
        if not self.parameters.get(key):
            return
        if force:
            self.kwargs[key] = value
        else:
            self.namespace[key] = value

    def re_build(self, *args, **kwargs):
        kwargs['namespace'] = {**self.namespace, **kwargs.get('namespace', {})}
        kwargs['annotations'] = {**self.annotations, **kwargs.get('annotations', {})}
        pre = prepare(self.func, *self.args, *args, **kwargs)
        self.__dict__ = pre.__dict__

    def __call__(self, *args, **kwargs):
        (args or kwargs) and self.re_build(*args, **kwargs)
        return self.func(*self.args, **self.kwargs)

    def __repr__(self):
        return f"<{self.__class__.__name__} func: {self.func}>"

    def __eq__(self, other):
        return self.func == other


def prepare(
        func: Callable,
        *args,
        annotations: dict = None,
        namespace: dict = None,
        **kwargs,
) -> Prepare:
    annotations = annotations or {}
    namespace = namespace or {}
    args = list(args or [])
    kwargs = kwargs or {}
    positional_only = []
    positional_or_keyword = []
    var_positional = []
    keyword_only = {}
    var_keyword = {}
    signature = inspect.signature(func)
    sig_param = signature.parameters

    def get_positional(k, s):
        if args:
            v = args.pop(0)
        elif k in kwargs:
            v = kwargs.pop(k)
        else:
            v = namespace.get(k, annotations.get(k, s.default))
        return v

    def get_keyword(k, s):
        v = kwargs.pop(k, namespace.get(k, annotations.get(k, s.default)))
        return v

    for key, sig in sig_param.items():
        value = sig.empty
        match sig.kind.name:
            case 'POSITIONAL_ONLY':
                value = get_positional(key, sig)
                positional_only.append(value)
            case 'POSITIONAL_OR_KEYWORD':
                value = get_positional(key, sig)
                positional_or_keyword.append(value)
            case 'VAR_POSITIONAL':
                value = args
                var_positional = value
            case 'KEYWORD_ONLY':
                value = get_keyword(key, sig)
                keyword_only[key] = value
            case 'VAR_KEYWORD':
                value = kwargs
                var_keyword = value
        if value == sig.empty:
            raise TypeError(f"缺少参数: {key}, 参数列表: {dict(sig_param)}")
    return Prepare(
        func=func,
        args=(*positional_only, *positional_or_keyword, *var_positional),
        kwargs={**keyword_only, **var_keyword}
    )


def result(
        func,
        args: Union[list, tuple] = None,
        kwargs: dict = None,
        strict: bool = True,
        debug: bool = True,
        annotations: dict = None,
        namespace: dict = None,
        to_generator: bool = False,
        to_gen_kwargs: dict = None
):
    """
    运行一个函数并获取结果, 可以自动修复参数错误, 移除无效参数; 补充缺失参数

    :param annotations:
    :param namespace:
    :param to_gen_kwargs:
    :param to_generator:
    :param debug:
    :param strict:
    :param func: 需要调用的函数引用或相对位置
    :param args: 函数的位置参数
    :param kwargs: 函数的关键字参数
                   - _fix_return: 是否自动修正返回值
                   - _strict: 是否抛出异常
    :return:
    """
    func = load_object(func)
    args = args or tuple()
    kwargs = kwargs or {}
    assert callable(func), ValueError(f'func 必须是可执行的方法, func: {func}')
    try:
        pre = prepare(func, *args, **kwargs, namespace=namespace, annotations=annotations)
        _result = pre()
    except Exception as e:
        if not strict:
            debug and logger.exception(e)
            _result = ResultError(
                error=e,
                stack=fmt_stack(e),
                f=func,
                a=args,
                k=kwargs
            )
        else:
            raise
    return _result if to_generator is False else generator(_result, **(to_gen_kwargs or {}))


def iterable(_object: Any, enforce=(dict, str, bytes), exclude=(), convert_null=True) -> List[Any]:
    """
    用列表将 `_exclude` 类型中的其他类型包装起来

    :rtype: object
    :param convert_null: 单个 None 的时候是否给出空列表
    :param exclude: 属于此类型,便不转换
    :param enforce: 属于这里的类型, 便强制转换, 不检查 iter, 优先级第一
    :param _object:
    :return:
    """
    if _object is None and convert_null:
        return []
    if isinstance(_object, enforce) and not isinstance(_object, exclude):
        return [_object]
    elif isinstance(_object, exclude) or hasattr(_object, "__iter__"):
        return _object
    else:
        return [_object]


def generator(_object: Any, **kwargs) -> Generator:
    if inspect.isgenerator(_object):
        return _object
    elif inspect.isasyncgen(_object):
        return _object  # noqa
    else:
        kwargs.setdefault("enforce", object)
        return (i for i in iterable(_object, **kwargs))


def single(_object, default=None):
    """
    将元素变为可迭代对象后, 获取其第一个元素

    :param _object:
    :param default:
    :return:
    """
    return next((i for i in iterable(_object)), default)


def first(_object, default=None):
    """
    将元素变为可迭代对象后, 获取其第一个元素

    :param _object:
    :param default:
    :return:
    """
    return next((i for i in iterable(_object)), default)


def guess(_object: Any) -> Any:
    """
    智能的转换类型

    :param _object:
    :return:
    """
    if isinstance(_object, dict):
        return {k: guess(v) for k, v in _object.items()}
    elif isinstance(_object, (list, tuple, set)):
        return _object.__class__([guess(i) for i in _object])
    elif isinstance(_object, str):
        try:
            return ast.literal_eval(_object)
        except:  # noqa
            return _object
    else:
        return _object


def json_or_eval(text, jsonp=False, errors="strict", _step=0, **kwargs) -> Union[dict, list, str]:
    """
    通过字符串获取 python 对象，支持json类字符串和jsonp字符串

    :param _step:
    :param jsonp: 是否为 jsonp
    :param errors: 错误处理方法
    :param text: 需要解序列化的文本
    :return:

    """

    def literal_eval():
        return ast.literal_eval(text)

    def json_decode():
        return json.loads(text)

    def use_jsonp():
        real_text = re.search('\S+?\((?P<obj>[\s\S]*)\)', text).group('obj')
        return json_or_eval(real_text, jsonp=True, _step=_step + 1, **kwargs)

    if not isinstance(text, str):
        return text

    funcs = [json_decode, literal_eval]
    jsonp and _step == 0 and funcs.append(use_jsonp)
    for func in funcs:
        try:
            return func()
        except:  # noqa
            pass
    else:
        if errors != 'ignore':
            raise ValueError(f'illegal json string: `{text}`')
        else:
            return text


def string2argv(_string: str):
    if not isinstance(_string, str):
        return _string

    options = {}
    if not _string:
        return options

    try:
        options = json_or_eval(_string)
        assert isinstance(options, dict)
        return options
    except:  # noqa
        _string = parse.unquote(_string)
        return {
            j[0].strip(): guess(j[1].strip()) for i in _string.strip().split("&") if i for j in [i.split("=", 1)] if
            "=" in i
        }


def fmt_stack(e: Exception):
    """
    获取 stack 信息

    """
    return "".join(list(exec_formatter.format_exception(e.__class__, e, sys.exc_info()[2])))


def make_origin(*obj: Any):
    from time import time
    from random import random
    from hashlib import md5
    id_str = '-'.join([str(id(_)) for _ in obj])
    return md5(f'{id_str}-{time()}-{random()}'.encode()).hexdigest()


if __name__ == '__main__':
    require('curl-cffi>=0.5.10', action='raise')
