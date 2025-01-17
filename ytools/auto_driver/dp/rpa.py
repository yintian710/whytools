# -*- coding: utf-8 -*-
"""
@File    : rpa.py
@Date    : 2025/1/17 15:02
@Author  : yintian
@Desc    : 
"""
import shutil
import time
import typing
from random import randint

from DrissionPage._configs.chromium_options import ChromiumOptions  # noqa
from DrissionPage._elements.chromium_element import ChromiumElement  # noqa
from DrissionPage._pages.chromium_page import ChromiumPage  # noqa
from DrissionPage._pages.chromium_tab import ChromiumTab  # noqa

from ytools import logger
from ytools.auto_driver.dp.route import Route
from ytools.auto_driver.rpa_base import RPAControl
from ytools.auto_driver.track import get_track
from ytools.utils.magic import single, iterable


class DpRpaBase(RPAControl):
    _page: ChromiumPage = None
    _tab: ChromiumTab = None
    options: ChromiumOptions = None
    route = Route
    _local_path: str = None
    listen_at = None

    def __init__(self, **kwargs):
        self.set_options(kwargs.get('options_kwargs', {}), **kwargs.get('options_others', {}))
        super().__init__(**kwargs)

    def goto(self, url, page=None, **kwargs):
        kwargs.setdefault('show_errmsg', False)
        kwargs.setdefault('retry', 0)
        kwargs.setdefault('interval', None)
        kwargs.setdefault('timeout', 30)

        page = page or self.page
        page.get(url, **kwargs)

    def set_options(self, options: dict = None, **kwargs):
        options = options or {}
        op = ChromiumOptions()
        for k, v in options.items():
            op.set_argument(k, v if v else None)
        if server := kwargs.get('server'):
            if isinstance(server, int):
                op.set_local_port(server)
            elif isinstance(server, str):
                if server.isdigit():
                    op.set_local_port(server)
                else:
                    op.set_address(server)
            else:
                raise ValueError
        if local_path := kwargs.get('user_data_path', self._local_path):
            op.set_user_data_path(local_path)
            self._local_path = local_path
        self.options = op
        if self._page:
            del self._page

    @property
    def page(self):
        if not self._page and not self._tab:
            self._page = ChromiumPage(self.options)
        if self.listen_at and not self._page.listen.listening:
            self._page.listen.start(self.listen_at)
        return self._tab or self._page

    def set_page(self, page: typing.Optional[ChromiumPage]):
        if not page:
            self.set_tab(None)
        self._page = page

    def set_tab(self, tab: typing.Optional[ChromiumTab]):
        self._tab = tab

    def re_tab(self):
        try:
            logger.debug(f'关闭当前标签, 启动新标签')
            self.close_other_tab()
            self.goto('about:blank')
        except Exception as e:
            logger.error(f're_tab-{e}')

    def close_other_tab(self):
        self.page.close_tabs([_ for _ in self.page.tab_ids if _ != self.page.tab_id])

    def close(self, rm=True):
        try:
            if self._tab:
                self._tab.close()
            if self._page:
                self._page.browser.quit(force=True)
            self.set_page(None)
            time.sleep(5)
        except Exception as e:
            logger.error(f'关闭浏览器失败, {e}', )
        try:
            rm and shutil.rmtree(self._local_path)
        except Exception as e:
            logger.error(f'删除浏览器本期文件失败, {e}')

    def find(self, eles: typing.Union[typing.List[typing.Union[str, dict]], str, dict], index=0, page: ChromiumPage = None, one=True, error_type='ignore', try_count=3) \
            -> typing.Union[typing.List[ChromiumElement], ChromiumElement]:
        def find_one(_ele, _index, parent=None):
            try:
                parent = parent or page
                r = parent.eles(_ele, timeout=1)
                if len(r) < _index:
                    self.deal_error(f'匹配到对应元素: {_ele},但 index-{index} 超标, 匹配长度为 {len(r)}',
                                    error_type=error_type)
                    return None
                r = r[_index] if one and r and _index >= 0 else r
                return r if not one else single(r)
            except Exception as e:
                self.deal_error(e, error_type=error_type)
            return None

        def find_dict(_ele: dict):
            try:
                if shadow_root := _ele.get('shadow_root'):
                    parent = page.ele(shadow_root).shadow_root
                else:
                    parent = page
                r = find_one(_ele.get('ele'), _ele.get('index', 0), parent=parent)
                r = r[index] if r and index > 0 else r
                return one and r
            except Exception as e:
                self.deal_error(e, error_type=error_type)
            return None

        res = []
        page = page or self.page
        for ele in iterable(eles):
            for _ in range(try_count):
                if isinstance(ele, str):
                    _r = find_one(ele, index)
                elif isinstance(ele, list) and len(ele) > 1:
                    _r = find_one(ele[0], ele[1])
                elif isinstance(ele, dict):
                    _r = find_dict(ele)
                else:
                    _r = ele
                if _r and one:
                    return single(_r)
                elif _r:
                    res.extend(list(iterable(_r)))
                    break
        return res  # noqa

    def run_slider(self, distance: int, slider_ele='#sliderContainer'):
        slider = single(self.find(slider_ele))
        track = self.get_track_list(
            distance=distance
        )
        self.page.actions.hold(slider)
        now = slider.rect.midpoint
        for t in track:
            self.page.actions.move_to(now, t[0], t[1], duration=0.006)
        self.sleep(0.1, 0.2)
        self.page.actions.release()

    @staticmethod
    def get_track_list(distance):
        def get_one_track(dis, file_name=""):
            while True:
                track = get_track(distance=dis, file_name=file_name)
                if len(track) > 2:
                    break
            return track

        while True:
            fast_dis = randint(distance // 2, distance * 2 // 3)
            low_dis = randint(12, 20)
            middle_dis = distance - fast_dis - low_dis
            if middle_dis > 0:
                break
        fast_track = get_one_track(fast_dis, 'fast.json')
        middle_track = get_one_track(middle_dis, 'middle.json')
        low_track = get_one_track(low_dis, 'low.json')
        _res = fast_track
        last_node = _res[-1]
        for _ in middle_track[1:]:
            _res.append([_[0] + last_node[0], _[1] + last_node[1]], )
        last_node = _res[-1]
        for _ in low_track[1:]:
            _res.append([_[0] + last_node[0], _[1] + last_node[1]])
        _res.append([distance, _res[-1][1]])
        return _res

    def click(self, eles: typing.Union[typing.List[typing.Union[str, dict]], str, dict], index=0, page: ChromiumPage = None, one=True, error_type='ignore', try_count=3, sleep=3):
        def click_one(_ele):
            try:
                if r := self.find(_ele, index=index, page=page, one=True, error_type=error_type, try_count=1):
                    return any([button.click() for button in iterable(r)])
                self.sleep()
            except Exception as e:
                self.deal_error(e, error_type=error_type)
            finally:
                self.sleep(sleep)

        page = page or self.page
        for ele in iterable(eles):
            flag = False
            for _ in range(try_count):
                flag = click_one(ele)
                if flag:
                    break
            if flag and one:
                break

    def input(self, eles: typing.Union[typing.List[typing.Union[str, dict]], str, dict], text: str, index=0, page: ChromiumPage = None, one=True, error_type='ignore', try_count=3):

        def input_one(_ele, _text, _index=0):
            try:
                if r := self.find(_ele, index=index, page=page, one=True, error_type=error_type, try_count=1):
                    if isinstance(_ele, list) and len(_ele) > 2:
                        clear = bool(_ele[2])
                    elif isinstance(_ele, dict):
                        clear = bool(_ele.get('clear'))
                    else:
                        clear = True
                    if isinstance(_ele, list) and len(_ele) > 3:
                        by_js = bool(_ele[3])
                    elif isinstance(_ele, dict):
                        by_js = bool(_ele.get('by_js'))
                    else:
                        by_js = False
                    [button.input(_text, clear=clear, by_js=by_js) for button in iterable(r)]
                    return True
                self.sleep()
            except Exception as e:
                self.deal_error(e, error_type=error_type)

        page = page or self.page
        for ele in iterable(eles):
            flag = False
            for _ in range(try_count):
                flag = input_one(ele, text, index)
                if flag:
                    break
            if flag and one:
                break

    def quit(self):
        if self._page:
            self._page.close()
        self._page = None  # noqa
        self._tab = None  # noqa

    def where_in_none(self, *args, **kwargs):
        logger.debug(f'当前位置无法识别')
        logger.debug(f'当前 url: {self.page.url}')
        time.sleep(30)
        kwargs['end'] = ''
        self.call(*args, **kwargs)

    def __del__(self):
        self.close()


if __name__ == '__main__':
    pass
