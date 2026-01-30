# -*- coding: utf-8 -*-
"""
@File    : test_var.py
@Author  : yintian
@Date    : 2026/1/30 16:19
@Software: PyCharm
@Desc    : 
"""
import ytools

print(ytools.G)
ytools.init_var('G')
print(ytools.G, ytools.C, ytools.T)
ytools.init_var('T')
print(ytools.G, ytools.C, ytools.T)
ytools.init_var('C')
print(ytools.G, ytools.C, ytools.T)

if __name__ == '__main__':
    pass
