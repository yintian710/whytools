# -*- coding: utf-8 -*-
"""
@File    : file.py
@Date    : 2024/4/15 下午7:29
@Author  : yintian
@Desc    : 
"""

from os import path


def get_file_read(filename, base_dir='', encoding='utf-8', mode='r', safe=False):
    file_path = path.join(base_dir, filename)
    if not path.exists(file_path):
        if safe:
            return ''
        raise FileNotFoundError(f'File not found: {file_path}')
    with open(file_path, encoding=encoding, mode=mode) as f:
        long_description = f.read()
    return long_description


if __name__ == '__main__':
    pass
