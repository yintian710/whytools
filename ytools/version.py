# -*- coding: utf-8 -*-
"""
@File    : version.py
@Author  : yintian
@Date    : 2025/6/23 14:02
@Software: PyCharm
@Desc    : 
"""
import os

from ytools.utils.magic import require

require("packaging")

from packaging.version import Version


def get_version(package='ytools', show=False, path=__file__):
    this_dir = os.path.dirname(os.path.dirname(path))
    version_path = os.path.join(this_dir, package, 'VERSION')
    if not os.path.exists(version_path):
        print(f'未找到 VERSION 文件')
        return
    with open(version_path, 'r') as f:
        version = f.read()
    show and print(version)
    return version


def update_version(version=None, update_type='auto', package='ytools', save=True, path=__file__):
    # 读取当前版本
    version = version or get_version(package=package, path=path)
    try:
        v = Version(version)
    except:  # noqa
        raise ValueError(f"无效的版本号格式: {version}")

    # 提取版本组件
    major = v.major
    minor = v.minor
    micro = v.micro
    pre = v.pre  # 预发布版本 (例如: ('b', 1))
    dev = v.dev  # 开发版本
    post = v.post  # 后发布版本
    epoch = v.epoch  # 纪元版本

    if update_type == 'auto' and pre:
        update_type = 'pre'

    # 根据更新类型处理版本
    if update_type in ('micro', 'auto'):
        micro += 1
        pre = post = dev = None
    elif update_type == 'minor':
        minor += 1
        micro = 0
        pre = post = dev = None
    elif update_type == 'major':
        major += 1
        minor = micro = 0
        pre = post = dev = None
    elif update_type.startswith('pre'):
        if pre:
            pre = (pre[0], pre[1] + 1)
        else:
            pre = (update_type[4:] if len(update_type) > 4 else 'a', 1)  # 默认创建alpha版本
            micro += 1
    else:
        raise ValueError(f"无效的更新类型: {update_type}")

    # 构建新版本号
    new_version = Version(f"{epoch}!{major}.{minor}.{micro}" +
                          (f"{pre[0]}{pre[1]}" if pre else "") +
                          (f".post{post}" if post else "") +
                          (f".dev{dev}" if dev else "")).public
    save and save_version(new_version, package, path=path)
    return new_version


def save_version(version, package='ytools', path=__file__):
    this_dir = os.path.dirname(os.path.dirname(path))
    version_path = os.path.join(this_dir, package, 'VERSION')
    # 写回文件
    with open(version_path, 'w') as f:
        f.write(str(version) + '\n')


def is_main_version(version):
    try:
        v = Version(version)
    except:  # noqa
        raise ValueError(f"无效的版本号格式: {version}")
    return not any([v.post, v.dev, v.pre, v.epoch])


if __name__ == '__main__':
    update_version(save=False)
