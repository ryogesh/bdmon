#!/bin/bash

# Copyright (c) 2018  Yogesh Rajashekharaiah 
# All Rights Reserved

check_stat()
{
    if [ `echo $?` -ne 0 ]
    then
        echo "Failed to $1 .. exiting now"
        exit 127
    fi
}

cd ~
read -p "Type python3 binary name e.g. python3 or python3.6 : " pyname
echo ""
echo "Verifying python3 availability"

Z1=`grep "debian" /etc/os-release`
which $pyname &>/dev/null
if [ `echo $?` -ne 0 ]
then
    echo "python3 doesn't exist, exiting...."
    echo ""
    exit 1
fi

echo "******Installing libraries******"
if [ "X" == "X"$Z1 ]
then
    sudo yum -y install epel-release
    #sudo yum -y groupinstall "Development Tools"
    sudo yum -y install gcc gcc-c++ kernel-devel
    pyver="`$pyname --version |cut -d ' ' -f 2 | cut -d '.' -f 2`"
    sudo yum -y install python3${pyver}-devel unixODBC-devel.x86_64 unzip openssl-devel.x86_64 libffi-devel.x86_64 python3${pyver}-pip
else
    sudo apt -y install build-essential unixodbc-dev unzip libssl-dev libffi-dev python3-dev python3-pip
fi
check_stat "Install python3-pip, odbc libraries"

echo ""
read -p  "Will you be using postgresql, mysql or mssql server (y/n)?" dbyn
if [ "X"$dbyn == "Xy" ]
then
    echo "Script can install postgres DB and required packages"
    read -p "Install postgresql DB(y/n)? " yn
    echo ""
    read -p "Install postgresql ODBC driver(y/n)? " dyn
    echo ""

    if [ "X"$yn == "Xy" ]
    then
        echo "******Installing postgresql DB******"
        if [ "X" == "X"$Z1 ]
        then
            sudo rpm -Uvh https://yum.postgresql.org/11/redhat/rhel-7-x86_64/pgdg-centos11-11-2.noarch.rpm
            sudo yum -y install postgresql11-server
        else
            sudo echo "deb http://apt.postgresql.org/pub/repos/apt/ $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list
            sudo apt-get update
            sudo apt-get install postgresql-11 
        fi
        check_stat "Install postgresDB"
        echo "Make sure to configure the postgresql DB"
    fi

    if [ "X"$dyn == "Xy" ]
    then
        echo "******Installing postgresql ODBC driver******"
        if [ "X" == "X"$Z1 ]
        then
            sudo yum -y install postgresql11-odbc.x86_64
            sudo ln -s /usr/pgsql-11/lib/psqlodbcw.so /usr/lib64/psqlodbcw.so
        else
            sudo apt -y install odbc-postgresql
        fi
        check_stat "Install postgresDB ODBC driver"
    fi
else   
    echo "BDMon will use a local sqlite engine"
    echo "**NOT** recommended for high volume or multi connection environment"
    echo ""
fi

echo "******Installing python3 modules******"
sudo $pyname -m pip install --upgrade pip  
$pyname -m pip install ujson pyodbc urllib3[secure] requests cryptography --user
check_stat "Install python3 modules"

echo ""
echo "Script can install grafana"
read -p "Install grafana(y/n)? " yn
echo ""

if [ "X"$yn == "Xy" ]
then
    echo "******Installing grafana******"
    if [ "X" == "X"$Z1 ]
    then
        sudo yum -y install https://dl.grafana.com/oss/release/grafana-6.2.1-1.x86_64.rpm
        sudo yum -y install initscripts fontconfig
    else
        sudo apt-get update
        sudo apt-get -y install grafana
    fi
    check_stat "Install grafana"
    sudo systemctl enable grafana-server.service
    echo "Make sure to configure grafana to the BDMON DB"
fi
