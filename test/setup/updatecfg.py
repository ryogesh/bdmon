#!/usr/bin/python3
# -*- coding: utf-8 -*-

# Copyright (c) 2018  Yogesh Rajashekharaiah
# All Rights Reserved

""" BDMONitor configuration update module"""

import sys
from getpass import getpass
import base64
import os
import pwd
import configparser as ConfigParser
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

_FLPATH = os.path.dirname(os.path.realpath(__file__))
CFGFL = _FLPATH + '/../config/bdmon.ini'

#print(CFGFL)
def upd_cfg():
    """ Updates the config file with encrypted password"""
    psswd = pwd.getpwuid(os.getuid())[0] + os.uname()[1] + os.uname()[4]
    psswd = psswd.encode()
    salt = ''.join(sorted(each for each in os.confstr_names if 'LDFLAG' in each))
    salt = salt.encode()
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt,
                     iterations=100000, backend=default_backend()
                    )
    key = base64.urlsafe_b64encode(kdf.derive(psswd))
    frnt = Fernet(key)

    db_supported = {'1':'{PostgreSQL}', '2':'{MySQL}', '3':'{SQL Server}', '4':'{SQLite}'}
    envval = os.getenv('BDMONDBTYPE')
    if envval:
        dbtype = envval
    else:
        print("Choose from the following database types:\n\
                1)Postgres\n\
                2)MySQL\n\
                3)MS SQL Server\n\
                4)SQLite")
        dbtype = input("Enter database type (1, 2, 3 or 4): ")

    if dbtype not in ('1', '2', '3', '4'):
        print("Enter supported database only, i.e. 1,2,3 or 4: ")
        print('exiting...')
        sys.exit(1)
    else:
        dbdriver = db_supported[dbtype]

    envval = os.getenv('BDMONDBSERVER')
    if envval:
        dbserver = envval
    else:
        if dbtype == '4':
            dbserver = input("Enter SQLite file full path(e.g. /etc/bdmon/bdmon.sqlite): ")
        else:
            dbserver = input("Enter database server hostname or IP address: ")

    if dbtype in ('1', '2', '3'):
        envval = os.getenv('BDMONDBPORT')
        if envval:
            dbport = envval
        else:
            dbport = input("Enter database server port: ")
        try:
            int(dbport)
            if int(dbport) < 1024 or int(dbport) > 65535:
                raise ValueError
        except ValueError:
            print('Invalid port number')
            print('exiting...')
            sys.exit(2)

        if dbtype != '4':
            envval = os.getenv('BDMONDBNAME')
            if envval:
                dbname = envval
            else:
                dbname = input("Enter database name: ")

        envval = os.getenv('BDMONDBUSER')
        if envval:
            dbuser = envval
        else:
            dbuser = input("Enter database user: ")

        envval = os.getenv('BDMONDBUSERPWD')
        if envval:
            pwd1 = envval
        else:
            pwd1 = getpass("Enter password for database user: ")
            pwd2 = getpass("Re-enter the password: ")
            if pwd1 != pwd2:
                print('Password do not match, try again')
                print('exiting...')
                sys.exit(3)
        token = frnt.encrypt(pwd1.encode())

    config = ConfigParser.ConfigParser()
    config.read(CFGFL)
    config.set('ODBC', 'DRIVER', dbdriver)
    if dbtype != '4':
        config.set('ODBC', 'SERVER', dbserver)
        config.set('ODBC', 'PORT', dbport)
        config.set('ODBC', 'DATABASE', dbname)
        config.set('ODBC', 'UID', dbuser)
        config.set('ODBC', 'PWD', token.decode())
    else:
        config.set('ODBC', 'SERVER', dbserver)
        config.remove_option('ODBC', 'PORT')
        config.remove_option('ODBC', 'DATABASE')
        config.remove_option('ODBC', 'UID')
        config.remove_option('ODBC', 'PWD')

    with open(CFGFL, 'w') as configfile:
        config.write(configfile)
    print("Configuration file updated successfully")
    if dbtype != '4':
        print("\n** Make sure to create the tables and run the insert statements **")
        print("DB scripts are available in the setup/db folder")
    else:
        print("\nSetting up the sqlite database tables")
        #Get to the base directory by traversing 2 times
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        #print(sys.path)
        from bdutils.coreutils import getlgr, BDMonException
        from bdutils.dbops import DbOps

        lgr = getlgr('DEBUG')
        dbo = DbOps(lgr)
        lgr.info('SQLite DB Connection ready')
        bdmon_tbls = {'t_coll_metrics': '''create table t_coll_metrics
                                        (appname text, appcomponent text,
                                        modelerType  text, mtypename  text, is_active text)
                                        ''',
                      't_node_metrics': '''create table t_node_metrics
                                        (hostnode text, appname   text, appcomponent text,
                                         metricname text, numvalue real, collection_ts text)
                                        ''',
                      't_hdfs_nn_metrics': '''create table t_hdfs_nn_metrics
                                        (namenode text, is_active text, modelerType text,
                                         metricname text, numvalue real, collection_ts text)
                                        ''',
                      't_hdfs_dn_metrics': '''create table t_hdfs_dn_metrics
                                        (datanode text, modelerType text,
                                         metricname text, numvalue real, collection_ts text)
                                        ''',
                      't_yarn_rm_metrics': '''create table t_yarn_rm_metrics
                                        (rmnode text, modelerType text,
                                         metricname text, numvalue real, collection_ts text)
                                        ''',
                      't_yarn_nm_metrics': '''create table t_yarn_nm_metrics
                                        (nmnode text, modelerType text,
                                         metricname text, numvalue real, collection_ts text)
                                        ''',
                      't_hmaster_metrics': '''create table t_hmaster_metrics
                                        (masternode text, is_active text, modelerType text,
                                         metricname text, numvalue real, collection_ts text)
                                        ''',
                      't_hbase_rs_metrics': '''create table t_hbase_rs_metrics
                                        (rsnode text, modelerType text,
                                         metricname text, numvalue real, collection_ts text)
                                        ''',
                      't_hbase_tbl_metrics': '''create table t_hbase_tbl_metrics
                                        (namespace text, tblname text, regionid text,
                                         metricname text, numvalue real, collection_ts text)
                                        ''',
                      't_hive_metrics': '''create table t_hive_metrics
                                        (hs2node text, modelerType text,
                                         metricname text, numvalue real, collection_ts text)
                                        ''',
                      't_zk_conn_metrics': '''create table t_zk_conn_metrics
                                        (zknode text, client_hostnode text,
                                         metricname text, numvalue real, collection_ts text)
                                        ''',
                      't_zk_metrics': '''create table t_zk_metrics
                                        (zknode text, zk_mode text,
                                         metricname text, numvalue real, collection_ts text)
                                        ''',
                      't_spark_apps': '''create table t_spark_apps
                                        (shshost text, app_id text, appname text,
                                         start_ts text, sparkuser text, start_ts_str text, time_taken real)
                                        ''',
                      't_spark_executors': '''create table t_spark_executors
                                        (app_id text, sprkhost text,
                                         metricname text, numvalue real, execution_ts text)
                                        ''',
                      't_spark_stages': '''create table t_spark_stages
                                        (app_id text, stageid integer,
                                         metricname text, numvalue real, launch_ts text)
                                        ''',
                      't_bdmon_metrics': '''create table t_bdmon_metrics
                                        (bdmonhost text,
                                         metricname text, numvalue real, collection_ts text)
                                        '''
                      }
        for tbl, stmt in bdmon_tbls.items():
            try:
                lgr.info('Create SQLite table %s', tbl)
                dbo.stmt = stmt
                dbo.execstmt()
            except BDMonException:
                print("Error while creating SQLite table:", tbl)

        dbo.stmt = "delete from t_coll_metrics"
        dbo.execstmt()
        print("Setup metrics events to collect")
        dbo.stmt = '''insert into t_coll_metrics (appname, appcomponent, modelerType, is_active)
                    values(?, ?, ?, ?)'''
        dbo.values = [('hdfs', 'namenode', 'JvmMetrics', 'Y'),
                      ('hdfs', 'namenode', 'StartupProgress', 'Y'),
                      ('hdfs', 'namenode', 'sun.management.OperatingSystemImpl', 'Y'),
                      ('hdfs', 'namenode', 'FSNamesystem', 'Y'),
                      ('hdfs', 'namenode', 'RpcDetailedActivityForPort', 'N'),
                      ('hdfs', 'namenode', 'MetricsSystem,sub=Stats', 'N'),
                      ('hdfs', 'namenode', 'NameNodeActivity', 'Y'),
                      ('hdfs', 'namenode', 'org.apache.hadoop.hdfs.server.namenode.FSNamesystem', 'Y'),
                      ('hdfs', 'namenode', 'RpcActivityForPort', 'Y'),
                      ('hdfs', 'namenode', 'UgiMetrics', 'N'),
                      ('hdfs', 'datanode', 'sun.management.OperatingSystemImpl', 'Y'),
                      ('hdfs', 'datanode', 'JvmMetrics', 'Y'),
                      ('hdfs', 'datanode', 'MetricsSystem,sub=Stats', 'N'),
                      ('hdfs', 'datanode', 'FSDatasetState', 'Y'),
                      ('hdfs', 'datanode', 'RpcDetailedActivityForPort', 'N'),
                      ('hdfs', 'datanode', 'RpcActivityForPort', 'N'),
                      ('hdfs', 'datanode', 'DataNodeActivity-', 'Y'),
                      ('hdfs', 'datanode', 'UgiMetrics', 'N'),
                      ('hbase', 'hmaster', 'Master,sub=Balancer', 'N'),
                      ('hbase', 'hmaster', 'Master,sub=AssignmentManager', 'N'),
                      ('hbase', 'hmaster', 'sun.management.OperatingSystemImpl', 'Y'),
                      ('hbase', 'hmaster', 'MetricsSystem,sub=Stats', 'N'),
                      ('hbase', 'hmaster', 'Master,sub=FileSystem', 'N'),
                      ('hbase', 'hmaster', 'RegionServer,sub=IO', 'N'),
                      ('hbase', 'hmaster', 'Master,sub=Quotas', 'N'),
                      ('hbase', 'hmaster', 'Master,sub=Server', 'Y'),
                      ('hbase', 'hmaster', 'JvmMetrics', 'Y'),
                      ('hbase', 'hmaster', 'Master,sub=IPC', 'N'),
                      ('hbase', 'hmaster', 'UgiMetrics', 'N'),
                      ('hbase', 'regionserver', 'sun.management.OperatingSystemImpl', 'Y'),
                      ('hbase', 'regionserver', 'MetricsSystem,sub=Stats', 'N'),
                      ('hbase', 'regionserver', 'RegionServer,sub=IO', 'N'),
                      ('hbase', 'regionserver', 'RegionServer,sub=Regions', 'Y'),
                      ('hbase', 'regionserver', 'RegionServer,sub=Replication', 'N'),
                      ('hbase', 'regionserver', 'RegionServer,sub=TableLatencies', 'N'),
                      ('hbase', 'regionserver', 'JvmMetrics', 'Y'),
                      ('hbase', 'regionserver', 'RegionServer,sub=WAL', 'N'),
                      ('hbase', 'regionserver', 'RegionServer,sub=Tables', 'Y'),
                      ('hbase', 'regionserver', 'RegionServer,sub=Server', 'N'),
                      ('hbase', 'regionserver', 'RegionServer,sub=Memory', 'N'),
                      ('hbase', 'regionserver', 'RegionServer,sub=IPC', 'N'),
                      ('hbase', 'regionserver', 'UgiMetrics', 'N'),
                      ('yarn', 'rm', 'JvmMetrics', 'Y'),
                      ('yarn', 'rm', 'sun.management.OperatingSystemImpl', 'Y'),
                      ('yarn', 'rm', 'QueueMetrics,', 'Y'),
                      ('yarn', 'rm', 'CapacitySchedulerMetrics', 'Y'),
                      ('yarn', 'rm', 'ClusterMetrics', 'Y'),
                      ('yarn', 'rm', 'RpcDetailedActivityFor', 'N'),
                      ('yarn', 'rm', 'UgiMetrics', 'N'),
                      ('yarn', 'rm', 'sun.management.ThreadImpl', 'N'),
                      ('yarn', 'rm', 'MetricsSystem,sub=Stats', 'N'),
                      ('yarn', 'rm', 'RpcActivityFor', 'N'),
                      ('yarn', 'nm', 'JvmMetrics', 'Y'),
                      ('yarn', 'nm', 'sun.management.OperatingSystemImpl', 'Y'),
                      ('yarn', 'nm', 'NodeManagerMetrics', 'Y'),
                      ('yarn', 'nm', 'ShuffleMetrics', 'Y'),
                      ('yarn', 'nm', 'sun.management.ThreadImpl', 'N'),
                      ('yarn', 'nm', 'RpcDetailedActivityFor', 'N'),
                      ('yarn', 'nm', 'RpcActivityFor', 'N'),
                      ('yarn', 'nm', 'UgiMetrics', 'N'),
                      ('yarn', 'nm', 'MetricsSystem,sub=Stats', 'N')]
        dbo.execstmt()
        dbo.stmt = '''insert into t_coll_metrics (appname, appcomponent, modelerType, mtypename, is_active)
                    values(?, ?, ?, ?, ?)'''
        dbo.values = [('hive', 'hs2', 'com.codahale.metrics.JmxReporter$JmxCounter', '', 'Y'),
                      ('hive', 'hs2', 'sun.management.GarbageCollectorImpl', 'java.lang:type=GarbageCollector', 'Y'),
                      ('hive', 'hs2', 'com.codahale.metrics.JmxReporter$JmxGauge', '', 'Y'),
                      ('hive', 'hs2', 'com.codahale.metrics.JmxReporter$JmxMeter', '', 'Y'),
                      ('hive', 'hs2', 'MetricsSystem,sub=Stats', '', 'Y'),
                      ('hive', 'hs2', 'UgiMetrics', '', 'N'),
                      ('hive', 'hs2', 'sun.management.OperatingSystemImpl', '', 'Y'),
                      ('hive', 'hs2', 'com.codahale.metrics.JmxReporter$JmxTimer', 'metrics:name=api_runTasks', 'Y'),
                      ('hive', 'hs2', 'com.codahale.metrics.JmxReporter$JmxTimer', 'metrics:name=hs2_submitted_queries', 'Y'),
                      ('hive', 'hs2', 'com.codahale.metrics.JmxReporter$JmxTimer', 'metrics:name=api_TezRunDag', 'Y'),
                      ('hive', 'hs2', 'com.codahale.metrics.JmxReporter$JmxTimer', 'metrics:name=api_hs2_sql_operation_PENDING', 'Y'),
                      ('hive', 'hs2', 'com.codahale.metrics.JmxReporter$JmxTimer', 'metrics:name=api_RenameOrMoveFiles', 'Y'),
                      ('hive', 'hs2', 'com.codahale.metrics.JmxReporter$JmxTimer', 'metrics:name=api_compile', 'N'),
                      ('hive', 'hs2', 'com.codahale.metrics.JmxReporter$JmxTimer', 'metrics:name=api_optimizer', 'N'),
                      ('hive', 'hs2', 'com.codahale.metrics.JmxReporter$JmxTimer', 'metrics:name=hs2_compiling_queries', 'N'),
                      ('hive', 'hs2', 'com.codahale.metrics.JmxReporter$JmxTimer', 'metrics:name=api_waitCompile', 'N'),
                      ('hive', 'hs2', 'com.codahale.metrics.JmxReporter$JmxTimer', 'metrics:name=api_hs2_operation_INITIALIZED', 'N'),
                      ('hive', 'hs2', 'com.codahale.metrics.JmxReporter$JmxTimer', 'metrics:name=api_doAuthorization', 'N'),
                      ('hive', 'hs2', 'com.codahale.metrics.JmxReporter$JmxTimer', 'metrics:name=api_acquireReadWriteLocks', 'N'),
                      ('hive', 'hs2', 'com.codahale.metrics.JmxReporter$JmxTimer', 'metrics:name=hs2_executing_queries', 'N'),
                      ('hive', 'hs2', 'com.codahale.metrics.JmxReporter$JmxTimer', 'metrics:name=api_Driver.execute', 'N'),
                      ('hive', 'hs2', 'com.codahale.metrics.JmxReporter$JmxTimer', 'metrics:name=api_hs2_sql_operation_RUNNING', 'N'),
                      ('hive', 'hs2', 'com.codahale.metrics.JmxReporter$JmxTimer', 'metrics:name=api_Driver.run', 'N'),
                      ('hive', 'hs2', 'com.codahale.metrics.JmxReporter$JmxTimer', 'metrics:name=api_releaseLocks', 'N'),
                      ('hive', 'hs2', 'com.codahale.metrics.JmxReporter$JmxTimer', 'metrics:name=api_hs2_operation_RUNNING', 'N'),
                      ('hive', 'hs2', 'com.codahale.metrics.JmxReporter$JmxTimer', 'metrics:name=api_hs2_operation_PENDING', 'N'),
                      ('hive', 'hs2', 'com.codahale.metrics.JmxReporter$JmxTimer', 'metrics:name=api_parse', 'N'),
                      ('hive', 'hs2', 'com.codahale.metrics.JmxReporter$JmxTimer', 'metrics:name=api_semanticAnalyze', 'N'),
                      ('hive', 'hs2', 'com.codahale.metrics.JmxReporter$JmxTimer', 'metrics:name=api_TezBuildDag', 'N'),
                      ('hive', 'hs2', 'com.codahale.metrics.JmxReporter$JmxTimer', 'metrics:name=api_TezCompiler', 'N'),
                      ('hive', 'hs2', 'com.codahale.metrics.JmxReporter$JmxTimer', 'metrics:name=api_TezSubmitDag', 'N'),
                      ('hive', 'hs2', 'com.codahale.metrics.JmxReporter$JmxTimer', 'metrics:name=api_TezSubmitToRunningDag', 'N'),
                      ('hive', 'hs2', 'com.codahale.metrics.JmxReporter$JmxTimer', 'metrics:name=api_RemoveTempOrDuplicateFiles', 'N')]
        dbo.execstmt()
        dbo.commitclose()
        print("SQLite Database setup complete")
        print("\n** Make sure to update the configuration file for each service before capturing metrics **")

if __name__ == '__main__':
    upd_cfg()
