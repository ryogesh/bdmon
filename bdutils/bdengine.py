#!/usr/bin/python3
# -*- coding: utf-8 -*-

# Copyright (c) 2018  Yogesh Rajashekharaiah
# All Rights Reserved

""" Provides utilities for processing Big Data Apps metrics data """
import re
import  os
import sys
import socket
from datetime import datetime
import itertools
from math import isnan

import requests
import ujson

from bdutils.coreutils import gethbasedetails, gethdfsdetails, gethivedetails, getbdapplst, getlgr
from bdutils.coreutils import BDMonException, getzkdetails, getyarndetails, getsparkdetails
from bdutils.dbops import DbOps

__all__ = ['get_appmetrics']

class _SocketConn():
    """ Class to process jmx data for different applications """
    def __init__(self, lgr, host, port):
        self._host = host
        self._port = port
        self._lgr = lgr
        self.skt = None

    def __enter__(self):
        if self.skt is not None:
            raise BDMonException('BDM-SKT-01: Connection exists on %s:%s' %(self._host, self._port))
        self._lgr.info('Connecting to ZK node :%s at port:%s', self._host, self._port)
        self.skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.skt.settimeout(1.0)
        hostip = socket.gethostbyname(self._host)
        self._lgr.info("HOST IP to connect: %s", hostip)
        self.skt.connect((hostip, self._port))
        return self.skt

    def __exit__(self, exp_type, exp_val, trcbk):
        self.skt.shutdown(socket.SHUT_RDWR)
        self.skt.close()
        self.skt = None


class _BDMProcess():
    """ Class to collect and process metrics for different applications """

    _dbo_stmts = {'host_os':('insert into t_node_metrics '
                             '(hostnode, appname, appcomponent, metricname, numvalue, collection_ts) '
                             'values(?, ?, ?, ?, ?, ?)'),
                  'hdfs_namenode':('insert into t_hdfs_nn_metrics '
                                   '(namenode, is_active, modelerType, metricname, numvalue, collection_ts) '
                                   'values(?, ?, ?, ?, ?, ?)'),
                  'hdfs_datanode':('insert into t_hdfs_dn_metrics '
                                   '(datanode, modelerType, metricname, numvalue, collection_ts) '
                                   'values(?, ?, ?, ?, ?)'),
                  'yarn_rm':('insert into t_yarn_rm_metrics '
                             '(rmnode, modelerType, metricname, numvalue, collection_ts) '
                             'values(?, ?, ?, ?, ?)'),
                  'yarn_nm':('insert into t_yarn_nm_metrics '
                             '(nmnode, modelerType, metricname, numvalue, collection_ts) '
                             'values(?, ?, ?, ?, ?)'),
                  'hbase_hmaster': ('insert into t_hmaster_metrics '
                                    '(masternode, is_active, modelerType, metricname, numvalue, collection_ts) '
                                    'values(?, ?, ?, ?, ?, ?)'),
                  'hbase_regionserver': ('insert into t_hbase_rs_metrics '
                                         '(rsnode, modelerType, metricname, numvalue, collection_ts) '
                                         'values(?, ?, ?, ?, ?)'),
                  'hbase_table': ('insert into t_hbase_tbl_metrics '
                                  '(namespace, tblname, regionid, metricname, numvalue, collection_ts) '
                                  'values(?, ?, ?, ?, ?, ?)'),
                  'zk_conn_mtrx': ('insert into t_zk_conn_metrics '
                                   '(zknode, client_hostnode, metricname, numvalue, collection_ts) '
                                   'values(?, ?, ?, ?, ?)'),
                  'zk_mtrx': ('insert into t_zk_metrics '
                              '(zknode, zk_mode, metricname, numvalue, collection_ts) '
                              'values(?, ?, ?, ?, ?)'),
                  'hive_hs2': ('insert into t_hive_metrics '
                               '(hs2node, modelerType, metricname, numvalue, collection_ts) '
                               'values(?, ?, ?, ?, ?)'),
                  'spark_app': ('insert into t_spark_apps '
                                '(shshost, app_id, appname, start_ts, start_ts_str, sparkuser, time_taken) '
                                'values(?, ?, ?, ?, ?, ?, ?)'),
                  'spark_exec': ('insert into t_spark_executors '
                                 '(app_id, sprkhost, metricname, numvalue, execution_ts) '
                                 'values(?, ?, ?, ?, ?)'),
                  'spark_stgs': ('insert into t_spark_stages '
                                 '(app_id, stageid, metricname, numvalue, launch_ts) '
                                 'values(?, ?, ?, ?, ?)')
                 }

    def __init__(self, lgr, dbo, dct):
        self._lgr = lgr
        self._dbo = dbo
        self._appmtrx = dct
        self._host = ''
        self._proto = 'http'
        self._uripath = '/jmx'
        self.mtrx = {'error':0, 'warning':0}

    def _bulk_insdb(self):
        """Function to perform bulk inserts"""
        self._lgr.info("Insert count:%d", len(self._dbo.values))
        if self._dbo.values:
            self._dbo.execstmt()
            self._dbo.commit()
        else:
            self._lgr.info("No insert for statement: %s", self._dbo.stmt)
        self._dbo.stmt = ''
        self._dbo.values = ''

    def _ins_osdata(self, osdata, app, comp, cltime):
        """Function to insert node OS metrics"""
        self._lgr.debug("Processing the following OS info: %s", osdata)
        self._dbo.values = [(self._host, app, comp, key, val, cltime) \
                  for key, val in osdata.items() if hasattr(val, 'real') and not isnan(val)]
        self._dbo.stmt = self._dbo_stmts["host_os"]
        self._bulk_insdb()

    def get_metrics_hdfs(self):
        """Function to process HDFS namenode/snode jmx data"""
        ## Get the namenodes, uri protocol, uri_path
        hdfs = gethdfsdetails(self._lgr)
        self._proto = hdfs["proto"]
        self._uripath = hdfs["uripath"]
        nnodes = hdfs["namenode"].replace(' ', '').split(',')
        self._lgr.debug("Received HDFS config info:%s", hdfs)
        for node in nnodes:
            try:
                jdata = self._get_metrics(node)
                self._host = node.split(':')[0]
            except BDMonException as err:
                self._lgr.warning("Unable to get namenode metrics, ignoring Node:%s", node)
                self._lgr.warning("Received namenode error:%s", err)
                self.mtrx['warning'] += 1
                continue
            is_active = 'N'
            cltime = datetime.now()
            for mtrx in jdata["beans"]:
                if mtrx.get("tag.HAState", 'N') == 'active':
                    is_active = 'Y'
                elif mtrx.get("LiveNodes", "{}") != "{}":
                    self._lgr.info("Getting datanodes list")
                    if hdfs["datanodes"]: #restricted datanode list
                        dnodes = hdfs["datanodes"].replace(' ', '').split(',')
                        self._lgr.info("Restricted dataNodes: %s, Total:%s", dnodes, len(dnodes))
                    else: #Get the list of all datanodes
                        lnodes = ujson.loads(mtrx["LiveNodes"])
                        self._lgr.info("DataNodes to process: %s", lnodes.keys())
                        dnodes = [lnodes[dna]["infoAddr"] for dna in lnodes]
            for mtrx in jdata["beans"]:
                mtype = mtrx["modelerType"]
                self._lgr.debug("NameNode:%s ; Check metrics:%s", self._host, mtype)
                #Metrics can be a substring from the start, hence the startswith
                #comes in handy with a lot metrics of the similar modelerType
                #e.g. instead of "sun.management.OperatingSystemImpl", it can be "sun.management.O"
                #self._appmtrx: Dict {appname:{appcomponent:[(modelertype1, mtypename1),...]}}
                if [mx for mx in self._appmtrx['hdfs']['namenode'] if mtype.startswith(mx[0])]:
                    self._lgr.info("NameNode:%s ; Process metrics:%s", self._host, mtype)
                    if mtype == "sun.management.OperatingSystemImpl":
                        self._ins_osdata(mtrx, 'hdfs', 'namenode', cltime)
                    else:
                        self._dbo.values = [(self._host, is_active, mtype, key, val, cltime) \
                                            for key, val in mtrx.items()
                                            if hasattr(val, 'real') and not isnan(val)]
                        self._dbo.stmt = self._dbo_stmts["hdfs_namenode"]
                        self._bulk_insdb()
        #Namenodes complete, now process datanodes
        try:
            self._lgr.info("Datanodes list: %s", dnodes)
            self._get_metrics_workers(dnodes, hdfs["dnport"], 'hdfs', 'datanode')
        except UnboundLocalError as err:
            errmsg = "BDM-HD-00: Looks like we don't have an active Namenode"
            self._lgr.error(errmsg)
            self._lgr.error("%s", err)
            self.mtrx['error'] += 1
            raise BDMonException(errmsg)

    def _get_metrics_workers(self, wnodes, cnfgport, app, appcomp):
        """Function to process HDFS datanodes, HBase regionservers jmx data"""
        for node in wnodes:
            #if datanodes, rs, nm port not specified then use port from config file
            try:
                if ':' in node:
                    jdata = self._get_metrics(node)
                    self._host = node.split(':')[0]
                else:
                    self._lgr.info("Defaulting port for %s:", node)
                    self._host = node
                    jdata = self._get_metrics(node + ":" + cnfgport)
            except BDMonException as err:
                self._lgr.warning("Unable to get worker node metrics, ignoring Node:%s", node)
                self._lgr.warning("Received node error:%s", err)
                self.mtrx['warning'] += 1
                continue
            cltime = datetime.now()
            for mtrx in jdata["beans"]:
                #Process only the required metrics on datanodes/regionservers
                mtype = mtrx["modelerType"]
                self._lgr.debug("%s:%s ; Check metrics:%s", appcomp, self._host, mtype)
                if [mx for mx in self._appmtrx[app][appcomp] if mtype.startswith(mx[0])]:
                    self._lgr.info("%s:%s ; Process metrics:%s", appcomp, self._host, mtype)
                    if mtype == "sun.management.OperatingSystemImpl":
                        self._ins_osdata(mtrx, app, appcomp, cltime)
                    elif mtype in ("RegionServer,sub=TableLatencies", "RegionServer,sub=Regions", \
                                   "RegionServer,sub=Tables"):
                        self._lgr.debug("Processing the following HBase table info: %s", mtrx)
                        self._dbo.values = []
                        for key, val in mtrx.items():
                            if hasattr(val, 'real') and key.startswith("Namespace_"):
                                #(namespace, tblname, regionid, metricname, numvalue, collection_ts)
                                vals = key.split('_')
                                regionid = ''
                                mtrxname = vals[5]
                                if "_region_" in key:
                                    regionid = vals[5]
                                    mtrxname = vals[7]
                                self._dbo.values.append((vals[1], vals[3], regionid, mtrxname,
                                                         val, cltime))
                        self._dbo.stmt = self._dbo_stmts["hbase_table"]
                        self._bulk_insdb()
                    else:
                        self._dbo.values = [(self._host, mtype, key, val, cltime) \
                                            for key, val in mtrx.items()
                                            if hasattr(val, 'real') and not isnan(val)]
                        self._dbo.stmt = self._dbo_stmts[app + "_" + appcomp]
                        self._bulk_insdb()

    def get_metrics_hbase(self):
        """Function to process Hbase/Hmaster jmx data"""
        hbase = gethbasedetails(self._lgr)
        self._proto = hbase["proto"]
        self._uripath = hbase["uripath"]
        hbnodes = hbase["hmaster"].replace(' ', '').split(',')
        self._lgr.debug("Received HBase config info:%s", hbase)
        for node in hbnodes:
            try:
                jdata = self._get_metrics(node)
                self._host = node.split(':')[0]
            except BDMonException as err:
                self._lgr.warning("Unable to get HMaster metrics, ignoring Node:%s", node)
                self._lgr.warning("Received Hmaster error:%s", err)
                self.mtrx['warning'] += 1
                continue
            is_active = 'N'
            cltime = datetime.now()
            for mtrx in jdata["beans"]:
                if mtrx["modelerType"] == "Master,sub=Server" and \
                   mtrx["tag.isActiveMaster"] == "true":
                    is_active = 'Y'
                    self._lgr.info("Getting regionservers list")
                    if hbase["regionservers"]: #restricted regionservers
                        rsrvrs = hbase["regionservers"].replace(' ', '').split(',')
                        self._lgr.info("Restricted RS: %s, Total:%s", rsrvrs, len(rsrvrs))
                    else: #Get the list of all regionservers
                        rsnodes = mtrx["tag.liveRegionServers"]
                        self._lgr.info("RSNodes to process: %s", rsnodes)
                        rsrvrs = [rs.split(',')[0] for rs in rsnodes.split(';')]
                    break
            for mtrx in jdata["beans"]:
                mtype = mtrx["modelerType"]
                self._lgr.debug("HMaster:%s ; Check metrics:%s", self._host, mtype)
                #self._appmtrx: Dict {appname:{appcomponent:[(modelertype1, mtypename1),...]}}
                if [mx for mx in self._appmtrx['hbase']['hmaster'] if mtype.startswith(mx[0])]:
                    self._lgr.info("HMaster:%s ; Process metrics:%s", self._host, mtype)
                    if mtype == "sun.management.OperatingSystemImpl":
                        self._ins_osdata(mtrx, 'hbase', 'hmaster', cltime)
                    else:
                        self._dbo.values = [(self._host, is_active, mtype, key, val, cltime) \
                                            for key, val in mtrx.items()
                                            if hasattr(val, 'real') and not isnan(val)]
                        self._dbo.stmt = self._dbo_stmts["hbase_hmaster"]
                        self._bulk_insdb()
        #Hmasters complete, now process regionservers
        try:
            self._lgr.info("RegionServer list: %s", rsrvrs)
            self._get_metrics_workers(rsrvrs, hbase["rsport"], 'hbase', 'regionserver')
        except UnboundLocalError as err:
            errmsg = "BDM-HB-00: Looks like we don't have an active HMaster, unable to get regionservers"
            self._lgr.error(errmsg)
            self._lgr.error("%s", err)
            self.mtrx['error'] += 1
            raise BDMonException(errmsg)

    def get_metrics_hive(self):
        """Function to process HIVE jmx data"""
        hive = gethivedetails(self._lgr)
        self._proto = hive["proto"]
        self._uripath = hive["uripath"]
        hs2nodes = hive["hs2"].replace(' ', '').split(',')
        self._lgr.debug("Received HIVE config info:%s", hive)
        rcmp = re.compile(r"Count|Valid|Value") # ignore these metricnames
        for node in hs2nodes:
            try:
                jdata = self._get_metrics(node)
                self._host = node.split(':')[0]
            except BDMonException as err:
                self._lgr.warning("Unable to get HS2 metrics, ignoring Node:%s", node)
                self._lgr.warning("Received HS2 error:%s", err)
                self.mtrx['warning'] += 1
                continue
            insvals = []
            cltime = datetime.now()
            for mtrx in jdata["beans"]:
                mtype = mtrx["modelerType"]
                mname = mtrx["name"]
                self._lgr.debug("HS2:%s ; Check metrics:%s - %s", self._host, mtype, mname)
                #self._appmtrx: Dict {appname:{appcomponent:[(modelertype1, mtypename1),...]}}
                ylst = [mtype.startswith(mx[0]) for mx in self._appmtrx['hive']['hs2']]
                if any(ylst):
                    self._lgr.info("HS2:%s ; Process metrics:%s - %s", self._host, mtype, mname)
                    if mtype == "sun.management.OperatingSystemImpl":
                        self._ins_osdata(mtrx, 'hive', 'hs2', cltime)
                    else:
                        #Get the index of the mtype(True) value
                        yindx = list(itertools.compress(range(len(ylst)), ylst))
                        self._lgr.debug("Found mType index: %s", yindx)
                        # For the mtype index (should be only one), check if mname is not null
                        # Or, if mname starts with the modelerName
                        melem = self._appmtrx['hive']['hs2'][yindx[0]]
                        self._lgr.debug("mType, mName: %s", melem)
                        if not melem[1] or mname.startswith(melem[1]):
                            self._lgr.info("HS2: About to insert:%s", mtype)
                            #hs2node, modelerType, metricname, numvalue, collection_ts
                            #metricname is combination of modelerName + MetricName
                            #e.g.java.lang:type=GarbageCollector,name=G1 Young Generation
                            # and CollectionCount becomes "G1YoungGeneration-CollectionCount"
                            #Also replace $ from modelerType, $ can cause problems in reporting
                            insvals.append([(self._host, mtype.replace('$', ''),
                                             str.rstrip(mname.split('=')[-1].replace(' ', '') + \
                                              '-' + rcmp.sub('', key), '-'), val, cltime) \
                                            for key, val in mtrx.items()
                                            if hasattr(val, 'real') and not isnan(val)])
            self._dbo.stmt = self._dbo_stmts["hive_hs2"]
            #Expand the list of lists to list of insert values
            self._dbo.values = list(itertools.chain(*insvals))
            self._bulk_insdb()

    def get_metrics_spark(self):
        """Function to process spark json metrics data"""
        sprk = getsparkdetails(self._lgr)
        self._proto = sprk["proto"]
        self._uripath = sprk["uripath"] + '/applications'
        shsnodes = sprk["histsrvr"].replace(' ', '').split(',')
        self._lgr.debug("Received spark config info:%s", sprk)
        for node in shsnodes:
            self._host = node.split(':')[0]
            #First, get the last run timestamp
            #Get the list of applications since last run
            self._dbo.stmt = ('select start_ts_str from t_spark_apps a, '
                              '(select max(start_ts) as mxts from t_spark_apps where shshost=?) b '
                              'where a.start_ts=b.mxts and a.shshost=?')
            self._dbo.values = (self._host, self._host)
            self._dbo.execstmt()
            last_ts = self._dbo.crsr.fetchone()
            if last_ts:
                self._lgr.info("Collect Spark metrics after:%s", last_ts[0])
                self._uripath += '?minDate=' + last_ts[0]
            elif sprk["mtrxdate"]:
                self._lgr.info("From config-Collect Spark metrics after:%s", sprk["mtrxdate"])
                self._uripath += '?minDate=' + sprk["mtrxdate"]
            try:
                jadata = self._get_metrics(node)
            except BDMonException as err:
                self._lgr.warning("Unable to get Spark History Server metrics, Node:%s", node)
                self._lgr.warning("Received Spark History Server error:%s", err)
                self.mtrx['warning'] += 1
                continue
            for app in jadata: # each element in json response is an application
                self._dbo.stmt = self._dbo_stmts["spark_app"]
                appid = app["id"]
                self._lgr.info("Spark App:%s", appid)
                attempt = app["attempts"][0]
                #shshost, app_id, appname, start_ts, start_ts_str,sparkuser, time_taken
                self._dbo.values = [(self._host, appid, app["name"], attempt["startTime"],
                                     attempt["startTime"], attempt["sparkUser"],
                                     attempt["duration"])]
                try:
                    self._dbo.execstmt()
                except BDMonException as err:
                    if "duplicate key value" in str(err):
                        #application information has already been captured
                        self._lgr.warning("Spark App already captured:%s", appid)
                        self.mtrx['warning'] += 1
                    else:
                        self._lgr.error("DB error on Spark App:%s", appid)
                        self.mtrx['error'] += 1
                else:
                    #For each application gather the executor metrics
                    try:
                        self._uripath = sprk["uripath"] + '/applications/' + appid + '/executors'
                        jedata = self._get_metrics(node)
                    except BDMonException as err:
                        self._lgr.warning("Unable to get executor metrics for:%s", self._uripath)
                        self._lgr.warning("Received node error:%s", err)
                        self.mtrx['warning'] += 1
                    else:
                        emtrx = jedata[0]
                        sprkhost = emtrx["hostPort"].split(":")[0] # ignore the port
                        exectime = emtrx["addTime"]
                        #app_id, sprkhost, metricname, numvalue, execution_ts
                        self._dbo.values = [(appid, sprkhost, key, val, exectime) \
                                            for key, val in \
                                            itertools.chain(emtrx.items(),
                                                            emtrx["memoryMetrics"].items())
                                            if hasattr(val, 'real') and not isnan(val)]
                        self._dbo.stmt = self._dbo_stmts["spark_exec"]
                        self._bulk_insdb()
                    #For each application gather the stage metrics
                    try:
                        self._uripath = sprk["uripath"] + '/applications/' + appid + '/stages'
                        jsdata = self._get_metrics(node)
                    except BDMonException as err:
                        self._lgr.warning("Unable to get Stage metrics for:%s", self._uripath)
                        self._lgr.warning("Received node error:%s", err)
                        self.mtrx['warning'] += 1
                    else:
                        for stg in jsdata:
                            #app_id, stageid, metricname, numvalue, launch_ts
                            try:
                                sst = stg["submissionTime"]
                            except KeyError:
                                self._lgr.info("Stage Status: SKIPPED, stageid:%s", stg["stageId"])
                            else:
                                self._dbo.values = [(appid, stg["stageId"], key, val, sst) \
                                                    for key, val in stg.items()
                                                    if hasattr(val, 'real') and not isnan(val) and \
                                                       key not in ('stageId', 'attemptId')]
                                self._dbo.stmt = self._dbo_stmts["spark_stgs"]
                                self._bulk_insdb()

    def get_metrics_yarn(self):
        """Function to process YARN active/standby jmx data"""
        ## Get the resourcemanager nodes, uri protocol, uri_path
        yarn = getyarndetails(self._lgr)
        self._proto = yarn["proto"]
        self._uripath = yarn["uripath"]
        rmnodes = yarn["rm"].replace(' ', '').split(',')
        self._lgr.debug("Received yarn config info:%s", yarn)
        for node in rmnodes:
            try:
                jdata = self._get_metrics(node)
                self._host = node.split(':')[0]
            except BDMonException as err:
                self._lgr.warning("Unable to get RM metrics, ignoring Node:%s", node)
                self._lgr.warning("Received node error:%s", err)
                self.mtrx['warning'] += 1
                continue
            cltime = datetime.now()
            for mtrx in jdata["beans"]:
                if mtrx.get("LiveNodeManagers", "{}") != "{}":
                    self._lgr.info("Getting nodemanagers list")
                    if yarn["nmnodes"]: #restricted NM list
                        rmnodes = yarn["nmnodes"].replace(' ', '').split(',')
                        self._lgr.info("Restricted RMNodes: %s, Total:%s", rmnodes, len(rmnodes))
                    else: #Get the list of all rmnodes
                        lnodes = ujson.loads(mtrx["LiveNodeManagers"])
                        self._lgr.info("Total RMNodes to process: %s", len(lnodes))
                        rmnodes = [rmn["NodeHTTPAddress"] for rmn in lnodes]
                    break
            for mtrx in jdata["beans"]:
                mtype = mtrx["modelerType"]
                self._lgr.debug("RMNode:%s ; Check metrics:%s", self._host, mtype)
                #self._appmtrx: Dict {appname:{appcomponent:[(modelertype1, mtypename1),...]}}
                if [mx for mx in self._appmtrx['yarn']['rm'] if mtype.startswith(mx[0])]:
                    self._lgr.info("RMNode:%s ; Process metrics:%s", self._host, mtype)
                    if mtype == "sun.management.OperatingSystemImpl":
                        self._ins_osdata(mtrx, 'yarn', 'rm', cltime)
                    else:
                        self._dbo.values = [(self._host, mtype, key, val, cltime) \
                                            for key, val in mtrx.items()
                                            if hasattr(val, 'real') and not isnan(val)]
                        self._dbo.stmt = self._dbo_stmts["yarn_rm"]
                        self._bulk_insdb()
            #Yarn RMs can be in Active-StandBy mode,
            #An active node is processed, skip the standby node, because it will point to active
            break
        #RMnodes complete, now process NMnodes
        try:
            self._lgr.info("NMnodes list: %s", rmnodes)
            self._get_metrics_workers(rmnodes, yarn["nmport"], 'yarn', 'nm')
        except UnboundLocalError as err:
            errmsg = "BDM-YN-00: Looks like we don't have an active ResourceManager"
            self._lgr.error(errmsg)
            self._lgr.error("%s", err)
            self.mtrx['error'] += 1
            raise BDMonException(errmsg)

    def get_metrics_zookeeper(self):
        """Function to process zookeeper quorum metrics"""
        zkq = getzkdetails(self._lgr)
        #e.g. namenode:2181,snode:2181,datanode1:2181
        zknodes = zkq.replace(' ', '').split(',')
        errmsg = ''
        for node in zknodes:
            self._host, port = node.split(':')
            try:
                conn = _SocketConn(self._lgr, self._host, int(port))
                # Using a context manager to work with sockets
                with conn as zks:
                    msgs = []
                    snt = zks.send(str.encode('stat'))
                    #Sent message length should match
                    if snt != 4:
                        errmsg = 'BDM-SK-03: Cannot send stat to ZK node %s:%s' %(self._host, port)
                        self._lgr.error(errmsg)
                        self.mtrx['error'] += 1
                        raise BDMonException(errmsg)
                    while True:
                        resp = zks.recv(4096)
                        if resp:
                            msg = resp.decode()
                            self._lgr.debug('ZK data: %s', msg)
                            msgs.append(msg)
                        else:
                            break
            except (socket.gaierror, ValueError, socket.error, BDMonException) as err:
                errmsg = 'BDM-SK-00: Connection error to ZK node %s:%s' %(self._host, port)
                self._lgr.warning(errmsg)
                self._lgr.warning("Unable to get zookeeper metrics, Node:%s", node)
                self._lgr.warning("Received ZK Server error:%s", err)
                self.mtrx['warning'] += 1
            else:
                if msgs:
                    cltime = datetime.now()
                    resp = ''.join(msgs)
                    self._lgr.info('Response Length:%s', len(resp))
                    zk_mtrx = []
                    zk_mode = resp.split('\nMode: ')[1][0]  #l-leader, f-follower, s-standalone
                    for stat in resp.split('\n'):
                        self._lgr.debug('ZK status item:%s', stat)
                        zkrow = stat.split(':')
                        if stat.startswith('Latency'):
                            # e.g. Latency min/avg/max: 0/0/16
                            for ltype, lval in zip(zkrow[0].strip('Latency ').split('/'),
                                                   zkrow[1].strip().split('/')):
                                #hostnode, zk_mode, metricname, numvalue, collection_ts
                                try:
                                    zk_mtrx.append((self._host, zk_mode, ltype + '_latency',
                                                    float(lval), cltime))
                                except ValueError:
                                    self._lgr.warning('Ignore zk Latency key %s', ltype)
                                    self.mtrx['warning'] += 1
                        elif "](queued=" in stat:
                            self._lgr.info('ZK client: %s', stat)
                            #e.g. /x.x.x.x:xxxx[0](queued=0,recved=1,sent=0)
                            clnt_host = stat.split(':')[0].replace('/', '')
                            clnt_mtrx = []
                            for clval in stat.split('](')[1].replace(')', '').split(','):
                                mname, nval = clval.split('=')
                                self._lgr.info('ZK client mname:%s, val=%s', mname, nval)
                                #zk_hostnode, client_hostnode, metricname, numvalue, collection_ts
                                try:
                                    clnt_mtrx.append((self._host, clnt_host, mname,
                                                      float(nval), cltime))
                                except ValueError:
                                    self._lgr.warning('Ignore zk client %s', clval)
                                    self.mtrx['warning'] += 1
                            self._dbo.values = clnt_mtrx
                            self._dbo.stmt = self._dbo_stmts["zk_conn_mtrx"]
                            self._bulk_insdb()
                        elif len(zkrow) == 2 and zkrow[0] and zkrow[1]:
                            self._lgr.info('ZK Key: %s ; Val:%s', zkrow[0], zkrow[1])
                            #hostnode, zk_mode, metricname, numvalue, collection_ts
                            try:
                                zk_mtrx.append((self._host, zk_mode, zkrow[0],
                                                float(zkrow[1]), cltime))
                            except ValueError:
                                self._lgr.warning('Ignore zk key %s', zkrow[0])
                                self.mtrx['warning'] += 1
                    self._dbo.values = zk_mtrx
                    self._dbo.stmt = self._dbo_stmts["zk_mtrx"]
                    self._bulk_insdb()
                else:  #We received no response from ZK server within the timeout period
                    errmsg = 'BDM-SK-05: No response from ZK node %s:%s' %(self._host, port)
                    self._lgr.warning(errmsg)
                    self._lgr.warning("Unable to get zookeeper metrics, Node:%s", node)
                    self.mtrx['warning'] += 1
        if errmsg: # there were errors when capturing ZK metrics on one or more nodes
            raise BDMonException(errmsg)

    def _get_metrics(self, app_host_port):
        """ GET JMX data from URIs"""
        app_uri = self._proto + "://" + app_host_port + self._uripath
        self._lgr.info('Invoking:%s', app_uri)
        try:
            res = requests.get(app_uri, timeout=1.0)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as err:
            errmsg = 'BDM-URI-00: Connection error to metrics URI:%s' %app_uri
            self._lgr.error(errmsg)
            self._lgr.error(err)
            self.mtrx['error'] += 1
            raise BDMonException(err)
        if res.status_code == 200:
            try:
                dct = res.json()
            except ValueError as err:
                errmsg = 'BDM-URI-03: FAILED to get a valid json response'
                self._lgr.error(errmsg)
                self._lgr.error(err)
                self.mtrx['error'] += 1
                raise BDMonException(err)
            self._lgr.debug('GET results:%s' %dct)
        else:
            errmsg = 'BDM-URI-05: Application metrics collection error %s'  %res.status_code
            self._lgr.error(errmsg)
            self.mtrx['error'] += 1
            raise BDMonException(errmsg)
        return dct


def _process_metrics(lgr, applst):
    """Function to process BD metrics data"""
    # Get the list of applications, components and metrics to collect
    dct = {}
    for app in applst:
        dct[app] = {}
    lgr.info("List of applications initialized: %s", dct)
    try:
        dbo = DbOps(lgr)
        lgr.info('DB Connection ready')
    except BDMonException as err:
        errmsg = 'BDM-PM-00: Unable to create database connection'
        lgr.error(errmsg)
        lgr.error(err)
        raise BDMonException(err)
    dbo.stmt = "select appname, appcomponent, modelertype, mtypename from t_coll_metrics where \
                appname in (" + ",".join(("'" + x + "'" for x in applst)) + ") and is_active='Y'"
    dbo.execstmt()
    for row in dbo.crsr.fetchall():
        try:
            #(appname,appcomponent,modelertype, row.mtypename)
            dct[row[0]][row[1]].append((row[2], row[3]))
        except KeyError:
            dct[row[0]].setdefault(row[1], [(row[2], row[3]), ])

    dbo.stmt = ''
    lgr.info("List of application metrics to collect confirmed")
    lgr.debug("List of application metrics: %s", dct)
    appstime = datetime.now()
    lgr.info('Start processing of apps at %s ', appstime)
    #Invoke the processing method for each of the app
    getmtrx = _BDMProcess(lgr, dbo, dct)
    for app in applst:
        stime = datetime.now()
        lgr.info('Start App processing: %s at %s', app, stime)
        try:
            fnc = 'get_metrics_' + app
            getattr(getmtrx, fnc)()
        except AttributeError as err:
            errmsg = 'BDM-APP-01: Invalid application name: %s ; Check config' %app
            lgr.error(errmsg)
            lgr.error(err)
            getmtrx.mtrx['error'] += 1
        except BDMonException as err:
            dbo.rollback()
            lgr.error('BDM-APP-03: Error while processing application: %s', app)
        etime = datetime.now()
        getmtrx.mtrx[app + "CollectionTime"] = (etime - stime).total_seconds()
        lgr.info('End App processing: %s at %s; Total time:%s', app, etime, etime - stime)
    #BDMonhost, metricname, numvalue, collection_ts
    getmtrx.mtrx["totalCollectionTime"] = (etime - appstime).total_seconds()
    lgr.info('Total processing:- Begin time: %s; End time:%s; Total time:%s',
             appstime, etime, getmtrx.mtrx["totalCollectionTime"])
    dbo.values = [(os.uname()[1], key, val, etime) \
                    for key, val in getmtrx.mtrx.items()]
    dbo.stmt = ('insert into t_bdmon_metrics '
                '(bdmonhost, metricname, numvalue, collection_ts) '
                'values(?, ?, ?, ?)')
    dbo.execstmt()
    dbo.commitclose()

def get_appmetrics(applst='', logidentifier='', logmode=30):
    """ Get application metrics, parse and store in DB
    Parameters
    -----------
    applst : tuple or list
        List of applications to capture metrics (default: ALL applications defined in config file)
    logidentifier : Unique log file name during multi process launch (default: '')
    logmode : str: DEBUG, INFO, WARNING, ERROR, CRITICAL (default: INFO)

    Raises
    -------
    BDMonException : Exception

    Returns
    -------
    Exit code : integer
        0: Metrics collected successfully
        1: Error when processing

    Usage
    -------
    To capture metrics for all apps specified in config file
        e.g. get_appmetrics()
    To capture metrics for specific app(s) invoke
        e.g. get_appmetrics(('hdfs',)) get_appmetrics(('hdfs', 'hive'))
    To change the loglevel to info
        e.g get_appmetrics('', '', 'INFO')
    To change the logfile name and loglevel to debug
        e.g. get_appmetrics('', 'hdfs', 'DEBUG')
        logfilename will be of the form <DEFAULTLOGFILE>_hdfs.log
    """

    if logmode not in ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'):
        logmode = 'INFO'
    lgr = getlgr(logmode, str(logidentifier))  #In case numeric identifiers are specified
    if not applst:
        try:
            applst = getbdapplst(lgr)
        except BDMonException as err:
            errmsg = 'BDM-MN-00: Unable to list of applications'
            lgr.error(errmsg)
            lgr.error(err)
            sys.exit(1)
    elif isinstance(applst, (list, tuple)):
        lgr.info('Begin: App list: %s', applst)
    else:
        errmsg = 'BDM-MN-01: Application list expected. Received: %s type' %type(applst).__name__
        lgr.error(errmsg)
        sys.exit(1)

    try:
        _process_metrics(lgr, applst)
    except BDMonException as err:
        errmsg = 'BDM-MN-03: Unable to extract and process metrics data'
        lgr.error(errmsg)
        lgr.error(err)
        sys.exit(1)
    sys.exit(0)
