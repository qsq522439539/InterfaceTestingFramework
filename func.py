#!/usr/bin/env python
# coding=utf-8

import hashlib


def gen_md5(password):
    '''
    :param password: 密码
    :return: md5加密
    '''
    return hashlib.md5(password.encode('utf-8')).hexdigest()
