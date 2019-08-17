#!/usr/bin/python3
# -*- coding: utf-8 -*-

# Copyright (c) 2018  Yogesh Rajashekharaiah
# All Rights Reserved

""" Test module for bdmon; DB connections tests
"""
import sys
from os import path
import unittest
import time

class TestSetup(unittest.TestCase):
    """ Unit test for verifying database connectivity"""
    @classmethod
    def setUpClass(cls):
        cls.lgr = getlgr(loglevel=30, logidentifier='utest')
        cls.dbo = DbOps(cls.lgr)

    @classmethod
    def tearDownClass(cls):
        cls.lgr = None
        cls.dbo = None

    def setUp(self):
        self.test_strt = time.time()

    def tearDown(self):
        time_taken = time.time() - self.test_strt
        print('{} ({}s)'.format(self.id(), round(time_taken, 2)))

    def test_lgr(self):
        """ Verify logger"""
        self.assertIsNotNone(self.lgr)

    def test_conn_db(self):
        """ Open a DB connection """
        self.lgr.critical("Checking connectivity to DB")
        self.assertIsNotNone(self.dbo.crsr)

    def test_hdfs_tbls(self):
        """ Checks HDFS metrics collection tables exists """
        self.lgr.critical("Checking HDFS metrics collection tables")
        self.dbo.stmt = "Select namenode, is_active, modelerType, metricname, numvalue, collection_ts from t_hdfs_nn_metrics"
        self.dbo.execstmt()
        self.assertIsNotNone(self.dbo.crsr)
        self.dbo.stmt = "Select datanode, modelerType, metricname, numvalue, collection_ts from t_hdfs_dn_metrics"
        self.dbo.execstmt()
        self.assertIsNotNone(self.dbo.crsr)

    def test_zk_tbls(self):
        """ Checks Zookeeper metrics collection tables exists """
        self.lgr.critical("Checking Zookeeper metrics collection tables")
        self.dbo.stmt = "Select zknode, client_hostnode, metricname, numvalue, collection_ts from t_zk_conn_metrics"
        self.dbo.execstmt()
        self.assertIsNotNone(self.dbo.crsr)
        self.dbo.stmt = "Select zknode, zk_mode, metricname, numvalue, collection_ts from t_zk_metrics"
        self.dbo.execstmt()
        self.assertIsNotNone(self.dbo.crsr)

    def test_yarn_tbls(self):
        """ Checks YARN metrics collection tables exists """
        self.lgr.critical("Checking YARN metrics collection tables")
        self.dbo.stmt = "Select rmnode, modelerType, metricname, numvalue, collection_ts from t_yarn_rm_metrics"
        self.dbo.execstmt()
        self.assertIsNotNone(self.dbo.crsr)
        self.dbo.stmt = "Select nmnode, modelerType, metricname, numvalue, collection_ts from t_yarn_nm_metrics"
        self.dbo.execstmt()
        self.assertIsNotNone(self.dbo.crsr)

    def test_hive_tbls(self):
        """ Checks HIVE metrics collection tables exists """
        self.lgr.critical("Checking HIVE metrics collection tables")
        self.dbo.stmt = "Select hs2node, modelerType, metricname, numvalue, collection_ts from t_hive_metrics"
        self.dbo.execstmt()
        self.assertIsNotNone(self.dbo.crsr)

    def test_hbase_tbls(self):
        """ Checks HBase metrics collection tables exists """
        self.lgr.critical("Checking HBase metrics collection tables")
        self.dbo.stmt = "Select masternode, is_active, modelerType, metricname, numvalue, collection_ts from t_hmaster_metrics"
        self.dbo.execstmt()
        self.assertIsNotNone(self.dbo.crsr)
        self.dbo.stmt = "Select rsnode, modelerType, metricname, numvalue, collection_ts from t_hbase_rs_metrics"
        self.dbo.execstmt()
        self.assertIsNotNone(self.dbo.crsr)
        self.dbo.stmt = "Select namespace, tblname, regionid, metricname, numvalue, collection_ts from t_hbase_tbl_metrics"
        self.dbo.execstmt()
        self.assertIsNotNone(self.dbo.crsr)

    def test_spark_tbls(self):
        """ Checks HBase metrics collection tables exists """
        self.lgr.critical("Checking Spark metrics collection tables")
        self.dbo.stmt = "Select shshost, app_id, appname, start_ts, start_ts_str,sparkuser, time_taken from t_spark_apps"
        self.dbo.execstmt()
        self.assertIsNotNone(self.dbo.crsr)
        self.dbo.stmt = "Select app_id, sprkhost, metricname, numvalue, execution_ts from t_spark_executors"
        self.dbo.execstmt()
        self.assertIsNotNone(self.dbo.crsr)
        self.dbo.stmt = "Select app_id, stageid, metricname, numvalue, launch_ts from t_spark_stages"
        self.dbo.execstmt()
        self.assertIsNotNone(self.dbo.crsr)

    def test_bdmon_tbls(self):
        """ Checks self metrics collection tables exists """
        self.lgr.critical("Checking bdmon metrics collection tables")
        self.dbo.stmt = "Select bdmonhost, metricname, numvalue, collection_ts from t_bdmon_metrics"
        self.dbo.execstmt()
        self.assertIsNotNone(self.dbo.crsr)

if __name__ == '__main__':
    #Get to the base directory by traversing 3 times
    sys.path.append(path.dirname(path.dirname(path.dirname(path.abspath(__file__)))))
    from bdutils.coreutils import getlgr
    from bdutils.dbops import DbOps

    unittest.main()
