#!/usr/bin/env python
# coding=utf-8

import re
import ast
import sys
import getopt
import pymysql
from func import *


def parse_string_value(str_value):
    """
    :param str_value: str, 如：3, [1,2,3], {a:1, b:2}
    :return: str==>int, str==>list, str==> dict
    """
    if str_value is None: return None
    try:
        return ast.literal_eval(str_value)
    except ValueError:
        return str_value
    except SyntaxError:
        return str_value


def parse_data(data):
    """
    :param data: 字符串：data1.0.data2=3;data4=5
    :return: {data1.0.data2:3, data4:5}
    """
    if not isinstance(data, dict):
        data = data.split(';') if data != '' else ''
        # 去掉换行符
        data = [i.strip('\n') for i in data]
        data = {i.split('=')[0]: i.split('=')[1] for i in data} if data != '' else ''
    return data


def change_data(data, value, k, i=0):
    """
    :param data: 要修改的数组, 列表和字典的多层嵌套，如{'a':1, 'b':[{'c':2}, {'c':3}]}
    :param value: 要修改的值
    :param k: 要修改的数据坐标, list形式，如['a', 0, 'c']
    :param i: 不需要填，缺省为0
    """
    if not isinstance(k, list):
        print('参数输入错误: {}'.format(k))
        return
    if i == len(k) - 1:
        data[k[i]] = value
        return
    change_data(data[k[i]], value, k, i + 1)


def change_str(string_):
    new_str = parse_string_value(string_)
    return repr(new_str) if type(new_str) == str else new_str


def parse_string(str_value):
    """
    data ==> [data]
    data1.data2 ==> [data1][data2]
    """
    return ''.join(["[{}]".format(change_str(i)) for i in str_value.split('.')]) if '.' in str_value else [str_value]


def parse_function(func, data):
    """
    :param func: 如：data.password=1
    :param data: 要改变的数据
    :return: 改变后的数据
    """
    # 转换function形式为字典
    func = parse_data(func)
    if func:
        for k, v in func.items():
            k = k.split('.') if '.' in k else [k]
            k = [parse_string_value(x) for x in k]
            change_data(data, v, k)


def argumentcheck():
    config = {'environment': 'Test', 'file': '', 'folder': ''}
    try:
        opts, args = getopt.getopt(sys.argv[1:], "he:f:F:")
        for op, value in opts:
            if op == "-e":
                config['environment'] = value
            elif op == "-f":
                config['file'] = value
            elif op == "-F":
                config['folder'] = value
            elif op == "-h":
                usage()
    except:
        usage()
    return config


def usage():
    print('Usage: -e [environment] -f [file] -F [folder] -h')
    print('\t-e option: the environment in which the script is executed')
    print('\t-f option: excel name: execute the case file1,file2,file3....')
    print('\t-F option: folder name: execute the case under the folder1,folder2,folder3...')
    sys.exit(10)
