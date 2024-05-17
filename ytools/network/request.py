# -*- coding: utf-8 -*-
"""
@File    : request.py
@Date    : 2024-04-17 13:14
@Author  : yintian
@Desc    : 
"""

import argparse
import inspect
import itertools
import re
import shlex
import threading
from collections import OrderedDict
from typing import Optional, Mapping, Any, Union, Callable, Dict
from urllib import parse

import requests
import ujson
from six.moves import http_cookies as _cookie  # noqa

from lego.libs import empty
from lego.libs.models.queues import Item
from lego.utils import universal


class Header(dict):

    def __init__(self, data=None, _dtype: Callable = None, _ktype: Callable = None, **kwargs):
        self.dtype = _dtype or (lambda x: x)
        self.ktype = _ktype or str
        self.comps = [
            lambda x: str(x).lower(),
            lambda x: str(x).upper(),
            lambda x: str(x).title(),
        ]
        if data is None:
            data = {}
        super().__init__({**data, **kwargs})

    def __setitem__(self, key, value):
        key: str = self.ktype(key)
        keys = self.keys()

        for comp in self.comps:
            nkey = comp(key)
            if nkey in keys:
                return super().__setitem__(nkey, self.dtype(value))

        else:
            return super().__setitem__(key, self.dtype(value))

    def __getitem__(self, key):

        key: str = self.ktype(key)
        keys = self.keys()

        for comp in self.comps:
            nkey = comp(key)
            if nkey in keys:
                return super().__getitem__(nkey)
        else:
            return super().__getitem__(key)

    def __delitem__(self, key):
        key: str = self.ktype(key)
        keys = self.keys()

        for comp in self.comps:
            nkey = comp(key)
            if nkey in keys:
                return super().__delitem__(nkey)
        else:
            return super().__delitem__(key)

    def __eq__(self, other):
        if isinstance(other, (Mapping, dict)):
            other = self.__class__(other, dtype=self.dtype, ktype=self.ktype)
        else:
            return NotImplemented
        # Compare insensitively
        return self.items() == other.items()

    def __contains__(self, __o: object) -> bool:
        key: str = self.ktype(__o)
        keys = self.keys()

        for comp in self.comps:
            nkey = comp(key)
            if nkey in keys:
                return True
        else:
            return False

    def setdefault(self, __key, __default):  # noqa
        key: str = self.ktype(__key)
        keys = self.keys()

        for comp in self.comps:
            nkey = comp(key)
            if nkey in keys:
                return super().setdefault(nkey, self.dtype(__default))
        else:
            return super().setdefault(key, self.dtype(__default))


class Request:

    def __init__(
            self,
            url: str = None,
            method: str = "get",
            params: Optional[Mapping[str, str]] = None,
            data: Any = None,
            json: Any = None,  # noqa
            headers: Union[Mapping[str, str]] = None,
            cookies: Union[Mapping[str, str]] = None,
            timeout: int = ...,
            allow_redirects: bool = True,
            proxies: Optional[Dict[str, str]] = None,
            verify: Union[bool] = False,
            cert=None,
            callback: Callable = empty,
            spider=empty,
            httpversion=None,
            sslversion=None,
            extra: dict = None,
            **kwargs
    ):
        """
        构造一个 Request

        :param url: 请求相关 URL
        :param method: 请求方法
        :param params: 请求参数
        :param data: 请求 body
        :param json: 请求 json body
        :param headers: 请求头
        :param cookies: 请求 cookies
        :param files: 请求文件
        :param auth: 验证
        :param timeout: 超时
        :param allow_redirects: 是否允许重定向
        :param proxies: 请求的代理
        :param hooks: 请求钩子
        :param stream: 流
        :param verify: verify ssl
        :param cert: 证书
        :param callback: 回调
        :param kwargs:
        """

        self.url = url
        self.method = method.upper()
        self.params = params or {}
        self.data = data
        self.json = json
        self._headers = Header(headers, _dtype=str)
        self.cookies = cookies
        self.timeout = timeout
        self.allow_redirects = allow_redirects
        self.proxies: Dict[str, str] = proxies
        self.verify = verify
        self.cert = cert
        self.retry = 0
        self.httpversion = httpversion
        self.sslversion = sslversion
        self.max_retry = 5
        self.res_min_size = None
        self.pass_code = kwargs.pop("pass_code", ...)
        self.spider = spider
        self.callback: Callable = callback
        self._seeds = Item()
        self.storage = True
        self.extra: dict = extra or {}

        for k, v in kwargs.items():
            setattr(self, k, v)

    headers: Header = property(
        fget=lambda self: self._headers,
        fset=lambda self, v: setattr(self, "_headers", Header(v, _dtype=str)),
        fdel=lambda self: setattr(self, "_headers", Header({}, _dtype=str)),
        doc="请求头"
    )

    @property
    def seeds(self) -> Item:
        return self._seeds

    @seeds.setter
    def seeds(self, v):
        self._seeds = Item(v)

    @seeds.deleter
    def seeds(self):
        self._seeds = Item()

    @property
    def request(self):
        """
        获取 PreparedRequest 对象

        :return:
        """
        p = requests.PreparedRequest()
        p.prepare(
            method=self.method.upper(),
            url=self.url,
            headers=self.headers,
            files=self.files,
            data=self.data or {},
            json=self.json,
            params=self.params or {},
            auth=self.auth,
            cookies=self.cookies,
        )
        return p

    @property
    def curl(self):
        """
        request object to curl cmd

        :return:
        """

        req = self.request
        args = [
            'curl',
            '-X %s' % req.method
        ]

        for k, v in sorted(req.headers.items()):
            args.append('-H ' + ujson.dumps('{}: {}'.format(k, v), escape_forward_slashes=False))

        if req.body:
            body = req.body.decode() if isinstance(req.body, bytes) else req.body
            args.append('-d ' + ujson.dumps(body, escape_forward_slashes=False))

        args.append(ujson.dumps(req.url, escape_forward_slashes=False))

        return ' '.join(args)

    @classmethod
    def from_curl(cls, curl_command, **kwargs):
        """
        从 curl 中导入

        :param curl_command:
        :param kwargs:
        :return:
        """

        _parser = argparse.ArgumentParser()
        _parser.add_argument('command')
        _parser.add_argument('url')
        _parser.add_argument('-d', '--data')
        _parser.add_argument('-c', '--cookie', default=None)
        _parser.add_argument('-r', '--request', default=None)
        _parser.add_argument('-p', '--proxy', default=None)
        _parser.add_argument('-b', '--data-binary', '--data-raw', default=None)
        _parser.add_argument('-X', default='')
        _parser.add_argument('-H', '--header', action='append', default=[])
        _parser.add_argument('-du', '--data-urlencode', action='append', default=[], type=lambda x: x.split("="))
        _parser.add_argument('--compressed', action='store_true')
        _parser.add_argument('--location', action='store_true')
        _parser.add_argument('-k', '--insecure', action='store_true')
        _parser.add_argument('--user', '-u', default=())
        _parser.add_argument('-i', '--include', action='store_true')
        _parser.add_argument('-s', '--silent', action='store_true')

        if isinstance(curl_command, str):
            curl_command = curl_command.replace('curl --location', 'curl')
            tokens = shlex.split(curl_command.replace(" \\\n", " "))
        else:
            tokens = curl_command

        parsed_args = _parser.parse_args(tokens)

        if parsed_args.data_urlencode:
            post_data = {i[0]: i[1] for i in parsed_args.data_urlencode}
        else:
            post_data = parsed_args.data or parsed_args.data_binary

        method = parsed_args.request.lower() if parsed_args.request else 'post' if post_data else "get"

        if parsed_args.X:
            method = parsed_args.X.lower()

        cookie_dict = OrderedDict()
        if parsed_args.cookie:
            cookie = _cookie.SimpleCookie(bytes(parsed_args.cookie, "ascii").decode("unicode-escape"))
            for key in cookie:
                cookie_dict[key] = cookie[key].value

        quoted_headers = OrderedDict()

        for curl_header in parsed_args.header:
            if curl_header.startswith(':'):
                occurrence = [m.start() for m in re.finditer(':', curl_header)]
                header_key, header_value = curl_header[:occurrence[1]], curl_header[occurrence[1] + 1:]
            else:
                header_key, header_value = curl_header.split(":", 1) if ':' in curl_header else (curl_header, "")

            if header_key.lower().strip("$") == 'cookie':
                cookie = _cookie.SimpleCookie(bytes(header_value, "ascii").decode("unicode-escape"))
                for key in cookie:
                    cookie_dict[key] = cookie[key].value
            else:
                quoted_headers[header_key] = header_value.strip()

        # add auth
        user = parsed_args.user
        if parsed_args.user:
            user = tuple(user.split(':'))

        return cls(
            url=parsed_args.url,
            params=kwargs,
            method=method,
            data=post_data,
            headers=quoted_headers,
            cookies=cookie_dict,
            auth=user,
            verify=parsed_args.insecure
        )

    @property
    def real_url(self):
        """
        带有参数的真实请求的 url

        :return:
        """

        if self.params:
            scheme, netloc, path, params, query, fragment = parse.urlparse(self.url)
            query = "&".join([query, parse.urlencode(self.params)]) if query else parse.urlencode(self.params)
            return parse.urlunparse([scheme, netloc, path, params, query, fragment])

        else:
            return self.url

    @property
    def proxies_or_thread(self):
        """
        返回代理或者线程信息

        :return: the name of the agent or thread being used
        """
        proxies = self.proxies or {}
        keys = ['http', 'https', 'sock5']

        for key in keys:
            _ret = proxies.get(key)
            if _ret: return _ret
        else:
            return threading.current_thread().name

    def clear_proxies(self):
        from lego.utils.proxies import proxy_manager
        self.proxies = None
        proxy_manager.clear_proxies(self.proxies_key)

    def success(self):
        """
        将请求标记为成功状态，删除备份临时种子等信息

        :return:
        """
        return self.spider.remove_seeds(self.seeds)

    def submit(self, limit=False):
        """
        将请求提交到待处理队列

        :return:
        """
        self.spider.submit(self, limit=limit)
        return self.to_task_queue("temp")

    def to_task_queue(self, qt='current', **kwargs):
        """
        save to task queue

        :return:
        """

        if not self.seeds:
            return False
        else:
            return self.spider.put_seeds(seeds=self.seeds, maxsize=None, qtypes=qt, **kwargs)

    def to_response(self, hooks: object = "default", retry=0, downloader=None):
        """
        发送请求获取响应对象，可以执行钩子

        :param retry:
        :param hooks: hooks
        :param downloader:
        :return:
        :rtype: Response
        """
        from lego.libs.network import Response
        from lego.core.downloader import RequestsDownloader

        if hooks == 'default':
            from lego.packages.before_request import random_ua, set_proxies
            from lego.packages.after_request import show_response

            hooks = {
                "before": [random_ua, set_proxies],
                "after": [show_response]
            }

        elif hooks is True:
            hooks = {
                'before': universal.iterable(self.before_request or []),
                'after': universal.iterable(self.after_request or []),
            }

        if retry != -1:
            ditto = range(retry + 1)
        else:
            ditto = itertools.count()

        response = Response.make_response(status_code=-1)
        downloader = downloader or RequestsDownloader()
        if inspect.isclass(downloader): downloader = downloader()

        assert not inspect.iscoroutinefunction(downloader.fetch), f"该模式不支持异步下载器: {downloader}"

        for _ in ditto:

            response: Response = downloader.fetch(self, hooks=hooks)
            if not response:
                self.retry += 1
                self.clear_proxies()
            else:
                break

        return response  # type:Response

    def replace(self, **kwargs):
        """
        替换请求的某些属性后生成一个新的 Request

        :param kwargs:
        :return:
        """
        attrs = {**self.__dict__}
        attrs.update(**kwargs)
        return self.__class__(**attrs)

    def follow(self, seeds: dict, backup: list = None, shutdown=False, attrs: dict = None):
        """
        根据种子 `seeds` 重新渲染 生成新的 request
        并拷贝 当前 request 的 attrs 至 新的 request
        默认拷贝 seeds.raw, 并设置 _follow

        :param seeds: 新的种子
        :param backup: 需要备份的属性
        :param shutdown: 是否终止当前流程
        :param attrs: 需要设置的属性
        :return:
        """
        return self.spider.follow(self, seeds=seeds, backup=backup, shutdown=shutdown, attrs=attrs)

    def __getattr__(self, item):
        if item == 'callback': item = 'parse'
        return getattr(self.spider, item, empty)

    def __getitem__(self, item):
        if isinstance(item, tuple):
            item, default = item

        elif isinstance(item, list):
            return tuple([self.seeds.get(*universal.iterable(_i)) for _i in item])
        else:
            item, default = item, None

        return self.seeds.get(item, default)

    def __setitem__(self, key, value):
        self.seeds[key] = value

    def __delitem__(self, key):
        for _k in universal.iterable(key):
            self.seeds.pop(_k, None)

    def __str__(self):
        return f'<Request [{self.real_url}]>'

    def __repr__(self):
        return self.__str__()

    def __bool__(self):
        return bool(self.real_url)

    def from_cookies(self):
        cookies = self.headers.get("Cookie")
        if not cookies:
            return []
        else:
            up = parse.urlparse(self.url)
            return [
                dict(zip(
                    (
                        "name",
                        "value",
                        "domain",
                        "path",
                    ),
                    (
                        *i.split("="),
                        up.netloc,
                        "/"
                    )
                )) for i in cookies.split("; ")
            ]


if __name__ == '__main__':
    req = Request.from_curl("""

   curl -X 'GET' \
  'http://10.0.0.36:5522/clash/api/get_sub' \
  -H 'accept: application/json'
    """)

    res = req.to_response()
    print(res.text)

if __name__ == '__main__':
    pass
