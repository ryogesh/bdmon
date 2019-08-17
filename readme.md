
# Big Data Monitoring Tool
## Overview

Big Data Monitoring(bdmon) tool can be used to capture and monitor various metrics across Big Data services. bdmon supports capturing metrics of the following Big Data services
- HDFS
- YARN
- HIVE
- SPARK
- HBase
- ZooKeeper

bdmon comes with grafana dashboards to monitor the above services and can be easily customized to your needs.

## Tool Features
- Capture metrics using the jmx web services of the big data services
- Capture metrics from many clusters (e.g. for comparison)
- Capture metrics from nodes
- Capture metrics for all services
- Capture metrics for a specific service
- Capture metrics for a specific service and a node
- Default grafana dashboards


## Installation
### Check prerequisites

- A Linux/Unix based system
- [Python](https://www.python.org/downloads/) 3.5 or greater

### Supported Database

- [PostgreSQL](https://www.postgresql.org/) (Recommended)
- [MySQL](https://www.mysql.com/)
- [SQL Server](https://www.microsoft.com/en-us/sql-server/sql-server-2016)
- [SQLite](https://sqlite.org/index.html) (default)

Note: 
Setup script can install PostgreSQL database and driver only, but you will need to configure the database. 
To configure for MySQL or SQL Server, refer [pyodbc](https://github.com/mkleehammer/pyodbc/wiki) documentation.

### Libraries required
unixodbc-dev, unzip, libssl-dev, libffi-dev, python3-dev, python3-pip

### Python modules required
ujson, pyodbc, urllib3[secure], requests, cryptography

If the above libraries and packages are not available on the server they can be installed by running the setup/setup-bdmon-app.sh script. See "Setup and configure application" section below.

## Getting Started
bdmon is a pure python module, requires no installation if the requirements are met. If the libraries and python modules are not installed on the server, run the script setup/setup-bdmon-app.sh

### Setup and configure application
- Download the zip file
- unzip the file
- (optional) run the setup script, setup/setup-bdmon-app.sh
- run application configuration script, setup/updatecfg.py

Before running the scripts, it's HIGHLY recommended that you review the script and configuration files. File comments provide information on the setup and on how to configure to capture metrics for a given service.
 - bdmon/setup/setup-bdmon-app.sh
 - bdmon/setup/updatecfg.py
 - bdmon/config/bdmon.ini

    ```
    cd /opt; unzip bdmon.zip  #Make sure you have rw permissions on the folder
    cd bdmon/setup; /bin/bash ./setup-bdmon-app.sh  #Optional
    python3 updatecfg.py
    ```

Note: 
- If the default SQLite database is choosen, skip the next "Configure database" section
- SQLite database is **NOT** suitable for capturing large metrics and for parallel execution

### Configure database
Note: Database configuration is REQUIRED, if the database is not SQLite

Prepare the database.

    ```
    cd /opt/bdmon/setup/db
    # Step1: Execute the appropriate create table script against the database
    # e.g. bdmon_postgres.sql against the PostgreSQL database
    
    # Step2: Execute the bdmon_inserts.sql against the database
    # DO REVIEW the insert script
    # Only the metrics set as is_active == 'Y' will be captured,  make changes as required
    # Default setup works for most cases
    ```

### Automation
If you are planning to automate deployment and configuration using scripts, the bdmon configuration script supports environment variables. If the environment variables are set, the script updatecfg.py will run configuration without user prompts. Review the script bdmon/setup/updatecfg.py for the environment variables.

### Test 
Run the test script to verify the deployment and database configuration

    ```
    cd /opt/bdmon/test/unit
    python3 test_bdmon_db.py
    ```

## Capture Big Data service metrics
    Usage
    -------
    To capture metrics for all apps specified in config file
        e.g. get_appmetrics()
    To capture metrics for specific app(s) invoke
        e.g. get_appmetrics(('hdfs',)) or  get_appmetrics(('hdfs', 'hive'))
    To change the loglevel to info and capture metrics for all services defined in config file
        e.g get_appmetrics('', '', 'INFO')
    To change the logfile name and loglevel to debug
        e.g. get_appmetrics('', 'all', 'DEBUG')
        logfilename will be of the form <DEFAULTLOGFILE>_all.log
        
For example:

    ```
    # Capture spark metrics only, with default log file name and INFO level
    cd /opt/bdmon; python3 -c  'from bdutils.bdengine import get_appmetrics;  get_appmetrics(("spark",), "", 20)'
    
    # Capture hdfs metrics in debug mode and specify file name
    cd /opt/bdmon; python3 -c  'from bdutils.bdengine import get_appmetrics;  get_appmetrics(("hdfs",), "hdfs", "DEBUG")'
    
    # To capture metrics from all services on 2 clusters, copy the install folder (/opt/bdmon) to a separate folder(/opt/bdmon1)
    # Metrics from both clusters will be captured on the same database
    
    # To capture metrics in different database, on the new folder run the config script, i.e./opt/bdmon1/setup/updatecfg.py to specify the database connection
    # Then run the below commands
    cd /opt/bdmon; python3 -c  'from bdutils.bdengine import get_appmetrics;  get_appmetrics()'
    cd /opt/bdmon1; python3 -c  'from bdutils.bdengine import get_appmetrics;  get_appmetrics()'
    
    ```

To capture metrics periodically, run the commands using a scheduler e.g. cron
For example:

    ```
    # Capture hdfs and zookeeper metrics on a cluster at different intervals, 5 and 10mins
    # Create 2 scheduler jobs; service names are always in lower case e.g. hdfs 
    cd /opt/bdmon; python3 -c  'from bdutils.bdengine import get_appmetrics;  get_appmetrics(("hdfs",))'
    
    cd /opt/bdmon; python3 -c  'from bdutils.bdengine import get_appmetrics;  get_appmetrics(("zookeeper",))'
    
    ```

## Grafana dashboards
Import any of the available dashboards from bdmon/setup/dashboards folder and edit to your requirements e.g. hostnames

Refer [grafana](https://grafana.com/docs/installation/configuration/) documentation

## Monitoring bdmon
Monitor the log files generated by the application for errors and warnings,  in bdmon/logs directory. 

bdmon also logs performance summary to the table t_bdmon_metrics. grafana dashboard "Metrics Collection Server", provides the visualization, edit the host name to match your deployment.

