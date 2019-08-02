#!/usr/bin/env python
# coding=utf-8

import sys
sys.path.append('..')
import time
import unittest
from func import *
from core.loader import *
from core.variable import *
from core.response import *
from core.report import *
from core.common import *


@classmethod
def setUpClass(cls):
    config = argumentcheck()
    runner = Runner(config)
    cls.start_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    print("Start test at {}".format(cls.start_time))
    datas = eval(runner.variable.select_variable('setup_class_{}'.format(cls.__name__)))
    try:
        runner.generatot_case(datas, True)
    except BaseException as e:
        print('setUpClass执行失败: {}'.format(e))


@classmethod
def tearDownClass(cls):
    config = argumentcheck()
    runner = Runner(config)
    datas = eval(runner.variable.select_variable('teardown_class_{}'.format(cls.__name__)))
    try:
        runner.generatot_case(datas, True)
    except BaseException as e:
        print('tearDownClass执行失败: {}'.format(e))
    cls.end_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    print("End test at {}".format(cls.end_time))
    timestamp = time.mktime(time.strptime(cls.end_time, "%Y-%m-%d %H:%M:%S")) - \
                time.mktime(time.strptime(cls.start_time, "%Y-%m-%d %H:%M:%S"))
    print('\n运行时间：{}秒'.format(timestamp))


@unittest.skip('')
def skip_test_generator():
    pass


class Runner(object):

    def __init__(self, config):
        self.config = config
        self.load_data = GetData()
        self.variable = VariableSqlite()
        self.get_config_variable()
        self.api_list = []

    def get_config_variable(self):
        """
        将config.ini中的参数加入到变量中，可以在case中调用
        :return:
        """
        info = self.load_data.get_config_data(self.config['environment'])
        for key, value in info.items():
            self.variable.insert_variable(key, value)

    def get_all_data(self):
        """
        获取全部的case数据
        :return:
        """
        return self.load_data.get_case_data(self.config['file'], self.config['folder'])

    def change_value(self, value, cls, valuetype=1):
        """
        自定义函数和变量替换为值
        :param value: 自定义函数或变量或值
        :param cls: 类
        :param valuetype: check point中使用区分是response中的值还是正常值
        :return:
        """
        if re.match('\$\{.*?\}', value):
            new_v = parse_string_value(self.extract_functions(value))
            if cls:
                cls.assertIsNotNone(new_v)
            else:
                if new_v is None:
                    print('自定义函数{}返回结果为None'.format(value))
                    return None
        elif re.match('\$.*?', value):
            new_v = parse_string_value(self.variable.select_variable(value.replace('$', '')))
            if cls:
                cls.assertIsNotNone(new_v, '未定义变量{}'.format(value))
            else:
                if new_v is None:
                    print('未定义变量{}'.format(value))
                    return None
        else:
            if valuetype:
                new_v = parse_string_value(value)
            else:
                new_v = parse_string(value)
        return new_v

    def log_api(self, apiname):
        """
        记录测试过的接口
        :param apiname:
        :return:
        """
        if not re.match('\$\{.*?\}', apiname):
            if '|' in apiname:
                api = apiname.split('|')[1].replace('_', '/') if not re.findall('\d+', apiname) else '/'.join(apiname.split('|')[1].split('_')[:-1])
            else:
                api = apiname.replace('_', '/') if not re.findall('\d+', apiname) else '/'.join(apiname.split('_')[:-1])
            self.api_list.append(api)

    def write_api_log(self):
        with open(r'../report/api.txt', 'wb') as f:
            f.writelines(str(api + '\n').encode('utf8') for api in list(set(self.api_list)))

    def extract_functions(self, content):
        """
        执行content，${func(a,b,c)}格式的自定义函数
        :param content:
        :return:
        """
        function_regexp = r"\$\{([\w_]+\([\$\w\.\-/_ =,]*\))\}"
        content = re.findall(function_regexp, content)[0]
        params = re.findall('\((.*?)\)', content)[0].split(',')
        if not params == ['']:
            for n, p in enumerate(params):
                if re.match('\$.*?', p):
                    p = parse_string_value(self.variable.select_variable(p.replace('$', '')))
                else:
                    p = parse_string_value(p)
                params[n] = repr(p) if type(p) == str else p
            params = [i if isinstance(i, str) else str(i) for i in params]
            content = content.split('(')[0] + '(' + ','.join(params) + ')'
        try:
            return eval(content)
        except BaseException as e:
            print(u'参数输入错误：{}, {}'.format(content, e))
            return

    def generator_cls(self, clsname):
        """
        动态生成继承unittest的类方法
        :param clsname: 类名称
        :return:
        """
        TestSequense = type(clsname, (unittest.TestCase,), {})
        return TestSequense

    def change_yml_excel_data(self, yml_data, data, cls=None):
        """
        根据data替换yml中的data数据
        :param yml_data: yml数据
        :param data: 要替换的数据
        :param cls: 判断是否需要断言
        :return:
        """
        for key, value in yml_data.items():
            data[key] = value
        # 有Host信息则替换yml中的url对应的host
        host = str(data['Host']).strip()
        if host != '':
            new_host = self.load_data.get_config_data(self.config['environment'], host)
            data['url'] = new_host + '/' + data['url'].split('/', 3)[-1]
        data['Correlation'] = parse_data(data['Correlation'])
        data['Check Point'] = self.load_data.change_check_point(data['Check Point'])
        # 根据Request Headers和Request Data替换case_data中的数据
        for func in [data['Request Headers'], data['Request Data']]:
            func = parse_data(func)
            if func:
                for k, v in func.items():
                    k = k.split('.') if '.' in k else [k]
                    k = [parse_string_value(x) for x in k]
                    new_v = self.change_value(v, cls)
                    if new_v is None: return None
                    change_data(yml_data, new_v, k)
        return data

    def gen_response(self, data, cls=None):
        """
        请求获取返回值
        :param data: 请求数据
        :param cls: 判断是否需要断言
        :return:
        """
        method = data['method']
        url = data['url']
        headers = data['headers']
        request_data = ''
        try:
            content_type = data['headers']['content-type']
        except KeyError:
            content_type = ''
        # get方法
        if str(method).lower() == 'get':
            try:
                request_data = data['params']
            except KeyError:
                request_data = None
            resp = get_response(url, method, headers=headers, params=request_data)
        # post方法
        elif str(method).lower() == 'post':
            # json和data形式
            if 'multipart/form-data' not in content_type:
                request_data = json.dumps(data['json']) if 'json' in content_type else data['data']
                params = data['params'] if 'params' in data.keys() else None
                resp = get_response(url, method, headers, request_data, params)
            # 上传文件
            else:
                request_data = parse_data(data['Request Data'])
                for k, v in request_data.items():
                    request_data[k] = self.change_value(v, cls)
                resp = multipart_form_data(url, headers, request_data)
        elif str(method).lower() == 'delete':
            try:
                request_data = data['params']
            except KeyError:
                request_data = None
            resp = get_response(url, method, headers, params=request_data)
        elif str(method).lower() == 'put':
            headers = data['headers']
            request_data = json.dumps(data['json']) if 'json' in content_type else data['data']
            resp = get_response(url, method, headers, data=request_data)
        else:
            resp = get_response(url, method)
        print('url: {}\nmethod: {}\nheaders: {}\ndata: {}\nstatus code: {}\nresponse: {}\ntiming: {}s\n'.
              format(url, method, headers, request_data, resp[0], resp[1], resp[2]))
        return  resp, request_data

    def check_response(self, check_point, resp, cls=None):
        """
        断言方法
        :param check_point: 断言
        :param resp: 接口response
        :param cls: 判断是否需要断言
        :return:
        """
        # status code默认200
        status_code = parse_string_value(
            check_point['status_code'][0]) if check_point and 'status_code' in check_point.keys() else 200
        if cls:
            cls.assertEqual(resp[0], status_code, '返回status code：{}与预期：{}不符'.format(resp[0], status_code))
        else:
            if resp[0] != status_code:
                print('返回status code：{}与预期：{}不符'.format(resp[0], status_code))
                return
        if check_point:
            if 'status_code' in check_point.keys(): check_point.pop('status_code')
            for key, value in check_point.items():
                # 断言两侧值如果为自定义函数或者变量都替换为正常值
                new_key = self.change_value(key, cls, 0)
                new_value = self.change_value(value[0], cls, 1)
                # 断言中数字特殊处理，带''的数字处理为字符串
                if isinstance(new_value, str):
                    if re.search('\'\d+\'', new_value):
                        try:
                            new_value = re.findall('\'(.*?)\'', new_value)[0]
                        except:
                            new_value = new_value
                    else:
                        new_value = parse_string_value(new_value) if type(new_value) != list else new_value
                # 如果key为变量或自定义函数，取替换后的值
                if re.match('\$.*?', key):
                    assert_value = new_key
                # 为值则根据response取到定位的值
                else:
                    assert_value = eval(str(resp[1]) + str(new_key)) if type(
                        eval(str(resp[1]) + str(new_key))) != list else eval(str(resp[1]) + str(new_key))
                    if type(assert_value) == str:
                        assert_value = assert_value.replace('\n', '').replace('\r', '')
                if cls:
                    cls.assertIsNotNone(new_value, '未定义变量{}'.format(value))
                else:
                    if new_value is None:
                        print('未定义变量{}'.format(value))
                        return
                assertMethod = value[1] if value[1] != '=' else '=='
                assert_str = "'{}' {} '{}'".format(new_value, assertMethod, assert_value)
                if cls:
                    cls.assertTrue(eval(assert_str), '断言与预期不符：{}'.format(assert_str))
                else:
                    try:
                        if not eval(assert_str):
                            print('断言与预期不符：{}'.format(assert_str))
                    except BaseException as e:
                        print('{} 断言失败：{}'.format(assert_str, e))

    def gen_correlation(self, data, request_data, resp):
        """
        传递变量
        :param data: 数据
        :param request_data: 请求参数
        :param resp: 请求返回值
        :return:
        """
        for key, value in data['Correlation'].items():
            # 区分request和resp，分别取值
            if 'request.' in value:
                if 'json' in value:
                    value = parse_string(value.replace('request.json.', ''))
                    try:
                        self.variable.insert_variable(key, eval(str(json.loads(request_data)) + str(value)))
                    except KeyError:
                        print('设置变量错误,未根据{}在数据{}中找到变量'.format(str(value), str(json.loads(request_data))))
                        return False
                else:
                    value = parse_string(value.replace('request.data.', ''))
                    try:
                        self.variable.insert_variable(key, eval(str(request_data) + str(value)))
                    except KeyError:
                        print('设置变量错误,未根据{}在数据{}中找到变量'.format(str(value), str(request_data)))
                        return False
            else:
                value = parse_string(value)
                try:
                    self.variable.insert_variable(key, eval(str(resp[1]) + str(value)))
                except KeyError:
                    print('设置变量错误,未根据{}在数据{}中找到变量'.format(str(value), str(resp[1])))
                    return False
        return True

    def generatot_case(self, datas, isclass=False):
        """
        生成test方法
        :param datas:
        :param isclass:
        :return:
        """

        def test(self):
            if type(datas) == list:
                for data in datas:
                    case(data, self)
            else:
                case(datas, self)

        def case(data, cls):
            # setupclass和teardownclass不需要断言
            is_assert = False if str(data['No.']).lower() in ['teardownclass', 'setupclass'] else True
            # 判断是否为case
            isnot_case = str(data['No.']).lower() in ['teardown', 'setup', 'teardownclass', 'setupclass']
            # 除case外其他的API Name为空允许跳过执行
            if isnot_case:
                if data['API Name'] == '' or data['Active'] == 'No':
                    print('{}跳过执行'.format(data['No.']))
                    return
            else:
                cls.assertTrue(data['API Name'], 'API Name不可为空')
            # case为自定义函数，对返回值的格式有要求
            if re.match('\$\{.*?\}', data['API Name']):
                return_data = self.extract_functions(data['API Name'])
                # 要求case作为自定义函数，自定义函数返回值有要求，数组第一项判断case是否成功
                if is_assert:
                    cls.assertTrue(return_data[0], '自定义函数返回值：{}不符合判断case是否成功的规则'.format(return_data))
                else:
                    print('函数{}执行成功'.format(data['API Name']))
                    return
                try:
                    # 自定义函数传递变量，返回数组第二位作为变量
                    if data['Correlation']:
                        self.variable.insert_variable(data['Correlation'], return_data[1])
                except IndexError:
                    print('自定义函数返回值：{}不符合设置Correlation规则'.format(return_data))
                    return
                return
            # 根据API Name寻找yml文件
            yml_data = self.load_data.get_yml_data(self.load_data.change_api_name(data['API Name']))
            if is_assert:
                cls.assertTrue(yml_data, '未找到对应的yml文件数据：{}'.format(data['API Name']))
            else:
                if not yml_data:
                    print('未找到对应的yml文件数据：{}'.format(data['API Name']))
                    return
            if isnot_case:
                print('{}: '.format(data['No.']))
            else:
                print('case: ')
            # 请求接口获取返回值
            if is_assert:
                data = self.change_yml_excel_data(yml_data, data, cls)
                resp, request_data = self.gen_response(data, cls)
            else:
                data = self.change_yml_excel_data(yml_data, data)
                if data is None:
                    return
                resp, request_data = self.gen_response(data)
            # 断言
            if is_assert:
                self.check_response(data['Check Point'], resp, cls)
            else:
                self.check_response(data['Check Point'], resp)
            # 传递参数
            if data['Correlation']:
                assert_correlation = self.gen_correlation(data, request_data, resp)
                if is_assert:
                    cls.assertTrue(assert_correlation)


        return test(self) if isclass else test

    def run(self):
        # 清空variable表，避免上次测试变量影响本次测试结果
        try:
            self.variable.truncate_table()
        except sqlite3.OperationalError:
            pass
        loaded_testcases = []
        loader = unittest.TestLoader()
        # 遍历case数据
        for excel_datas in self.get_all_data():
            for sheet_data in excel_datas:
                # 动态生成unittest方法
                sheet_name = sheet_data['sheet_name']
                TestSequense = self.generator_cls(sheet_name)
                TestSequense.setUpClass = setUpClass
                TestSequense.tearDownClass = tearDownClass
                setupclass = sheet_data['setupclass']
                teardownclass = sheet_data['teardownclass']
                setup_data = sheet_data['setup']
                teardown_data = sheet_data['teardown']
                case_datas = sheet_data['testcase']
                setup = self.generatot_case(setup_data)
                teardown = self.generatot_case(teardown_data)
                self.variable.insert_variable('setup_class_{}'.format(sheet_name), str(setupclass))
                self.variable.insert_variable('teardown_class_{}'.format(sheet_name), str(teardownclass))
                setattr(TestSequense, 'setUp', setup)
                setattr(TestSequense, 'tearDown', teardown)
                for n, case_data in enumerate(case_datas):
                    test = self.generatot_case(case_data)
                    description = case_data['Description']
                    if case_data['Active'] == 'No':
                        setattr(TestSequense, 'test_{:03d}_{}'.format(n, description), skip_test_generator)
                    else:
                        self.log_api(case_data['API Name'])
                        setattr(TestSequense, 'test_{:03d}_{}'.format(n, description), test)
                loaded_testcase = loader.loadTestsFromTestCase(TestSequense)
                loaded_testcases.append(loaded_testcase)
        test_suite = unittest.TestSuite(loaded_testcases)
        api_num = len(list(set(self.api_list)))
        result = Report(test_suite)
        result.report(api_num)
        self.write_api_log()
        # runner = unittest.TextTestRunner()
        # runner.run(test_suite)


if __name__ == "__main__":
    config = argumentcheck()
    Runner(config).run()