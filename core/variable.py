# !/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sqlite3


class VariableSqlite(object):

    def __init__(self):
        self.variable_db = os.path.abspath('..') + '/variable.db'
        self.conn = sqlite3.connect(self.variable_db)
        self.create_variable_table()

    def execute_sql(self, sql, *args, **kwargs):
        cursor = self.conn.cursor()
        cursor.execute(sql, *args, **kwargs)
        result = cursor.fetchall()
        cursor.close()
        self.conn.commit()
        return result

    def create_variable_table(self):
        sql = "CREATE TABLE IF NOT EXISTS variable (name varchar(30) UNIQUE, value varchar(30))"
        self.execute_sql(sql)

    def insert_variable(self, name, value):
        sql = "INSERT OR REPLACE INTO variable (name, value) VALUES (?, ?)"
        self.execute_sql(sql, (name, str(value)))

    def select_variable(self, name):
        sql = "SELECT value from variable where name='{}'".format(name)
        try:
            result = self.execute_sql(sql)[0][0]
        except IndexError:
            result = None
        return result

    def truncate_table(self):
        sql = "delete from variable"
        self.execute_sql(sql)

    # def close_conn(self):
    #     self.conn.close()

if __name__ == '__main__':
    print(VariableSqlite().truncate_table())
