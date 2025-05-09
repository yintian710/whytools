# -*- coding: utf-8 -*-
"""
@File    : route.py
@Date    : 2024/8/12 上午9:17
@Author  : yintian
@Desc    : 
"""
from DrissionPage._configs.chromium_options import ChromiumOptions

from ytools.utils.magic import require

require('DrissionPage>=4.0.5.6')

import base64
import json
import random
import re
import time
from collections import defaultdict
from hashlib import md5

from DrissionPage._base.driver import Driver  # noqa
from DrissionPage._pages.chromium_page import ChromiumPage  # noqa

from ytools.utils.magic import result


class RouteRequestExtra:
    def __init__(self, **kwargs):
        self.resource_type = kwargs.get('resourceType')
        self.resource_error_reason = kwargs.get('responseErrorReason')
        self.response_status_code = kwargs.get('responseStatusCode')
        self.response_status_text = kwargs.get('responseStatusText')
        self.response_headers = kwargs.get('responseHeaders')
        # self.network_id = kwargs.get('networkId')
        self.redirect_url = kwargs.get('redirectUrl')
        self.is_download = kwargs.get('isDownload')
        self.is_navigation_request = kwargs.get('isNavigationRequest')
        self.auth_challenge = kwargs.get('authChallenge')
        self.is_download = kwargs.get('isDownload')
        self.is_download = kwargs.get('isDownload')
        request = kwargs.get('request')
        self.has_post_data = request.get('hasPostData')
        self.post_data_entries = request.get('postDataEntries')
        self.mixed_content_type = request.get('mixedContentType')
        self.initial_priority = request.get('initialPriority')
        self.referrer_policy = request.get('referrerPolicy')
        self.is_link_preload = request.get('isLinkPreload')
        self.trust_token_params = request.get('trustTokenParams')
        self.is_same_site = request.get('isSameSite')
        self.url_fragment = request.get('urlFragment')


class RouteRequest:
    response = None

    def __init__(self, **kwargs):
        self.error = None
        self.success = False
        request: dict = kwargs.get('request')
        self.interception_id = kwargs.get('interceptionId')
        self.driver: Driver = kwargs.get('driver')
        self.frame_id = kwargs.get('frameId')
        self.request_id = kwargs.get('requestId')
        self.url = request.get('url')
        self.method = request.get('method')
        self.headers = request.get('headers')
        self.post_data = request.get('postData')
        self.extra = RouteRequestExtra(**kwargs)
        self.options = kwargs.copy()
        self.options.pop('driver', None)
        self.raw_fingerprint = self.fingerprint
        self.response_headers = {}
        self.raw_data = self.continue_data.copy()

    @property
    def fingerprint(self):
        md = md5()
        md.update(json.dumps({
            **self.continue_data,
            "error": str(self.error),
            "success": self.success
        }).encode())
        return md.hexdigest()

    @property
    def continue_data(self):
        data = dict(
            interceptionId=self.interception_id,
            url=self.url,
            method=self.method,
            postData=self.post_data or '',
            headers=self.headers,
        )
        if self.response:
            body = ['HTTP/2.0 200 OK']
            for k, v in self.response_headers.items():
                body.append(f'{k}: {v}')
            body.append(f"Content-Length: {len(self.response)}")
            body.append('')
            body.append(self.response)
            response = '\r\n'.join(body)
            # body.append(base64.b64encode(self.response.encode()).decode())
            data['rawResponse'] = base64.b64encode(response.encode()).decode()
        if self.error:
            if self.error not in ['Failed', 'Aborted', 'TimedOut', 'AccessDenied', 'ConnectionClosed',
                                  'ConnectionReset', 'ConnectionRefused', 'ConnectionAborted', 'ConnectionFailed',
                                  'NameNotResolved', 'InternetDisconnected', 'AddressUnreachable',
                                  'BlockedByClient', 'BlockedByResponse']:
                self.error = 'Aborted'
            data['errorReason'] = self.error
        return data

    def fulfill_request(self, **kwargs):
        pass

    def continue_request(self, **kwargs):
        if self.raw_fingerprint == self.fingerprint:
            self.driver.run(
                'Network.continueInterceptedRequest',
                interceptionId=self.interception_id
            )
        else:
            continue_data = {
                **self.continue_data,
                **kwargs
            }
            self.driver.run(
                'Network.continueInterceptedRequest',
                **continue_data
            )
        self.success = True

    def fail_request(self, error):
        error = error or self.error
        if not error or error not in ['Failed', 'Aborted', 'TimedOut', 'AccessDenied', 'ConnectionClosed',
                                      'ConnectionReset', 'ConnectionRefused', 'ConnectionAborted', 'ConnectionFailed',
                                      'NameNotResolved', 'InternetDisconnected', 'AddressUnreachable',
                                      'BlockedByClient', 'BlockedByResponse']:
            error = 'Aborted'
        self.driver.run(
            'Fetch.failRequest',
            requestId=self.request_id,
            errorReason=error
        )
        self.error = error


class RouteResponse:
    content: bytes = b''
    encoding = 'utf-8'
    flag = False

    def __init__(self, **kwargs):
        self.success = False
        self.error = ''
        self.request: RouteRequest = kwargs.get('request')
        self.driver: Driver = kwargs.get('driver')
        self.url = self.request.url
        self.raw_fingerprint = self.fingerprint
        self.raw_data = self.continue_data.copy()
        self.headers = {}
        self.get_response_body()

    def get_response_body(self):
        if self.content:
            return self.content
        res = self.driver.run(
            'Network.getResponseBodyForInterception',
            interceptionId=self.request.interception_id
        )
        if body := res.get('body'):
            if res.get('base64Encoded'):
                self.content = base64.b64decode(body)
            else:
                if isinstance(body, str):
                    self.content = body.encode()
                elif isinstance(body, bytes):
                    self.content = body
                else:
                    raise ValueError(f'body 类型错误,应为 str, bytes, 获取到 {type(body)}')
        return self.content

    @property
    def text(self):
        return self.content.decode(encoding=self.encoding)

    @text.setter
    def text(self, value):
        if isinstance(value, str):
            self.content = value.encode(encoding=self.encoding)
        elif isinstance(value, bytes):
            self.content = value
        else:
            try:
                self.content = json.dumps(value).encode(encoding=self.encoding)
            except Exception as e:
                raise e
        self.flag = True

    def json(self):
        return json.loads(self.text)

    @property
    def continue_data(self):
        data = dict(
            interceptionId=self.request.interception_id,
            url=self.url,
            method=self.request.method,
            postData=self.request.post_data or '',
            headers=self.request.headers,
        )
        if self.flag and self.content:
            if self.headers:
                response_lines = ['HTTP/1.1 200 OK']
                # 添加默认头部
                if self.headers:
                    for key, value in self.headers.items():
                        response_lines.append(f"{key}: {value}")
                # 添加 Content-Length
                response_lines.append(f"Content-Length: {len(self.content)}")
                # 添加空行分隔头部和正文
                response_lines.append("")
                # 添加正文
                response_lines.append(self.content.decode())
                # 合并成完整的响应字符串
                full_response = "\r\n".join(response_lines)
                data['rawResponse'] = base64.b64encode(full_response.encode()).decode()
            else:
                data['rawResponse'] = base64.b64encode(self.content).decode()
            # if self.headers:
            #     data['headers'] = self.headers
        if self.error:
            if self.error not in ['Failed', 'Aborted', 'TimedOut', 'AccessDenied', 'ConnectionClosed',
                                  'ConnectionReset', 'ConnectionRefused', 'ConnectionAborted', 'ConnectionFailed',
                                  'NameNotResolved', 'InternetDisconnected', 'AddressUnreachable',
                                  'BlockedByClient', 'BlockedByResponse']:
                self.error = 'Aborted'
            data['errorReason'] = self.error
        return data

    @property
    def fingerprint(self):
        md = md5()
        md.update(json.dumps({
            **self.continue_data,
            "success": self.success
        }).encode())
        return md.hexdigest()

    def continue_request(self, **kwargs):
        if self.raw_fingerprint == self.fingerprint:
            self.driver.run(
                'Network.continueInterceptedRequest',
                interceptionId=self.request.interception_id
            )
        else:
            continue_data = {
                **self.continue_data,
                **kwargs
            }
            self.driver.run(
                'Network.continueInterceptedRequest',
                **continue_data
            )
        self.success = True


class Route:
    _patters = defaultdict(dict)
    _request = defaultdict(dict)

    @classmethod
    def start_by_driver(cls, driver: Driver):
        driver.run(
            'Network.setRequestInterception',
            patterns=[
                {
                    "urlPattern": "*",
                    "interceptionStage": "HeadersReceived"
                },
                {
                    "urlPattern": "*",
                    "interceptionStage": "Request"
                }
            ]
        )
        driver.set_callback(
            'Network.requestIntercepted',
            cls.mock_func(
                func=cls.request_pause,
                driver=driver
            )
            # cls.request_pause
        )

    @staticmethod
    def mock_func(func, *args, **kwargs):
        def inner(**k):
            _kwargs = kwargs.copy()
            _kwargs.update(k or {})
            return result(
                func=func,
                args=args,
                kwargs=_kwargs,
            )

        return inner

    @classmethod
    def set(cls, action, target, func):
        if action not in cls._patters[target]:
            cls._patters[target][action] = []
        cls._patters[target][action].append(func)

    @classmethod
    def get(cls, action, target):
        if action not in cls._patters[target]:
            cls._patters[target][action] = []
        return cls._patters[target][action]

    @classmethod
    def pop(cls, action, target, func):
        if action not in cls._patters[target]:
            cls._patters[target][action] = []
        cls._patters[target][action].remove(func)

    @classmethod
    def on(cls, action, target, func):
        cls.set(f'on_{action}', target, func)

    @classmethod
    def format_request(cls, **kwargs):
        driver: Driver = kwargs.get('driver')
        request = RouteRequest(**kwargs)
        cls._request[request.request_id]['request'] = request
        cls._request[request.request_id]['driver'] = driver
        return request

    @classmethod
    def format_response(cls, **kwargs):
        response = RouteResponse(**kwargs)
        cls._request[response.request.request_id]['response'] = response
        return response

    @classmethod
    def request_pause(cls, **kwargs):
        # driver: Driver = kwargs.get('driver')
        request = cls.format_request(**kwargs)
        if request.extra.response_status_code:
            kwargs['request'] = request
            response = cls.format_response(**kwargs)
            cls._on_response(request, response)
        else:
            cls._on_request(request)

    @classmethod
    def _on_request(cls, request: RouteRequest):
        for p, v in cls._patters.items():
            if re.search(p, request.url):
                for func in v.get('on_request', []):
                    cls.mock_func(
                        func=func,
                        request=request
                    )()
                    if request.success or request.error:
                        break
        else:
            request.continue_request()

    @classmethod
    def _on_response(cls, request: RouteRequest, response: RouteResponse):
        for p, v in cls._patters.items():
            if re.search(p, response.url):
                for func in v.get('on_response', []):
                    cls.mock_func(
                        func=func,
                        request=request,
                        response=response
                    )()
                    if request.success or request.error:
                        break
        else:
            response.continue_request()


def mock_raw(request: RouteRequest):
    request.url = 'http://106.55.2.140:5522/utils/raw?a=0&b=0'
    request.headers['t1'] = "asd"
    request.response_headers = {
        'Date': 'Tue, 11 Mar 2025 16:48:03 GMT',
        'Content-Type': 'text/plain; charset=utf-8',
        'X-Custom-Header': 'Test-Value111',
        'Access-Control-Allow-Origin': '*',  # 处理跨域
    }
    request.response = "123"
    # request.headers = {
    #     'Content-Type': 'text/plain; charset=utf-8'
    # }
    # print(kwargs)
    # request.fail_request('')


def mock_res(**kwargs):
    response: RouteResponse = kwargs['response']

    response.text = 'mock success'

    response.headers = {
        'Date': 'Tue, 11 Mar 2025 16:48:03 GMT',
        'Content-Type': 'text/plain; charset=utf-8',
        'X-Custom-Header': 'Test-Value111',
        'Access-Control-Allow-Origin': '*',  # 处理跨域
    }
    # print(kwargs)


def mock_baidu(request: RouteRequest):
    print(request.url)


def test():
    opt = ChromiumOptions()
    opt.set_argument(' --disable-web-security', "")
    opt.set_browser_path("a")
    browser = ChromiumPage(opt)
    Route.start_by_driver(driver=browser.driver)
    Route.on('request', 'utils', mock_raw)
    Route.on('response', 'utils', mock_res)
    # Route.on('response', 'baidu', mock_baidu)
    # browser.get('http://www.baidu.com')
    b = random.randint(0, 10000)
    browser.get(f'http://106.55.2.140:5522/utils/raw?a=1&b={b}')
    while True:
        time.sleep(1)


if __name__ == '__main__':
    test()
