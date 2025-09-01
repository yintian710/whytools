# -*- coding: utf-8 -*-
"""
@File    : route_test.py
@Date    : 2025/3/11 23:30
@Author  : yintian
@Desc    : 
"""
from DrissionPage._configs.chromium_options import ChromiumOptions
from objprint import op

from ytools.auto_driver.dp.route_by_fetch import *


def a(**kwargs):
    op(kwargs["request"])

def b(**kwargs):
    op(kwargs["headers"])


def test():
    opt = ChromiumOptions()
    opt.set_argument(' --disable-web-security', "")
    opt.set_browser_path("a")
    browser = ChromiumPage(opt)
    driver = browser.driver
    driver.run("Network.enable")
    driver.set_callback("Network.requestWillBeSent", a)
    driver.set_callback("Network.requestWillBeSentExtraInfo ", b)
    while True:
        time.sleep(1)


if __name__ == '__main__':
    test()
