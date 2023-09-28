# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example configuration for ORACLE plugin for Windows
# Set the ORACLE_HOME if we have more than one oracle home on the server
# then we can generate the PATH based on that. Note that the tnsnames.ora
# must then be in %ORACLE_HOME%\network\admin, or use the the environment
# variable %TBS_ADMIN% to set to another directory.
# $ORACLE_HOME="C:\oracle\product\12.1.0.1"

# $DBUSER=@("sys", "Secret12", "SYSDBA", "localhost", "1521")
# $DBUSER_tst=@("sys", "Secret12", "SYSDBA", "localhost", "1521")
# $DBUSER_orcl=@("sys", "Secret12", "SYSDBA", "localhost", "1521")
# $DBUSER_orcl=@("sys", "Secret12", "SYSDBA", "localhost", "1521")
# $ASMUSER=@("user", "password", "SYSDBA/SYSASM", "hostname", "port")

