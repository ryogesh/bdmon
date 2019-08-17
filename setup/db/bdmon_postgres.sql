-- Master table with application definitions and the metrics to be collected
CREATE TABLE t_coll_metrics
(
  id serial NOT NULL,
  appname   varchar(16),
  appcomponent varchar(16),
  modelerType  varchar(64),
  mtypename  varchar(64),
  is_active char(1) default 'N',
  CONSTRAINT t_coll_metrics_pkey PRIMARY KEY (id),
  CONSTRAINT cons_coll_metrics_uniq UNIQUE(appname, appcomponent, modelerType, mtypename)
);


CREATE TABLE t_node_metrics
(
  id serial NOT NULL,
  hostnode varchar(64),
  appname   varchar(16),
  appcomponent varchar(16),
  metricname varchar(64),
  numvalue    float,
  collection_ts timestamp without time zone,
  CONSTRAINT t_host_app_pkey PRIMARY KEY (id)
);
Create index ind_node_ts_hn on t_node_metrics(collection_ts, hostnode);
Create index ind_node_anc_mt on t_node_metrics(appname, appcomponent);

CREATE TABLE t_hdfs_nn_metrics
(
  id serial NOT NULL,
  namenode varchar(64),
  is_active    char(1) default 'N',
  modelerType varchar(64),
  metricname varchar(64),
  numvalue    float,
  collection_ts timestamp without time zone,
  CONSTRAINT t_hdfs_nn_pkey PRIMARY KEY (id)
);
Create index ind_t_hdfs_nn_ts on t_hdfs_nn_metrics(collection_ts);
Create index ind_t_hdfs_mt_ts on t_hdfs_nn_metrics(modelerType);

CREATE TABLE t_hdfs_dn_metrics
(
  id serial NOT NULL,
  datanode varchar(64),
  modelerType varchar(64),
  metricname varchar(64),
  numvalue    float,
  collection_ts timestamp without time zone,
  CONSTRAINT t_hdfs_dn_pkey PRIMARY KEY (id)
);
Create index ind_hdfs_dn_ts on t_hdfs_dn_metrics(collection_ts);
Create index ind_hdfs_mt_ts on t_hdfs_dn_metrics(modelerType);

CREATE TABLE t_yarn_rm_metrics
(
  id serial NOT NULL,
  rmnode varchar(64),
  modelerType varchar(64),
  metricname varchar(64),
  numvalue    float,
  collection_ts timestamp without time zone,
  CONSTRAINT t_yarn_rm_pkey PRIMARY KEY (id)
);
Create index ind_t_yarn_rm_ts on t_yarn_rm_metrics(collection_ts);
Create index ind_t_yarn_mt_ts on t_yarn_rm_metrics(modelerType);

CREATE TABLE t_yarn_nm_metrics
(
  id serial NOT NULL,
  nmnode varchar(64),
  modelerType varchar(64),
  metricname varchar(64),
  numvalue    float,
  collection_ts timestamp without time zone,
  CONSTRAINT t_yarn_nm_pkey PRIMARY KEY (id)
);
Create index ind_yarn_nm_ts on t_yarn_nm_metrics(collection_ts);
Create index ind_yarn_mt_ts on t_yarn_nm_metrics(modelerType);

CREATE TABLE t_hmaster_metrics
(
  id serial NOT NULL,
  masternode varchar(64),
  is_active    char(1) default 'N',
  modelerType varchar(64),
  metricname varchar(64),
  numvalue    float,
  collection_ts timestamp without time zone,
  CONSTRAINT t_hmaster_pkey PRIMARY KEY (id)
);
Create index ind_hmaster_ts on t_hmaster_metrics(collection_ts);
Create index ind_hmaster_mt on t_hmaster_metrics(modelerType);

CREATE TABLE t_hbase_rs_metrics
(
  id serial NOT NULL,
  rsnode varchar(64),
  modelerType varchar(64),
  metricname varchar(64),
  numvalue    float,
  collection_ts timestamp without time zone,
  CONSTRAINT t_hbase_rs_pkey PRIMARY KEY (id)
);
Create index ind_hbase_rs_ts on t_hbase_rs_metrics(collection_ts);
Create index ind_hbase_rs_mt on t_hbase_rs_metrics(modelerType);

CREATE TABLE t_hbase_tbl_metrics
(
  id serial NOT NULL,
  namespace varchar(64),
  tblname   varchar(64),
  regionid   varchar(64),
  metricname varchar(64),
  numvalue    float,
  collection_ts timestamp without time zone,
  CONSTRAINT t_hbase_tbl_pkey PRIMARY KEY (id)
);
Create index ind_hbase_tbl_tbl_mn on t_hbase_tbl_metrics(tblname, metricname);
Create index ind_hbase_tbl_tbl_ts on t_hbase_tbl_metrics(collection_ts);

CREATE TABLE t_hive_metrics
(
  id serial NOT NULL,
  hs2node varchar(64),
  modelerType varchar(64),
  metricname varchar(128),
  numvalue    float,
  collection_ts timestamp without time zone,
  CONSTRAINT t_hive_pkey PRIMARY KEY (id)
);
Create index ind_hive_ts on t_hive_metrics(collection_ts);
Create index ind_hive_mt on t_hive_metrics(modelerType);

CREATE TABLE t_zk_conn_metrics
(
  id serial NOT NULL,
  zknode varchar(64),
  client_hostnode varchar(64),
  metricname varchar(64),
  numvalue    float,
  collection_ts timestamp without time zone,
  CONSTRAINT t_zk_conn_pkey PRIMARY KEY (id)
);
Create index ind_zk_conn_ts on t_zk_conn_metrics(collection_ts);
Create index ind_zk_conn_ts_hn on t_zk_conn_metrics(collection_ts, zknode);

CREATE TABLE t_zk_metrics
(
  id serial NOT NULL,
  zknode varchar(64),
  zk_mode char(1) default 's',
  metricname varchar(64),
  numvalue    float,
  collection_ts timestamp without time zone,
  CONSTRAINT t_zk_pkey PRIMARY KEY (id)
);
Create index ind_zk_hst_mn on t_zk_metrics(zknode, metricname);
Create index ind_zk_ts on t_zk_metrics(collection_ts);

Create table t_spark_apps
(
  id serial NOT NULL,
  shshost varchar(64),
  app_id varchar(64),
  appname varchar(64),
  start_ts timestamp without time zone,
  sparkuser varchar(64),
  start_ts_str varchar(64),
  time_taken float,
  CONSTRAINT t_sprk_app_pkey PRIMARY KEY (id),
  CONSTRAINT cons_spark_apps_uniq UNIQUE(app_id)
);
Create index ind_sprk_app_ts on t_spark_apps(start_ts);


Create table t_spark_executors
(
  id serial NOT NULL,
  app_id varchar(64),
  sprkhost varchar(64),
  metricname varchar(64),
  numvalue    float, 
  execution_ts timestamp without time zone,
  CONSTRAINT t_sprk_exec_pkey PRIMARY KEY (id)
);
Create index ind_sprk_exec_ts on t_spark_executors(execution_ts);

Create table t_spark_stages
(
  id serial NOT NULL,
  app_id varchar(64),
  stageid integer,
  metricname varchar(64),
  numvalue    float, 
  launch_ts timestamp without time zone,
  CONSTRAINT t_sprk_stg_pkey PRIMARY KEY (id)
);
Create index ind_sprk_stg_ts on t_spark_stages(launch_ts);

Create table t_bdmon_metrics
(
  id serial NOT NULL,
  bdmonhost varchar(64),
  metricname varchar(64),
  numvalue    float, 
  collection_ts timestamp without time zone,
  CONSTRAINT t_bdmon_pkey PRIMARY KEY (id)
);
Create index ind_bdmon_ts on t_bdmon_metrics(collection_ts);
