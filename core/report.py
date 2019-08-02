# !/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from BeautifulReport import BeautifulReport


class Report(BeautifulReport):

    def __init__(self, suites):
        super(BeautifulReport, self).__init__(suites)
        self.suites = suites
        self.title = '自动化测试报告'
        self.filename = 'report.html'
        self.log_path = os.path.abspath('..') + '/report'
        self.config_tmp_path = os.path.abspath('..') + '/report/template'

    def report(self, api_num, description=None, filename: str = None, log_path='.'):
        if filename:
            self.filename = filename if filename.endswith('.html') else filename + '.html'

        if description:
            self.title = description
        self.suites.run(result=self)
        self.stopTestRun(self.title)
        self.FIELDS['apinum'] = api_num
        self.output_report()
        text = '\n测试已全部完成, 可前往{}查询测试报告'.format(self.log_path)
        print(text)