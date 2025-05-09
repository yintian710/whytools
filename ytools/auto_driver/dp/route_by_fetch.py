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
import re
import time
from collections import defaultdict
from hashlib import md5

from DrissionPage._base.driver import Driver  # noqa
from DrissionPage._pages.chromium_page import ChromiumPage  # noqa

from ytools.utils.magic import result


class Full:

    def __init__(self, **kwargs):
        self.options = kwargs.copy()
        self.options.pop('driver', None)
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
        self.full_content: bytes = b''
        self.full_headers: dict = {}
        self.full_error: str = ''
        self.full_status_code: int = 0
        self.fulls = {
            # interceptResponse: bool, full request use
            # responsePhrase: str, full response use
        }
        self.raw = self.fingerprint

    @property
    def fingerprint(self):
        return md5(
            json.dumps(
                {
                    'requestId': self.request_id,
                    'url': self.url,
                    'method': self.method,
                    'headers': self.headers,
                    'post_data': self.post_data
                }
            ).encode()
        ).hexdigest()

    @property
    def flag(self):
        return any(
            [
                self.raw != self.fingerprint,
                self.full_status_code,
                self.full_content,
                self.full_headers,
                self.full_error,
                self.fulls,
            ]
        )

    @property
    def data(self):
        return {
            "requestId": self.request_id,
            **self.fulls
        }

    @property
    def continue_data(self):
        return {
            **self.data,
            "url": self.url,
            "method": self.method,
            "postData": self.post_data or '',
            "headers": [{'name': k, 'value': v} for k, v in self.headers.items()],
        }

    @property
    def full_header_list(self):
        header_list = []
        for k, v in self.full_headers.items():
            header_list.append({'name': k, 'value': v})
        return header_list

    @property
    def full_data(self):
        data = {
            **self.data,
            "responseCode": self.full_status_code or 200
        }
        if self.full_headers:
            data['responseHeaders'] = self.full_header_list
        if self.full_content:
            data['body'] = base64.b64encode(self.full_content).decode()
        return data

    @property
    def error_data(self):
        if self.full_error not in ['Failed', 'Aborted', 'TimedOut', 'AccessDenied', 'ConnectionClosed',
                                   'ConnectionReset', 'ConnectionRefused', 'ConnectionAborted', 'ConnectionFailed',
                                   'NameNotResolved', 'InternetDisconnected', 'AddressUnreachable',
                                   'BlockedByClient', 'BlockedByResponse']:
            self.full_error = 'Aborted'
        data = {
            **self.data,
            "errorReason": self.full_error,
        }
        return data

    @property
    def full_response_data(self):
        return {
            **self.data,
            'responseHeaders': self.full_header_list
        }


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


class RouteRequest(Full):
    def continue_request(self):
        _method = 'Fetch.continueRequest'
        if not self.flag:
            continue_data = self.data
        elif self.full_error:
            _method = 'Fetch.failRequest'
            continue_data = self.error_data
        elif self.full_content or self.full_headers:
            _method = 'Fetch.fulfillRequest'
            continue_data = self.full_data
        else:
            continue_data = self.continue_data
        self.driver.run(
            _method,
            **continue_data
        )


class RouteResponse(Full):
    content: bytes = b''
    encoding = 'utf-8'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.request: RouteRequest = kwargs.get('_request')
        self.headers = {_['name']: _['value'] for _ in self.extra.response_headers}
        self.get_response_body()

    @property
    def text(self):
        return self.content.decode(encoding=self.encoding) if not self.full_content else self.full_content.decode(encoding=self.encoding)

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
        self.full_content = self.content

    def json(self):
        return json.loads(self.text)

    def get_response_body(self):
        if self.content:
            return self.content
        res = self.driver.run(
            'Fetch.getResponseBody',
            requestId=self.request_id
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

    def continue_request(self, ):
        _method = 'Fetch.continueRequest'
        if not self.flag:
            continue_data = self.data
        elif self.full_error:
            _method = 'Fetch.failRequest'
            continue_data = self.error_data
        elif self.full_content:
            _method = 'Fetch.fulfillRequest'
            continue_data = self.full_data
        elif self.full_headers:
            _method = 'Fetch.continueResponse'
            continue_data = self.full_data
        else:
            continue_data = self.data
        self.driver.run(
            _method,
            **continue_data
        )


class Route:
    _patters = defaultdict(dict)
    _request = defaultdict(dict)
    _driver: list[Driver] = []

    @classmethod
    def start_by_driver(cls, driver: Driver):
        cls._driver.append(driver)
        cls.update_listen()

    @classmethod
    def update_listen(cls):
        patterns = []
        for patters, actions in cls._patters.items():
            if actions.get('on_request'):
                patterns.append({
                    "urlPattern": f"*{patters}*",
                    "requestStage": "Request"
                })
            if actions.get('on_response'):
                patterns.append({
                    "urlPattern": f"*{patters}*",
                    "requestStage": "Response"
                })
        for driver in cls._driver:
            driver.run(
                'Fetch.enable',
                patterns=patterns
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
        cls.update_listen()

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
        request = cls.format_request(**kwargs)
        if request.extra.response_status_code:
            kwargs['_request'] = request
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
                    if request.flag:
                        break
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
                    if not response.flag:
                        break
        response.continue_request()


def mock_raw(request: RouteRequest):
    request.full_content = b""


def mock_res(response: RouteResponse):
    print()
    response.text = open('2.25.1.js').read().replace('2.25.1', '2.25.47') + "\n // 2.25.1"
    response.full_headers = {
        **response.headers,
        "content-length": str(response.full_content.__len__()),
    }
    print(123)


def test():
    from DrissionPage._configs.chromium_options import ChromiumOptions  # noqa
    opt = ChromiumOptions()
    opt.set_argument(' --disable-web-security', "")
    opt.set_browser_path("a")
    browser = ChromiumPage(opt)
    Route.start_by_driver(driver=browser.driver)
    # Route.on('request', '2.25.', mock_raw)
    Route.on('response', '2.25.', mock_res)
    browser.get(f'https://shopee.co.th/buyer/login')
    while True:
        time.sleep(1)


if __name__ == '__main__':
    test()
