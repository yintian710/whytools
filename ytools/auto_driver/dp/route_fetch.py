# -*- coding: utf-8 -*-
"""
@File    : route.py
@Date    : 2024/8/12 上午9:17
@Author  : yintian
@Desc    : 
"""
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
from loguru import logger

from ytools.utils.magic import result


class RouteRequestExtra:
    def __init__(self, **kwargs):
        self.resource_type = kwargs.get('resourceType')
        self.resource_error_reason = kwargs.get('responseErrorReason')
        self.response_status_code = kwargs.get('responseStatusCode')
        self.response_status_text = kwargs.get('responseStatusText')
        self.response_headers = kwargs.get('responseHeaders')
        self.redirect_request_id = kwargs.get('redirectedRequestId')
        self.redirect_url = kwargs.get('redirectUrl')
        self.is_download = kwargs.get('isDownload')
        self.is_navigation_request = kwargs.get('isNavigationRequest')
        self.auth_challenge = kwargs.get('authChallenge')
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
        self.network_id = kwargs.get('networkId')
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
            requestId=self.request_id,
            url=self.url,
            method=self.method,
            postData=self.post_data or '',
            headers=self.headers,
        )
        if self.response:
            data['rawResponse'] = base64.b64encode(self.response.encode()).decode()
        if self.error:
            if self.error not in ['Failed', 'Aborted', 'TimedOut', 'AccessDenied', 'ConnectionClosed',
                                  'ConnectionReset', 'ConnectionRefused', 'ConnectionAborted', 'ConnectionFailed',
                                  'NameNotResolved', 'InternetDisconnected', 'AddressUnreachable',
                                  'BlockedByClient', 'BlockedByResponse']:
                self.error = 'Aborted'
            data['errorReason'] = self.error
        return data

    def continue_request(self, **kwargs):
        if self.raw_fingerprint == self.fingerprint:
            self.driver.run(
                'Fetch.continueRequest',
                interceptionId=self.network_id
            )
        else:
            continue_data = {
                **self.continue_data,
                **kwargs
            }
            if self.response:
                _method = 'Fetch.fulfillRequest'
            elif self.error:
                _method = 'Fetch.failRequest'
            else:
                _method = 'Fetch.continueRequest'
            self.driver.run(
                _method,
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

    class MyDict(dict):
        def __init__(self, parent_instance: 'RouteResponse'):
            self.ins = parent_instance
            super().__init__()

        def __setitem__(self, key, value):
            super().__setitem__(key, value)
            self.ins.flag = True

    def __init__(self, **kwargs):
        self.success = False
        self.error = ''
        self.request: RouteRequest = kwargs.get('request')
        self.driver: Driver = kwargs.get('driver')
        self.headers = self.MyDict(self)
        self.headers.update(**kwargs.get('responseHeaders'))
        self.reason = kwargs.get('responseErrorReason')
        self.status_code = kwargs.get('responseStatusCode')
        self.network_id = kwargs.get('networkId')
        self.request_id = kwargs.get('RequestId')
        self.redirect_request_id = kwargs.get('redirectedRequestId')
        self.url = self.request.url
        self.raw_fingerprint = self.fingerprint
        self.raw_data = self.continue_data.copy()
        self.get_response_body()

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
    def headers_list(self):
        header_list = []
        for k, v in self.headers:
            header_list.append({'name': k, 'value': v})
        return header_list

    def get_response_body(self):
        if self.content:
            return self.content
        res = self.driver.run(
            'Fetch.getResponseBody',
            requestId=self.request.request_id
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
    def continue_data(self):
        data = dict(
            requestId=self.request.request_id,
            headers=self.headers_list
        )
        if self.flag and self.content:
            data['rawResponse'] = base64.b64encode(self.content).decode()
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
                'Fetch.continueRequest',
                requestId=self.request.request_id
            )
        else:
            continue_data = {
                **self.continue_data,
                **kwargs
            }
            self.driver.run(
                'Fetch.continueResponse',
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


class Route:
    _patters = defaultdict(dict)
    _request = defaultdict(dict)

    @classmethod
    def start_by_driver(cls, driver: Driver):
        driver.run(
            'Fetch.enable',
            patterns=[
                {
                    "urlPattern": "*",
                    "requestStage": "Response"
                },
                {
                    "urlPattern": "*",
                    "requestStage": "Request"
                }
            ]
        )
        driver.set_callback(
            'Fetch.requestPaused',
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
        print('''111''')
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
    request.url = 'http://localhost:5522/utils/raw?a=0&b=0'
    request.response = 'mock success'
    # print(kwargs)
    # request.fail_request('')


def mock_res(**kwargs):
    request: RouteRequest = kwargs['request']
    response: RouteResponse = kwargs['response']
    logger.info(request.extra.resource_type)
    logger.info(response.text)
    response.text = '123'
    # print(kwargs)


def mock_baidu(request: RouteRequest):
    print(request.url)


def test():
    browser = ChromiumPage()
    Route.start_by_driver(driver=browser.driver)
    Route.on('request', 'utils', mock_raw)
    Route.on('response', 'utils', mock_res)
    # Route.on('response', 'baidu', mock_baidu)
    # browser.get('http://www.baidu.com')
    b = random.randint(0, 10000)
    browser.get(f'http://localhost:5522/utils/raw?a=1&b={b}')
    while True:
        time.sleep(1)


if __name__ == '__main__':
    test()
