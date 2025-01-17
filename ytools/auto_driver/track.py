# -*- coding: utf-8 -*-
"""
@File    : track.py
@Date    : 2025/1/17 15:10
@Author  : yintian
@Desc    : 
"""

# -*- coding: utf-8 -*-

# @File    : track.py
# @Date    : 2023-03-09 14:32
# @Author  : yintian
# @Desc    :

import json
import re
import subprocess
import threading
import time
from queue import Queue
from random import choice, randint

from loguru import logger

lock = threading.Lock()

track_queue = Queue()

GLOBAL_INFO = {}


def put2queue(track_list):
    track_queue.put(track_list)


def iter_queue():
    while True:
        if not track_queue.empty():
            if item := track_queue.get():
                yield [item]


def listener(
        filename=None,
        save=False,
        plat='pc',
        min_length=100,
        interval=0.001,
        **kwargs
):
    """
    录制总接口
    :param filename: 存储的文件名
    :param save: 是否存储到本地文件
    :param plat: 录制平台
    :param min_length: 最小录制长度
    :param interval: 录制间隔
    :param kwargs:
    :return:
    """
    assert bool(save) != bool(filename), 'save 和 filename 只需要一个且不能同时存在'

    def save():
        for data in iter_queue():
            save_data(
                data=data,
                filename=filename,
                min_length=min_length,
                **kwargs
            )

    threading.Thread(target=save, daemon=True).start()

    if plat == 'pc':
        listen_pc(interval)
    elif plat == 'android':
        listen_android(**kwargs)
    else:
        raise ValueError(f'Platform {plat} not supported')


def listen_android(
        device='/dev/input/event2',
        window_size=None,
        max_xy=None
):
    """
     监听 android 的轨迹
    :param device: 通过 adb shell getevent -lp 找到和屏幕相关的设备, 可以输出后复制给 GPT 帮忙找
    :param window_size: 可不传
    :param max_xy: 可不传
    :return:
    """
    xy_pattern = re.compile(r'(\d+\.\d+).*ABS_MT_POSITION_([XY])\s+(\w+)')
    flag_pattern = re.compile(r'(\d+\.\d+).*BTN_TOUCH\s+(\w+)')

    def get_screen_resolution():
        """获取手机屏幕分辨率"""
        res = subprocess.run(['adb', 'shell', 'wm', 'size'], capture_output=True, text=True)
        resolution = re.search(r'(\d+)x(\d+)', res.stdout)
        if resolution:
            width, height = map(int, resolution.groups())
            return width, height
        else:
            raise Exception("无法获取屏幕分辨率")

    def get_max_xy():
        """获取手机屏幕分辨率"""
        res = subprocess.run('adb shell dumpsys input'.split(' '), capture_output=True, text=True)
        resolution = re.findall(r'([XY]): min=0, max=(\d+)', res.stdout)
        max_x, max_y = 0, 0
        for r in resolution:
            if r[0] == 'X':
                max_x = int(r[1])
            elif r[0] == 'Y':
                max_y = int(r[1])
            if max_x and max_y:
                return max_x, max_y
        raise Exception("无法获取最大像素值")

    def get_radio():
        sx, sy = window_size or get_screen_resolution()
        max_x, max_y = max_xy or get_max_xy()
        return sx / max_x, sy / max_y

    radio_x, radio_y = get_radio()
    process = subprocess.Popen(
        ['adb', 'shell', 'getevent', '-lt', device],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    flag = False
    x, y, t = 0, 0, 0
    x0, y0, t0 = 0, 0, 0
    track_list = []
    try:
        for line in process.stdout:
            if flag_match := re.findall(flag_pattern, line):
                ts, action = flag_match[0]
                if action == 'DOWN':
                    flag = True
                elif action == 'UP':
                    logger.debug(track_list)
                    put2queue(track_list.copy())
                    track_list.clear()
                    x0, y0, t0 = 0, 0, 0
                    x, y, t = 0, 0, 0
                    flag = False
            if not flag:
                continue
            xy_match = re.findall(xy_pattern, line)
            if not xy_match:
                continue
            ts, xy, value_hex = xy_match[0]
            value = int(value_hex, 16)
            if xy == 'X':
                x = value
                t = int(float(ts) * 1000)
            elif xy == 'Y':
                if t != int(float(ts) * 1000):
                    x = 0
                    continue
                y = value
            if all([x, y, t]):
                if not any([x0, y0, t0]):
                    x0, y0, t0 = x, y, t
                track_list.append(((x - x0) * radio_x, (y - y0) * radio_y, t - t0))
                x, y, t = 0, 0, 0
    except KeyboardInterrupt:
        pass
    finally:
        # 确保进程结束
        process.terminate()


def listen_pc(
        interval=0.001
):
    try:
        from pynput.mouse import Listener
    except ImportError:
        logger.error(
            '请安装 pynput 库 -- 参考指令: pip install -i https://pypi.tuna.tsinghua.edu.cn/simple pynput==1.7.6')
        return

    # 可变化的原点
    x0, y0, t0 = 0, 0, 0
    # 录制标志
    flag = False
    # 临时队列
    res = []

    def on_move(x, y):
        nonlocal t0
        now = int(time.time() * 1000)
        if t0 == 0:
            t0 = now
        res.append((int(x - x0), int(y - y0), int(time.time() * 1000) - t0))
        time.sleep(interval)

    def on_click(x, y, button, pressed):  # noqa
        nonlocal flag, res, x0, y0, t0
        flag = not flag
        logger.debug('开始录制' if flag else '结束录制')
        if flag:
            x0, y0, t0 = x, y, 0
            res.clear()
        else:
            now = res.copy()
            logger.info(now)
            put2queue(now)

    with Listener(on_move=on_move, on_click=on_click) as listen:
        listen.join()


def save_data(data, filename=None, min_length=100, save_mode='override'):
    data = [_ for _ in data if len(_) > min_length]
    if not data:
        logger.debug(f'未有符合条件的轨迹,不保存')
        return
    if filename:
        logger.debug(f'保存历史轨迹至文件 {filename}: {json.dumps(data)}')
        if save_mode == 'override':
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f)  # noqa
        else:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception:  # noqa
                data = []
            data.extend(data)
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f)  # noqa


def get_track(
        distance: int,
        track_list: list = None,
        max_dis=1000,
        file_name="",
        min_node=100,
        tag=None
):
    """
    获取随机轨迹
    :param distance: 需生成的轨迹长度, 需要小于 max_dis 以及 track_list中的最小长度的三分之一, 用以保证轨迹的随机性
    :param track_list: 自带轨迹, 在该轨迹中随机选取一段轨迹
    :param max_dis: 限制最大传入长度
    :param file_name: 需要读取的文件名
    :param min_node: 最少的节点数, 用以保证轨迹的随机性
    :param tag: 
    :return:
    """

    def get_track_list() -> list:
        """
        获取 track_list 信息

        :return: track_list 信息
        """
        try:
            with open(file_name, 'r', encoding='utf-8') as f:
                _track_list = json.load(f)
            return _track_list
        except Exception as e:
            raise RuntimeError(f'[请求失败] 失败原因: 获取 track_list 信息 失败，失败信息：{str(e)}')

    def binary_search(lis: list, x, left=None, right=None, ):
        """
        二分查找
        :param lis: 被查找的队列
        :param x: 目标值
        :param left: 起始点
        :param right: 结束点
        :return:
        """
        left = left or 0
        right = right or len(lis)
        while left <= right:
            mid = left + (right - left) // 2
            if lis[mid] == x:
                return mid
            elif lis[mid] > x:
                right = mid - 1
            else:
                left = mid + 1
        return right

    def get_one_track():
        """
        获取一条轨迹
        :return:
        """
        one_track_xy = choice(track_list)
        if len(one_track_xy) < min_node:
            logger.debug(f'轨迹节点数小于 {min_node}, 重新获取轨迹')
            return get_one_track()
        one_track = [_[0] for _ in one_track_xy]
        start_index = randint(0, len(one_track) - 2)
        last = one_track[-1]
        start = one_track[start_index]
        return last, start, one_track, one_track_xy, start_index

    def get_target_track():
        """
        获取目标轨迹
        :return:
        """
        last, start, one_track, one_track_xy, start_index = get_one_track()
        while last - start < distance:
            last, start, one_track, one_track_xy, start_index = get_one_track()
        target = start + distance
        target_index = binary_search(one_track, target)
        _res = one_track_xy[start_index: target_index + 2]
        start_row = _res[0]
        _result = []
        for _ in _res:
            _result.append([_[i] - start_row[i] for i in range(len(_))])
        _distance = target - start_row[0]
        while _result[-2][0] >= _distance:
            _result.pop(-1)
        _result[-1][0] = target - start_row[0]
        return _result

    while not (track_list or GLOBAL_INFO[f'$track_list_{tag}']):
        # 只有拿到锁之后才会去获取 track_list 指纹
        if lock.acquire():
            try:
                GLOBAL_INFO[f'$track_list_{tag}'] = get_track_list()
            finally:
                lock.release()
        else:
            logger.debug('等待 track_list 获取')
            time.sleep(5)

    track_list = track_list or [json.loads(_['track']) for _ in GLOBAL_INFO[f'$track_list_{tag}']]

    assert track_list != [], "未获取到符合条件的 track_list !"

    if distance > max_dis:
        raise ValueError('Distance 太大了')

    track = get_target_track()
    return track


if __name__ == '__main__':
    # print(get_track(130, tag='default'))
    listener(filename='a.json', tag='low1', plat='pc')

if __name__ == '__main__':
    pass
