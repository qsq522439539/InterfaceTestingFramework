#!/usr/bin/env python
# coding=utf-8

import os
import re
import json
import requests
import random
import filetype
from requests_toolbelt.multipart.encoder import MultipartEncoder


def get_file_type(filepath):
    kind = filetype.guess(filepath)
    if kind is None:
        print('Cannot guess file type!')
        return
    return kind.mime


def get_response(url, method, headers=None, data=None, params=None):
    if str(method).lower() == 'get':
        resp = requests.get(url, headers=headers, params=params)
    elif str(method).lower() == 'post':
        resp = requests.post(url, headers=headers, data=data, params=params)
    elif str(method).lower() == 'delete':
        resp = requests.delete(url, headers=headers, params=params)
    elif str(method).lower() == 'put':
        resp = requests.put(url, headers=headers, data=data)
    else:
        print('请求method错误：{}'.format(method))
        return [-1]
    try:
        return [resp.status_code, resp.json(), resp.elapsed.total_seconds()]
    except json.decoder.JSONDecodeError:
        return [resp.status_code, resp.text, resp.elapsed.total_seconds()]


def multipart_form_data(url, headers, request_data, path=os.path.abspath('..') + '/file'):
    """
    :param url: 请求url
    :param headers: 包含token的请求头
    :param request_data: file=aaa.xlsx，isAdd=0
    :param path: 文件目录
    :return:
    """
    fname = ''
    for key, value in request_data.items():
        try:
            if re.match('.*?\..*?', request_data[key]):
                fname = key
                break
        except TypeError:
            pass
    if not fname:
        print('未识别出要上传的文件')
        return [-1]
    file = path + '/' + request_data[fname]
    filename = os.path.split(file)[1]
    if not os.path.exists(file):
        print('{}目录下没有此文件: {}'.format(path, filename))
        return [-1, '', '']
    content = 'application/octet-stream' if filename.endswith('.xlsx') or filename.endswith(
        '.xls')else get_file_type(file)
    try:
        fields = {
            fname: (os.path.basename(filename), open(file, 'rb'), content)
        }
    except BaseException as e:
        print('未找到相应文件：{}'.format(file), e)
        return [-1]
    for key, value in request_data.items():
        if key != fname:
            fields[key] = value if isinstance(value, str) else str(value)
    multipart_encoder = MultipartEncoder(
        fields=fields,
        boundary='-----------------------------' + str(random.randint(1e28, 1e29 - 1))
    )
    headers['content-type'] = multipart_encoder.content_type
    resp = requests.post(url, data=multipart_encoder, headers=headers)
    try:
        return [resp.status_code, resp.json(), resp.elapsed.total_seconds()]
    except json.decoder.JSONDecodeError:
        return [resp.status_code, resp.text, resp.elapsed.total_seconds()]

if __name__ == '__main__':
    print(get_response('https://am.addnewer.com/1', 'get'))
