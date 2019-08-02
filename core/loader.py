#!/usr/bin/env python
# coding=utf-8

import os
import yaml
import xlrd
import configparser
from core.common import *


# 重写optionxform方法，修复源码中自动转为小写的问题
class MyConfigParser(configparser.ConfigParser):
    def __init__(self, defaults=None):
        configparser.ConfigParser.__init__(self, defaults=defaults)

    def optionxform(self, optionstr):
        return optionstr


class GetData(object):
    def __init__(self):
        self.work_path = os.path.abspath('.')
        self.yml_path = os.path.join(os.path.abspath('..'), 'test_api')
        self.excel_path = os.path.join(os.path.abspath('..'), 'test_cases')
        self.config_path = os.path.join(os.path.abspath('..'), 'config.ini')

    @staticmethod
    def change_api_name(apiname):
        """
        :param apiname: /api/user/login,  api_user_login
        :return:  统一转换为api_user_login
        """
        return '_'.join(apiname.lstrip('/').split('/')).strip('\r').strip('\n') if '/' in apiname else apiname

    def change_request_info(self, operation, *args):
        """
        :param operation: excel数据
        :param args: 要改变的数据，如：data.password=1
        :return: 被替换的yml数据
        """
        # 根据excel找到yml文件数据
        if operation['API Name'] != '':
            yml_data = self.get_yml_data(self.change_api_name(operation['API Name']))
            if not yml_data:
                print(u'没有对应的yml数据：{}'.format(self.change_api_name(operation['API Name'])))
                return {}
            # 逐个替换数据
            for i in args:
                parse_function(i, yml_data)
            return yml_data
        return {}

    def list_all_files(self, rootdir):
        """
        :param rootdir: 根目录
        :return: 目录下所有的文件
        """
        _files = []
        flist = os.listdir(rootdir)
        for i in range(0, len(flist)):
            path = os.path.join(rootdir, flist[i])
            if os.path.isdir(path):
                _files.extend(self.list_all_files(path))
            if os.path.isfile(path):
                _files.append(path)
        return _files

    def get_config_data(self, section, option=None):
        """
        :param section: 配置文件section
        :param option: 配置文件option
        :return: section下对应option值或者section下所有option值
        """
        config = MyConfigParser()
        config.read(self.config_path, encoding="utf-8-sig")
        if option:
            try:
                value = config.get(section, option)
            except BaseException as e:
                print(u'未找到相应的配置文件信息： section:{}, option:{}'.format(section, option), e)
                value = ''
        else:
            try:
                options = config.options(section)
                value = {option: config.get(section, option) for option in options}
            except BaseException as e:
                print(u'未找到相应的配置文件信息： section:{}'.format(section), e)
                value = ''
        return value

    def get_yml_data(self, name):
        """
        :param name: api的名称
        :return: 对应的数据 {name:{}}
        """
        # case可指定文件夹寻找yml文件
        folder = ''
        if '|' in name:
            folder_name = name.split('|')
            name = folder_name[-1]
            folder = '/'.join(folder_name[:-1])
        yml_files = self.list_all_files(self.yml_path + '/' + folder)
        for yml_file in yml_files:
            if str(yml_file).endswith('.yml'):
                with open(yml_file, 'rb') as f:
                    api_data = yaml.load(f)
                    if name in api_data.keys():
                        return api_data[name]
        return False

    def get_excel_files(self, allfiles, folder):
        # 文件夹下全部excel files
        excel_files = self.list_all_files(self.excel_path)
        # 根据配置文件信息寻找需要的excel名
        excel_names = self.get_config_data('CaseInfo', 'excel_name').split(
            ',') if not allfiles and not folder else allfiles.split(',')
        files = []
        if excel_names != ['']:
            for excel_name in excel_names:
                for excel_file in excel_files:
                    excel_name = excel_name + '.xlsx' if 'xlsx' not in excel_name else excel_name
                    if excel_file.endswith(excel_name) and '~$' not in excel_file:
                        files.append(excel_file)
        if folder:
            folder = folder.split(',') if ',' in folder else [folder]
            folder_path = [os.path.join(self.excel_path, f) for f in folder]
            for f_path in folder_path:
                if os.path.exists(f_path):
                    files.extend(self.list_all_files(f_path))
        # 保持顺序去重
        new_files = []
        for f in files:
            if f not in new_files and '~$' not in f:
                new_files.append(f)
        return new_files

    @staticmethod
    def change_check_point(check_point):
        if not isinstance(check_point, dict):
            try:
                check_point = [str(i).strip('\r\n') for i in check_point.split(';')] if check_point != '' else ''
            except BaseException as e:
                print('check point填写错误：{}'.format(check_point), e)
            # 如："Check Point": { "code": ["0","=" ], "data.ord_id": [ "1","in"],"msg": ["\u6210\u529f","="]
            check_point = {re.split('\s(=|in|notin)\s', c)[2]: [re.split('\s(=|in|notin)\s', c)[0],
                                                                re.findall('\s(=|in|notin)\s', c)[0]] for c in
                           check_point} if check_point != '' else ''
        return check_point

    def get_case_data(self, allfiles='', folder=''):
        '''
        :return: excel中所有case的数据 [[{}]],一层为excel,二层为sheet，三层为sheet内信息
        '''
        files = self.get_excel_files(allfiles, folder)
        if not files:
            return []
        all_caseinfo = []
        # 遍历所有要执行的excel
        for file in files:
            filename = os.path.split(file)[1].replace('.xlsx', '')
            try:
                test_case = xlrd.open_workbook(file)
            except PermissionError:
                pass
            sheets = test_case.sheet_names()
            sheetinfo = []
            # 遍历所有sheet
            for sheet in sheets:
                test_data = {}
                table = test_case.sheet_by_name(sheet)
                test_data['sheet_name'] = filename + '_' + sheet
                try:
                    test_data['Active'] = table.cell(2, 1).value  # Active
                    # Active为No则跳过执行
                    if test_data['Active'] == 'No':
                        continue
                    test_data['case_name'] = table.cell(0, 1).value  # 名称
                    test_data['priority'] = table.cell(1, 1).value  # 优先级
                except:
                    print('{}缺少关键字段'.format(test_data['sheet_name']))
                    continue

                # 获取case列表的title
                title = {i: str(table.cell(4, i).value).strip().strip('\r').strip('\n') for i in range(table.ncols)}
                case_row = table.nrows
                # 获取setup、teardown信息行数
                for i in range(5, table.nrows):
                    description = str(table.cell(i, 0).value).strip().strip('\r').strip('\n').lower()
                    if description != 'setupclass' and description != 'teardownclass' and description != 'teardown' \
                        and description != 'setup':
                        case_row = i
                        break
                # setup、teardown、setupclass、teardownclass数据
                setup_or_teardown = [{title[i]: str(table.cell(j, i).value).strip().strip('\r').strip('\n')
                                      for i in range(table.ncols)} for j in range(5, case_row)]
                setup_list = [setup for setup in setup_or_teardown if str(setup['No.']).lower() == 'setup']
                teardown_list = [teardown for teardown in setup_or_teardown if
                                 str(teardown['No.']).lower() == 'teardown']
                setupclass_list = [setupclass for setupclass in setup_or_teardown if
                                   str(setupclass['No.']).lower() == 'setupclass']
                teardownclass_list = [teardownclass for teardownclass in setup_or_teardown
                                      if str(teardownclass['No.']).lower() == 'teardownclass']
                caselist = []
                # 所有的case信息
                for j in range(case_row, table.nrows):
                    case = {title[i]: str(table.cell(j, i).value).strip().strip('\r').strip('\n') for i in
                            range(table.ncols)}
                    # if case['Active'] == 'No' or case['API Name'] == '':
                    # 	continue
                    caselist.append(case)
                test_data['setup'] = setup_list
                test_data['teardown'] = teardown_list
                test_data['setupclass'] = setupclass_list
                test_data['teardownclass'] = teardownclass_list
                test_data['testcase'] = caselist
                sheetinfo.append(test_data)
            all_caseinfo.append(sheetinfo)
        return all_caseinfo


if __name__ == '__main__':
    a = GetData().get_yml_data('api_User_login')
    # print(a)