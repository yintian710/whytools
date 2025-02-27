# -*- coding: utf-8 -*-
"""
@File    : dp_route_test.py
@Date    : 2025/2/27 16:02
@Author  : yintian
@Desc    : 
"""
import random
import time

from DrissionPage._pages.chromium_page import ChromiumPage
from loguru import logger

from ytools.auto_driver.dp.route import Route, RouteRequest, RouteResponse


def mock_raw(request: RouteRequest):
    request.url = 'http://localhost:5522/utils/raw?a=0&b=0'
    request.response = 'mock success'
    # print(kwargs)
    request.fail_request('')


def mock_res(**kwargs):
    request: RouteRequest = kwargs['request']
    response: RouteResponse = kwargs['response']
    logger.info(request.extra.resource_type)
    logger.info(response.text)
    response.text = '123'
    # print(kwargs)


browser = ChromiumPage()
Route.start_by_driver(driver=browser.driver)
Route.on('request', 'utils', mock_raw)
Route.on('response', 'utils', mock_res)
# browser.get('http://www.baidu.com')
b = random.randint(0, 10000)
browser.get(f'http://localhost:5522/utils/raw?a=1&b={b}')
while True:
    time.sleep(1)

if __name__ == '__main__':
    pass
