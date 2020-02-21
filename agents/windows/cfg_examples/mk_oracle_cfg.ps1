# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2020             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

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

