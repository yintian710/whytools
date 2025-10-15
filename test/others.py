# -*- coding: utf-8 -*-
"""
@File    : others.py
@Author  : yintian
@Date    : 2025/9/1 14:34
@Software: PyCharm
@Desc    : 
"""

import os


def replace_spaces_in_filenames(path):
    """
    遍历指定路径下的所有文件夹和子文件夹，将文件名中的空格替换为连字符(-)。

    Args:
        path (str): 要处理的文件夹路径
    """
    # 确保路径存在
    if not os.path.exists(path):
        print(f"路径 {path} 不存在")
        return

    # 使用 os.walk 遍历文件夹
    for root, dirs, files in os.walk(path):
        for filename in files:
            # 检查文件名是否包含空格
            if ' ' in filename:
                # 构造旧文件名和新文件名
                old_file_path = os.path.join(root, filename)
                new_filename = filename.replace(' ', '-')
                new_file_path = os.path.join(root, new_filename)

                try:
                    # 重命名文件
                    os.rename(old_file_path, new_file_path)
                    print(f"已将 '{old_file_path}' 重命名为 '{new_file_path}'")
                except OSError as e:
                    print(f"重命名文件 '{old_file_path}' 时出错: {e}")


# 示例用法
if __name__ == "__main__":
    # 替换为你想处理的文件夹路径
    folder_path = r"D:\yintian\project\ark_wiki"
    replace_spaces_in_filenames(folder_path)

if __name__ == '__main__':
    pass
