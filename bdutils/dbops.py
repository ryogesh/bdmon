#!/usr/bin/python3
# -*- coding: utf-8 -*-

# Copyright (c) 2018  Yogesh Rajashekharaiah
# All Rights Reserved

""" dbops module
Supports db operations on postgres/mysql/ms sql server database
"""
from time import sleep
import sqlite3

import pyodbc

from bdutils.coreutils import BDMonException, getdbdetails

__all__ = ['DbOps']


class DbOps():
    """ For database operations """
    def __init__(self, logger, dbdetail=''):
        self._lgr = logger
        self.stmt = ''
        self.values = ''
        if not dbdetail:
            dbdetail, rcnt, stime = getdbdetails(self._lgr)
        errmsg = ''

        for each in dbdetail.split(';'):
            if each.startswith('server'):
                dbsrvr = each.split('=')[1]
            elif each.startswith('port'):
                dbport = each.split('=')[1]
            elif each.startswith('driver'):
                dbtype = each.split('=')[1]
        for rtry in range(rcnt):
            try:
                if dbtype.lower() == '{sqlite}':
                    self._dbcn = sqlite3.connect(dbsrvr)
                else:
                    self._dbcn = pyodbc.connect(dbdetail)
            except (pyodbc.OperationalError, pyodbc.Error) as err:
                self._lgr.error(str(err))
                errmsg = 'BDM-DB-00: Unable to create connection to %s DB.' %dbtype
                self._lgr.error(errmsg)
                self._lgr.error('DB Host:%s; DB Port:%s Retry:%s' %(dbsrvr, dbport, rtry+1))
                sleep(stime + rtry)
            except (sqlite3.OperationalError, sqlite3.Error) as err:
                self._lgr.error(str(err))
                errmsg = 'BDM-DB-01: Unable to open sqlite DB file: %s' %dbsrvr
                self._lgr.error(errmsg)
                break
            else:
                if dbtype.lower() != '{sqlite}':
                    self._dbcn.autocommit = False
                    self._lgr.debug("Created %s connection", dbtype)
                else:
                    self._dbcn.row_factory = sqlite3.Row
                    self._lgr.debug("Created sqlite connection")
                self.crsr = self._dbcn.cursor()
                if "SQL Server" in dbtype:
                    self.crsr.fast_executemany = True
                elif "PostgreSQL" in dbtype:
                    self._dbcn.setdecoding(pyodbc.SQL_WCHAR, encoding='utf-8')
                    self._dbcn.setencoding(encoding='utf-8')
                break
        if errmsg:
            raise BDMonException(errmsg)

    def execstmt(self):
        """ Execute the DB statements; cursor object can be iterated for the resultset"""
        try:
            self._lgr.debug("DB stmt: %s", self.stmt)
            self._lgr.debug("values: %s", self.values)
            if self.stmt.split()[0].lower() == 'insert':
                if self.values:
                    self.crsr.executemany(self.stmt, self.values)
                else:
                    self.crsr.executemany(self.stmt)
            else:
                if self.values:
                    self.crsr.execute(self.stmt, self.values)
                else:
                    self.crsr.execute(self.stmt)
        except (pyodbc.Error, sqlite3.Error) as err:
            errmsg = 'BDM-DB-05: Unable to execute query.'
            self._lgr.error(errmsg)
            self._lgr.error(self.stmt)
            self._lgr.error(str(err))
            raise BDMonException(err)

    def commitclose(self):
        """ Commit all cursor transactions and close the db connection """
        self._dbcn.commit()
        self._dbcn.close()

    def commit(self):
        """ Commit the cursor transaction"""
        try:
            self.crsr.commit()
        except AttributeError: #sqlite3
            self._dbcn.commit()

    def rollbackclose(self):
        """ Rollback all cursor transactions and close the db connection """
        self._dbcn.rollback()
        self._dbcn.close()

    def rollback(self):
        """ Rollback the cursor transaction"""
        try:
            self.crsr.rollback()
        except AttributeError: #sqlite3
            self._dbcn.rollback()

    def close(self):
        """Close the db connection """
        self._dbcn.close()
