# -*- coding: utf-8 -*-
"""
@File    : utils.py
@Date    : 2024/4/16 下午8:17
@Author  : yintian
@Desc    : 
"""
import re
import subprocess
import sys
from typing import Literal

import importlib_metadata

from ytools.log import logger

PACKAGE_REGEX = re.compile(r"([a-zA-Z0-9_\-]+)([<>=]*)([\d.]*)")


def require(
        package_spec: str,
        action: Literal["raise", "fix"] = "fix"
) -> str:
    """
    依赖 python 包

    :param action:
    :param package_spec: pymongo==4.6.0 / pymongo
    :return: 安装的包版本号
    """
    # 分离包名和版本规范
    match = PACKAGE_REGEX.match(package_spec)
    assert match, ValueError("无效的包规范")

    package, operator, required_version = match.groups()

    try:
        # 获取已安装的包版本
        installed_version = importlib_metadata.version(package)
        # 检查是否需要安装或更新
        if required_version and not eval(f'{installed_version!r} {operator} {required_version!r}'):
            raise importlib_metadata.PackageNotFoundError
        else:
            return installed_version

    except importlib_metadata.PackageNotFoundError:

        # 包没有安装或版本不符合要求
        install_command = package_spec if required_version else package
        cmd = [sys.executable, "-m", "pip", "install", install_command]
        if action == "raise":
            raise importlib_metadata.PackageNotFoundError(f"依赖包不符合要求, 请使用以下命令安装: {' '.join(cmd)}")
        else:
            logger.debug(f"依赖包不符合要求, 自动修正, 命令: {' '.join(cmd)}")
            subprocess.check_call(cmd)
            return importlib_metadata.version(package)


if __name__ == '__main__':
    pass
