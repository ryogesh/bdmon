#!/usr/bin/python3
# -*- coding: utf-8 -*-

# Copyright (c) 2018  Yogesh Rajashekharaiah
# All Rights Reserved

""" coreutils module
Provides common utilities for all modules
"""
import os
import logging
from logging.handlers import RotatingFileHandler
import pwd
import base64

from configparser import ConfigParser, NoSectionError, NoOptionError

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


__all__ = ['BDMonException', 'getlgr', 'getdbdetails', 'gethbasedetails', 'gethivedetails', 'getsecsettings',
           'gethdfsdetails', 'getyarndetails', 'getzkdetails', 'getbdapplst', 'getsparkdetails']

_FLPATH = os.path.dirname(os.path.realpath(__file__))
_CONFIGFL = _FLPATH + '/../config/bdmon.ini'
_CFG = ConfigParser()

class BDMonException(Exception):
    """ Exception class for the  monitoring tool """


def getlgr(loglevel=logging.WARNING, logidentifier=''):
    """ Function provides a logger
    Parameters
    -----------
    loglevel : int, str
        Set the loglevel (default: WARNING)
    logidentifier : str
        Append identifier to log file name during multi process launch (default: '')

    Returns
    -------
    loghandle : lgr object
        lgr for generating file output
    """

    appname = 'BDMon'
    fappend = '_'.join((appname, os.uname()[1], logidentifier)).rstrip('_') + '.log'
    fmtstr = "%(levelname)1.1s %(asctime)s %(filename)s %(funcName)s %(lineno)d %(message)s"
    try:
        _CFG.read(_CONFIGFL)
        logfname = _FLPATH + _CFG.get('LOGS', 'LOCATION') + fappend
    except (NameError, NoSectionError, NoOptionError):
        logfname = _FLPATH + '/../logs/' + fappend
    lgr = logging.getLogger(appname)
    lgr.setLevel(loglevel)
    if not lgr.handlers:
        flh = RotatingFileHandler(logfname, mode="a", backupCount=3, maxBytes=5000000)
        fmt = logging.Formatter(fmtstr)
        flh.setFormatter(fmt)
        lgr.addHandler(flh)
        lgr.propagate = False
    return lgr

def getdbdetails(lgr=''):
    """ Function provides DB connection string"""
    if not lgr:
        lgr = getlgr()
    try:
        _CFG.read(_CONFIGFL)
        dbdetail = ''
        rcnt = 3
        rsleep = 2
        dbtype = 'ODBC'
        for name, value in _CFG.items(dbtype):
            if name == 'pwd':
                psswd = pwd.getpwuid(os.getuid())[0] + os.uname()[1] + os.uname()[4]
                psswd = psswd.encode()
                salt = ''.join(sorted(each for each in os.confstr_names if 'LDFLAG' in each))
                salt = salt.encode()
                kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt,
                                 iterations=100000, backend=default_backend()
                                )
                key = base64.urlsafe_b64encode(kdf.derive(psswd))
                frnt = Fernet(key)
                try:
                    value = frnt.decrypt(value.encode())
                except InvalidToken:
                    err = 'BDM-DBC-01: Unable to decrypt DB password, run "updatecfg.py" script'
                    lgr.error(err)
                    raise BDMonException(err)
                value = value.decode()
            if name == 'retry':
                rcnt = int(value)
            elif name == 'sleep':
                rsleep = int(value)
            else:
                dbdetail += name + '=' + value + ';'
    except (NameError, NoSectionError, NoOptionError):
        err = 'BDM-DB-02: Missing config file or DB config information for %s' %dbtype
        lgr.error(err)
        raise BDMonException(err)
    else:
        lgr.debug('Returing DB details, Retry count:%s, Sleep time:%s', rcnt, rsleep)
        return (dbdetail, rcnt, rsleep)

def gethdfsdetails(lgr=''):
    """ Function provides HDFS jmx config"""
    if not lgr:
        lgr = getlgr()
    try:
        _CFG.read(_CONFIGFL)
        hdfs = {'namenode':"localhost:50070", 'dnport': '50075', 'datanodes':'',
                'proto':'http', 'uripath':'/jmx', 'kerberos':'y'}
        for name, value in _CFG.items('HDFS'):
            lgr.debug("HDFS Name:%s, Value:%s", name, value)
            if name == 'namenode':
                hdfs["namenode"] = value
            elif name == 'datanodes':
                hdfs["datanodes"] = value
            elif name == 'dnport':
                hdfs["dnport"] = value
            elif name == 'tls' and value == 'y':
                hdfs["proto"] = 'https'
            elif name == 'uripath':
                hdfs["uripath"] = value
            elif name == 'kerberos':
                hdfs["kerberos"] = value
    except (NameError, NoSectionError, NoOptionError) as err:
        lgr.warning('HDFS config missing; assuming standalone local hdfs')
        lgr.warning('HDFS config error: %s', err)
    return hdfs

def gethbasedetails(lgr=''):
    """ Function provides Hbase jmx config"""
    if not lgr:
        lgr = getlgr()
    try:
        _CFG.read(_CONFIGFL)
        hbase = {'hmaster':"localhost:16010", 'rsport': '16030', 'regionservers':'',
                 'proto':'http', 'uripath':'/jmx', 'kerberos':'y'}
        for name, value in _CFG.items('HBASE'):
            lgr.debug("HBase Name:%s, Value:%s", name, value)
            if name == 'hmaster':
                hbase["hmaster"] = value
            elif name == 'rsport':
                hbase["rsport"] = value
            elif name == 'regionservers':
                hbase["regionservers"] = value
            elif name == 'tls' and value == 'y':
                hbase["proto"] = 'https'
            elif name == 'uripath':
                hbase["uripath"] = value
            elif name == 'kerberos':
                hbase["kerberos"] = value
    except (NameError, NoSectionError, NoOptionError) as err:
        lgr.warning('HBASE config missing; assuming standalone local hbase')
        lgr.warning('HBASE config error: %s', err)
    return hbase

def gethivedetails(lgr=''):
    """ Function provides HIVE Server jmx config"""
    if not lgr:
        lgr = getlgr()
    try:
        _CFG.read(_CONFIGFL)
        hive = {'hs2':"localhost:10002", 'proto':'http', 'uripath':'/jmx', 'kerberos':'y'}
        for name, value in _CFG.items('HIVE'):
            lgr.debug("Hive Name:%s, Value:%s", name, value)
            if name == 'hs2':
                hive["hs2"] = value
            elif name == 'tls' and value == 'y':
                hive["proto"] = 'https'
            elif name == 'uripath':
                hive["uripath"] = value
            elif name == 'kerberos':
                hive["kerberos"] = value
    except (NameError, NoSectionError, NoOptionError) as err:
        lgr.warning('HIVE Server config missing; assuming standalone local hive')
        lgr.warning('HIVE config error: %s', err)
    return hive

def getyarndetails(lgr=''):
    """ Function provides YARN jmx config"""
    if not lgr:
        lgr = getlgr()
    try:
        _CFG.read(_CONFIGFL)
        yarn = {'rm':"localhost:8088", 'nmport': '8042', 'nmnodes':'',
                'proto':'http', 'uripath':'/jmx', 'kerberos':'y'}
        for name, value in _CFG.items('YARN'):
            lgr.debug("yarn Name:%s, Value:%s", name, value)
            if name == 'rm':
                yarn["rm"] = value
            elif name == 'tls' and value == 'y':
                yarn["proto"] = 'https'
            elif name == 'uripath':
                yarn["uripath"] = value
            elif name == 'nmnodes':
                yarn["nmnodes"] = value
            elif name == 'nmport':
                yarn["nmport"] = value
            elif name == 'kerberos':
                yarn["kerberos"] = value
    except (NameError, NoSectionError, NoOptionError) as err:
        lgr.warning('YARN Server config missing; assuming standalone local yarn')
        lgr.warning('yarn config error: %s', err)
    return yarn

def getzkdetails(lgr=''):
    """ Function provides ZOOKEEPER quorum config"""
    if not lgr:
        lgr = getlgr()
    try:
        _CFG.read(_CONFIGFL)
        zkq = "localhost:2181"
        for _, value in _CFG.items('ZOOKEEPER'):
            zkq = value
    except (NameError, NoSectionError, NoOptionError) as err:
        lgr.warning('ZOOKEEPER Server config missing; assuming standalone local ZK')
        lgr.warning('ZK config error: %s', err)
    return zkq

def getsparkdetails(lgr=''):
    """ Function provides SPARK History Server config"""
    if not lgr:
        lgr = getlgr()
    try:
        _CFG.read(_CONFIGFL)
        spk = {'histsrvr':"localhost:18080", 'proto':'http', 'uripath':'/api/v1',
               'mtrxdate':'', 'kerberos':'y'}
        for name, value in _CFG.items('SPARK'):
            if name == 'histsrvr':
                spk["histsrvr"] = value
            elif name == 'tls' and value == 'y':
                spk["proto"] = 'https'
            elif name == 'uripath':
                spk["uripath"] = value
            elif name == 'mtrxdate':
                spk["mtrxdate"] = value
            elif name == 'kerberos':
                spk["kerberos"] = value
    except (NameError, NoSectionError, NoOptionError) as err:
        lgr.warning('Spark Server config missing; assuming standalone local spark')
        lgr.warning('Spark config error: %s', err)
    return spk

def getbdapplst(lgr=''):
    """ Function list of BD apps to monitor"""
    if not lgr:
        lgr = getlgr()
    try:
        _CFG.read(_CONFIGFL)
        applst = ['hdfs']
        for _, value in _CFG.items('BDAPPS'):
            applst = value.replace(' ', '').lower().split(',')
    except (NameError, NoSectionError, NoOptionError):
        lgr.warning('Applications to monitor missing; assuming hdfs only')
    return applst

def getsecsettings(lgr=''):
    """ Function for security config"""
    if not lgr:
        lgr = getlgr()
    try:
        _CFG.read(_CONFIGFL)
        sec = {'tlsverify':'y', 'kerberos':'n'}
        for name, value in _CFG.items('SECURITY'):
            if name == 'tlsverify' and value == 'n':
                sec["tlsverify"] = value
            elif name == 'kerberos' and value == 'y':
                sec["kerberos"] = value
    except (NameError, NoSectionError, NoOptionError) as err:
        lgr.warning('Security Server config missing; assuming verify TLS certificate, no Kerberos')
        lgr.warning('Security config error: %s', err)
    return sec
