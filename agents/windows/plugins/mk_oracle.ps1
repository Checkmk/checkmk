$CMK_VERSION = "2.1.0b7"
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Checkmk agent plugin for monitoring ORACLE databases
# This plugin is a result of the common work of Thorsten Bruhns, Andrew Lacy
# and Mathias Kettner. Thorsten is responsible for the ORACLE
# stuff, Mathias for the shell hacking, Andrew for the powershell...


###############################################################################
# open issues
###############################################################################
# 1. error connection to instance, old async still shown is this ok?

###############################################################################
# usage
###############################################################################
# copy this file to C:\Program Files (x86)\check_mk\plugins
# copy the config file to C:\Program Files (x86)\check_mk\config
# cd C:\Program Files (x86)\check_mk
# check_mk_agent test
###############################################################################



#   .--Config--------------------------------------------------------------.
#   |                     ____             __ _                            |
#   |                    / ___|___  _ __  / _(_) __ _                      |
#   |                   | |   / _ \| '_ \| |_| |/ _` |                     |
#   |                   | |__| (_) | | | |  _| | (_| |                     |
#   |                    \____\___/|_| |_|_| |_|\__, |                     |
#   |                                           |___/                      |
#   +----------------------------------------------------------------------+
#   | The user can override and set variables in mk_oracle_cfg.ps1         |
#   '----------------------------------------------------------------------'

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


# what should happen when an error occurs? SilentlyContinue, Continue, Stop, and Inquire
# SilentlyContinue is currently required due to the check of EXCLUDE_$inst_name
# when the variable EXCLUDE_$inst_name is not defined. This is set at certain points in the code
$NORMAL_ACTION_PREFERENCE = "Stop"
$ErrorActionPreference = "Stop"
$run_async = $null


# Sections that run fast and are not run with caching
$SYNC_SECTIONS = @("instance", "sessions", "logswitches", "undostat", "recovery_area", "processes", "recovery_status", "longactivesessions", "dataguard_stats", "performance")

# Set debug to 1 to turn it on, set to zero to turn it off
# if debug is on, debug messages are shown on the screen
$DEBUG = 0

# Sections that are run in the background and at a larger interval.
# These sections take longer to run and are therefore run in the background
# Note: sections not listed in ASYNC_ASM_SECTIONS, SYNC_SECTIONS or
# ASYNC_SECTIONS will not be executed at all!
$ASYNC_SECTIONS = @("tablespaces", "rman", "jobs", "ts_quotas", "resumable", "locks")


# Note: _ASM_ sections are only executed when SID starts with '+'
#       sections not listed in ASYNC_ASM_SECTIONS, SYNC_SECTIONS or
#       ASYNC_SECTIONS will not be executed at all!
$ASYNC_ASM_SECTIONS = @("asm_diskgroup")

# Note: _ASM_ sections are only executed when SID starts with '+'
#       sections not listed in ASYNC_ASM_SECTIONS, SYNC_SECTIONS or
#       ASYNC_SECTIONS will not be executed at all!
$SYNC_ASM_SECTIONS = @("instance")

# Interval for running async checks (in seconds)
$CACHE_MAXAGE = 600

# You can specify a list of SIDs to monitor. Other databases will then be ignored.
# Those databases will only be handled, if they are found running, though!
#
#   $ONLY_SIDS=@("XE", "ORCL", "FOO", "BAR")
#
# It is possible to filter SIDS negatively. Just add the following to
# the mk_oracle_cfg.ps1 file:
#
#   $EXCLUDE_<sid>="ALL"
#
# Another option is to filter single checks for SIDS. Just add
# lines as follows to the mk_oracle_cfg.ps1 file. One section per
# line:
#
#   $EXCLUDE_<sid>="<section>"
#
# For example skip oracle_sessions and oracle_logswitches checks
# for the instance "mysid".
#
#   $EXCLUDE_mysid="sessions logswitches"
#

Function debug_echo {
     Param(
          [Parameter(Mandatory = $True, Position = 1)]
          [string]$error_message
     )
     # if debug=1 then output
     if ($DEBUG -gt 0) {
          $MYTIME = Get-Date -Format o
          echo "${MYTIME} DEBUG:${error_message}"
     }
}

# filename for timestamp
$MK_CONFDIR = $env:MK_CONFDIR

# Fallback if the (old) agent does not provide the MK_CONFDIR
if (!$MK_CONFDIR) {
     $MK_CONFDIR = "c:\Program Files (x86)\check_mk\config"
}

# directory for tempfiles
$MK_TEMPDIR = $env:MK_TEMPDIR

# Fallback if the (old) agent does not provide the MK_TEMPDIR
if (!$MK_TEMPDIR) {
     $MK_TEMPDIR = "C:\Program Files (x86)\check_mk\temp"
}


# Source the optional configuration file for this agent plugin
$CONFIG_FILE = "${MK_CONFDIR}\mk_oracle_cfg.ps1"
if (test-path -path "${CONFIG_FILE}" ) {
     debug_echo "${CONFIG_FILE} found, reading"
     . "${CONFIG_FILE}"
}
else {
     debug_echo "${CONFIG_FILE} not found"
}

# If sqlnet.ora or tnsnames.ora exist in MK_CONFDIR set it as %TNS_ADMIN%
if ((test-path -path "${MK_CONFDIR}\sqlnet.ora") -or (test-path -path "${MK_CONFDIR}\tnsnames.ora")) {
     $env:TNS_ADMIN = "${MK_CONFDIR}"
}
debug_echo "value of TNS_ADMIN = $env:TNS_ADMIN"

if ($ORACLE_HOME) {
     # if the ORACLE_HOME is set in the config file then we
     # set the environment variable %ORACLE_HOME% for the time this script is run
     $env:ORACLE_HOME = "$ORACLE_HOME"
     $env:PATH = "$ORACLE_HOME\bin;" + $env:PATH

     debug_echo "value of ORACLE_HOME = $env:ORACLE_HOME"
     debug_echo "value of PATH = $env:PATH"
}
# setting the output error language to be English
$env:NLS_LANG = "AMERICAN_AMERICA.AL32UTF8"

$ASYNC_PROC_PATH = "$MK_TEMPDIR\async_proc.txt"

#.
#   .--SQL Queries---------------------------------------------------------.
#   |        ____   ___  _        ___                  _                   |
#   |       / ___| / _ \| |      / _ \ _   _  ___ _ __(_) ___  ___         |
#   |       \___ \| | | | |     | | | | | | |/ _ \ '__| |/ _ \/ __|        |
#   |        ___) | |_| | |___  | |_| | |_| |  __/ |  | |  __/\__ \        |
#   |       |____/ \__\_\_____|  \__\_\\__,_|\___|_|  |_|\___||___/        |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | The following functions create SQL queries for ORACLE and output     |
#   | them to stdout. All queries output the database name or the instane  |
#   | name as first column.                                                |
#   '----------------------------------------------------------------------'


$SQL_START = @"
set pages 0 trimspool on feedback off lines 8000
set echo on

"@

# use this workaround to avoid the message that the "<" symbol is reserved for future use
$LESS_THAN = '<'


Function get_dbversion_database ($ORACLE_HOME) {
     # The output of this command contains -- among others -- the version
     $version_str = (Invoke-Expression $ORACLE_HOME'\bin\sqlplus.exe -v')
     debug_echo "xx $version_str xx"


     # The output string can have arbitrary content. We rely on the assumption that the first
     # three elements have always the same syntax, e.g.: SQL*Plus: Release 12.1.0.2.0
     # so we take the third element separated by a whitespace as the version number and remove
     # all dots resulting in: 121020
     (([string]$version_str).split(' '))[3] -replace '\D+', ''
}


function is_async_running {
     if (-not(Test-Path -path "$ASYNC_PROC_PATH")) {
          # no file, no running process
          return $false
     }

     $proc_pid = (Get-Content ${ASYNC_PROC_PATH})
     $proc = Get-Process -id $proc_pid -ErrorAction SilentlyContinue
     if ($proc) {
         return $true
     }
     # The process to the PID cannot be found, so remove also the proc file
     rm $ASYNC_PROC_PATH
     return $false
}

################################################################################
# Run any SQL against the Oracle database
################################################################################
Function sqlcall {
     Param(
          [Parameter(Mandatory = $True, Position = 1)]
          [string]$sql_message,

          [Parameter(Mandatory = $True, Position = 2)]
          [string]$sqltext,

          [Parameter(Mandatory = $True, Position = 3)]
          [int]$run_async,

          [Parameter(Mandatory = $True, Position = 5)]
          [string]$sqlsid
     )
     ################################################################################
     # Meaning of parameters in function sqlcall
     ################################################################################
     # 1. sql_message - section banner *without* chevrons <<<>>> (only text)
     #    The sql_message is also used as the job name if run asynchronously
     #    The sql_message is also used as a temporary filename
     # 2. sqltext - The text of the SQL statement
     # 3. run_async, set to 1 if this SQL should run asynchronously. If the SQL takes a long time to run
     #    we do not want to wait for the output of the SQL, but simply use the last output if it is fresh enough.
     # 4. the oracle sid



     # Here we set our connection string to the database instance.
     # This code could be expanded in future to support the oracle wallet.

     # we no longer assume we can login using "/ as sysdba", as we want to check if the listener is running
     $SQL_CONNECT = "user_connection_not_set"
     $SKIP_DOUBLE_ERROR = 0
     $ASM_FIRST_CHAR = "+"
     $CHECK_FIRST_CHAR = $sqlsid.substring(0, 1)
     if ( $CHECK_FIRST_CHAR.compareTo($ASM_FIRST_CHAR) -eq 0 ) {
          if ($ASMUSER) {
               # The ASMUSER variable is set in the config file , so we will use that for the connection
               $counter = 0
               # set default values for the connection variables
               $the_user = ""
               $the_password = ""
               $the_sysdba = ""
               $the_host = "localhost"
               $the_port = "1521"

               # cycle through the $ASMUSER variable, to get our connection data
               foreach ($the_dbuser in $ASMUSER) {
                    $counter = $counter + 1
                    switch ($counter) {
                         1 { $the_user = $the_dbuser }
                         2 { $the_password = $the_dbuser }
                         3 { $the_sysdba = $the_dbuser }
                         4 { $the_host = $the_dbuser }
                         5 { $the_port = $the_dbuser }
                         default { "Error handling Oracle database connection with config for ASMUSER." }
                    }
               }
               if ($the_sysdba ) {
                    $assysdbaconnect = " as $the_sysdba"
               }
               else {
                    $assysdbaconnect = ""
               }
               #$TNSALIAS="$the_host`:$the_port/$sqlsid"
               $UPPER_SID = $sqlsid.toupper()
               $TNSALIAS = "(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST=$the_host)(PORT=$the_port))(CONNECT_DATA=(SERVICE_NAME=+ASM)(INSTANCE_NAME=$UPPER_SID)(UR=A)))"
               # we presume we can use an EZconnect
               $SQL_CONNECT = "$the_user/$the_password@$TNSALIAS$assysdbaconnect"
               debug_echo "value of sql_connect in ASMUSER = $SQL_CONNECT"
          }
          else {
               debug_echo "ASMUSER is not defined"
          }

          # if $asmuser_$sqlsid is not used, then we will get an error here
          # Powershell cannot really use dynamic variables, as a workaround we silently continue
          # for this section of code
          $ErrorActionPreference = "SilentlyContinue"

          if ((get-variable "asmuser_$sqlsid").value -ne $null) {
               # The ASMUSER_SID variable is set in the config file, so we will use that for the connection
               $counter = 0
               # set default values for the connection variables
               $the_user = ""
               $the_password = ""
               $the_sysdba = ""
               $the_host = "localhost"
               $the_port = "1521"
               $the_service = ""

               # cycle through the "$ASMUSER$inst_name" variable, to get our connection data
               foreach ($the_dbuser in (get-variable "asmuser_$sqlsid").value) {
                    $counter = $counter + 1
                    switch ($counter) {
                         1 { $the_user = $the_dbuser }
                         2 { $the_password = $the_dbuser }
                         3 { $the_sysdba = $the_dbuser }
                         4 { $the_host = $the_dbuser }
                         5 { $the_port = $the_dbuser }
                         6 { $the_service = $the_dbuser }
                         default { "Error handling Oracle database connection with config for ASMUSER_SID." }
                    }
               }
               if ($the_sysdba ) {
                    $assysdbaconnect = " as $the_sysdba"
               }
               else {
                    $assysdbaconnect = ""
               }
               # $TNSALIAS="$the_host`:$the_port/$the_service"
               $TNSALIAS = "(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST=$the_host)(PORT=$the_port))(CONNECT_DATA=(SID=$the_service)))"
               # we presume we can use an EZconnect
               $SQL_CONNECT = "$the_user/$the_password@$TNSALIAS$assysdbaconnect"
               debug_echo "value of sql_connect in asmuser_sid = $SQL_CONNECT"
          }
          # now we set our action on error back to our normal value
          $ErrorActionPreference = $NORMAL_ACTION_PREFERENCE
     }
     else {
          if ($DBUSER) {
               # The DBUSER variable is set in the config file , so we will use that for the connection
               $counter = 0
               # set default values for the connection variables
               $the_user = ""
               $the_password = ""
               $the_sysdba = ""
               $the_host = "localhost"
               $the_port = "1521"

               # cycle through the $DBUSER variable, to get our connection data
               foreach ($the_dbuser in $DBUSER) {
                    $counter = $counter + 1
                    switch ($counter) {
                         1 { $the_user = $the_dbuser }
                         2 { $the_password = $the_dbuser }
                         3 { $the_sysdba = $the_dbuser }
                         4 { $the_host = $the_dbuser }
                         5 { $the_port = $the_dbuser }
                         default { "Error handling Oracle database connection with config for DBUSER." }
                    }
               }
               if ($the_sysdba ) {
                    $assysdbaconnect = " as $the_sysdba"
               }
               else {
                    $assysdbaconnect = ""
               }
               $UPPER_SID = $sqlsid.toupper()

               # use oracle wallet if requested in cfg file
               if ($the_user -like "/" ) {
                    $SQL_CONNECT = "/@$UPPER_SID$assysdbaconnect"
               }
               else {
                    $TNSALIAS = "(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST=$the_host)(PORT=$the_port))(CONNECT_DATA=(SID=$UPPER_SID)))"
                    # we presume we can use an EZconnect
                    $SQL_CONNECT = "$the_user/$the_password@$TNSALIAS$assysdbaconnect"
               }
               debug_echo "value of sql_connect in dbuser = $SQL_CONNECT"
          }
          else {
               debug_echo "DBUSER is not defined"
          }

          # if $dbuser_$sqlsid is not used, then we will get an error here
          # Powershell cannot really use dynamic variables, as a workaround we silently continue
          # for this section of code
          $ErrorActionPreference = "SilentlyContinue"

          if ((get-variable "dbuser_$sqlsid").value -ne $null) {
               # The DBUSER_SID variable is set in the config file, so we will use that for the connection
               $counter = 0
               # set default values for the connection variables
               $the_user = ""
               $the_password = ""
               $the_sysdba = ""
               $the_host = "localhost"
               $the_port = "1521"
               $the_service = ""

               # cycle through the "$DBUSER$inst_name" variable, to get our connection data
               foreach ($the_dbuser in (get-variable "dbuser_$sqlsid").value) {
                    $counter = $counter + 1
                    switch ($counter) {
                         1 { $the_user = $the_dbuser }
                         2 { $the_password = $the_dbuser }
                         3 { $the_sysdba = $the_dbuser }
                         4 { $the_host = $the_dbuser }
                         5 { $the_port = $the_dbuser }
                         6 { $the_service = $the_dbuser }
                         default { "Error handling Oracle database connection with config for DBUSER_SID." }
                    }
               }
               if ($the_sysdba ) {
                    $assysdbaconnect = " as $the_sysdba"
               }
               else {
                    $assysdbaconnect = ""
               }
               # $TNSALIAS="$the_host`:$the_port/$the_service"
               $TNSALIAS = "(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST=$the_host)(PORT=$the_port))(CONNECT_DATA=(SID=$the_service)))"
               # we presume we can use an EZconnect
               $SQL_CONNECT = "$the_user/$the_password@$TNSALIAS$assysdbaconnect"
               debug_echo "value of sql_connect in dbuser_sid = $SQL_CONNECT"
          }
          # now we set our action on error back to our normal value
          $ErrorActionPreference = $NORMAL_ACTION_PREFERENCE
     }




     # set the environment variable %ORACLE_SID% for the time this script is run
     $env:ORACLE_SID = "$sqlsid"
     # add the standard SQL (linesize, on error quit, etc.) to this SQL
     $THE_SQL = $SQL_START + $sqltext

     # The temporary file to store the output of the SQL
     # currently default path is used here. change this @TBR?
     $fullpath = $MK_TEMPDIR + "\" + "$sql_message.$sqlsid.txt"

     if ($run_async -eq 0) {
          $SKIP_DOUBLE_ERROR = 0
          try {
               $res = ( $THE_SQL | sqlplus -L -s "$SQL_CONNECT")
               if ($LastExitCode -eq 0) {
                    # we only show the output if there was no error...
                    $res | Set-Content $fullpath
                    cat $fullpath
               }
               else {
                    $SKIP_DOUBLE_ERROR = 1
                    # an error occurred
                    # add the SID and "FAILURE" to the output
                    $res = "$sqlsid|FAILURE|" + $res | select-string -pattern "ERROR"
                    # write the output to the file
                    $res = "<<<oracle_instance:sep(124)>>>" + "`n" + $res
                    $res | Set-Content $fullpath
                    # show the contents of the file
                    cat $fullpath
               }
          }

          catch {
               if ($SKIP_DOUBLE_ERROR -eq 0) {
                    $SKIP_DOUBLE_ERROR = 1
                    # an error occurred
                    # add the SID and "FAILURE" to the output
                    $res = "$sqlsid|FAILURE|" + $res | select-string -pattern "ERROR"
                    # write the output to the file
                    $res = "<<<oracle_instance:sep(124)>>>" + "`n" + $res
                    $res | Set-Content $fullpath
                    # show the contents of the file
                    cat $fullpath
               }

          }

     }
     else {
          [bool]$need_async_process = $false
          # We first check if the file exists, otherwise we cannot show the old SQL output
          if (Test-Path -path "$fullPath") {
               cat $fullpath
               # the file exists, so now we can check how old it is
               debug_echo "file found $run_async"
               $lastWrite = (get-item $fullPath).LastWriteTime
               # How old may the SQL Output files be, before new ones are generated?
               $timespan = new-timespan -days 0 -hours 0 -minutes ($CACHE_MAXAGE / 60)
               if (((get-date) - $lastWrite) -gt $timespan) {
                    # the file is too old - so start a new process
                    $need_async_process = $true
               }
          }
          else {
               # file not found, so we need to run it
               $need_async_process = $true
          }

          if ($need_async_process) {
               #####################################################
               # now we ensure that the async SQL Calls have up-to-date SQL outputs, running this job asynchronously...
               #####################################################
               debug_echo "about to call bg task $sql_message"
               if (-not(is_async_running)) {

                    $command = {
                        param([string]$sql_connect, [string]$sql, [string]$path, [string]$sql_sid)
                        $res = ("$sql" | sqlplus -s -L $sql_connect)
                        if ($LastExitCode -eq 0) {
                            $res | Set-Content $path
                        }
                        else {
                        $stripped_res = '$sql_sid|FAILURE|' + $res | select-string -pattern 'ERROR'
                        '<<<oracle_instance:sep(124)>>>' | Set-Content $path
                        $stripped_res | Add-Content $path
                        }
                    }

                    # This escaping is needed as it seems the here string attribute gets lost or has no effect when passing the
                    # variable to the script block
                    $escaped_sql = $THE_SQL.replace("'", "''")
                    $async_proc = Start-Process -PassThru powershell -windowstyle hidden -ArgumentList "-command invoke-command -scriptblock {$command} -argumentlist '$SQL_CONNECT', '$escaped_sql', '$fullpath', '$sqlsid'"
                    $async_proc.id | set-content $ASYNC_PROC_PATH
                    debug_echo "should be run here $run_async"
               }
          }
     }
     # normally we would simply return with a 1 or 0, but in powershell if I return from the function
     # with a value, then nothing else is shown on the screen. Hence the following less elegant solution...
     if ($SKIP_DOUBLE_ERROR -gt 0) {
          $global:ERROR_FOUND = 1
     }
}




################################################################################
# SQL for Performance information
################################################################################
Function sql_performance {
     if ($DBVERSION -gt 121000) {
          $query_performance = @'
          PROMPT <<<oracle_performance:sep(124)>>>;
          select upper(i.INSTANCE_NAME)
               ||'|'|| 'sys_time_model'
               ||'|'|| S.STAT_NAME
               ||'|'|| Round(s.value/1000000)
          from v$instance i,
               v$sys_time_model s
          where s.stat_name in('DB time', 'DB CPU')
          order by s.stat_name;
          select upper(i.INSTANCE_NAME ||'.'||vd.name)
               ||'|'|| 'sys_time_model'
               ||'|'|| S.STAT_NAME
               ||'|'|| Round(s.value/1000000)
          from v$instance i
          join v$con_sys_time_model s on s.stat_name in('DB time', 'DB CPU')
          join v$containers vd on vd.con_id = s.con_id
          join v$database d on d.cdb = 'YES'
          where vd.con_id <> 2
          order by s.stat_name;
          select upper(i.INSTANCE_NAME)
               ||'|'|| 'buffer_pool_statistics'
               ||'|'|| b.name
               ||'|'|| b.db_block_gets
               ||'|'|| b.db_block_change
               ||'|'|| b.consistent_gets
               ||'|'|| b.physical_reads
               ||'|'|| b.physical_writes
               ||'|'|| b.FREE_BUFFER_WAIT
               ||'|'|| b.BUFFER_BUSY_WAIT
          from v$instance i, v$BUFFER_POOL_STATISTICS b;
          select upper(i.INSTANCE_NAME)
               ||'|'|| 'SGA_info'
               ||'|'|| s.name
               ||'|'|| s.bytes
          from v$sgainfo s, v$instance i;
          select upper(i.INSTANCE_NAME)
               ||'|'|| 'librarycache'
               ||'|'|| b.namespace
               ||'|'|| b.gets
               ||'|'|| b.gethits
               ||'|'|| b.pins
               ||'|'|| b.pinhits
               ||'|'|| b.reloads
               ||'|'|| b.invalidations
          from v$instance i, v$librarycache b;

'@
          echo $query_performance
     }
     elseif ($DBVERSION -gt 101000) {
          $query_performance = @'
          prompt <<<oracle_performance:sep(124)>>>;
          select upper(i.INSTANCE_NAME)
               ||'|'|| 'sys_time_model'
               ||'|'|| S.STAT_NAME
               ||'|'|| Round(s.value/1000000)
          from v$instance i,
               v$sys_time_model s
          where s.stat_name in('DB time', 'DB CPU')
          order by s.stat_name;
          select upper(i.INSTANCE_NAME)
               ||'|'|| 'buffer_pool_statistics'
               ||'|'|| b.name
               ||'|'|| b.db_block_gets
               ||'|'|| b.db_block_change
               ||'|'|| b.consistent_gets
               ||'|'|| b.physical_reads
               ||'|'|| b.physical_writes
               ||'|'|| b.FREE_BUFFER_WAIT
               ||'|'|| b.BUFFER_BUSY_WAIT
          from v$instance i, V$BUFFER_POOL_STATISTICS b;
          select upper(i.INSTANCE_NAME)
               ||'|'|| 'SGA_info'
               ||'|'|| s.name
               ||'|'|| s.bytes
          from v$sgainfo s, v$instance i;
          select upper(i.INSTANCE_NAME)
               ||'|'|| 'librarycache'
               ||'|'|| b.namespace
               ||'|'|| b.gets
               ||'|'|| b.gethits
               ||'|'|| b.pins
               ||'|'|| b.pinhits
               ||'|'|| b.reloads
               ||'|'|| b.invalidations
          from v$instance i, V$librarycache b;

'@
          echo $query_performance
     }
}


################################################################################
# SQL for Tablespace information
################################################################################
Function sql_tablespaces {
     if ($DBVERSION -gt 121000) {
          $query_tablespace = @'
          prompt <<<oracle_tablespaces:sep(124)>>>;
          SET SERVEROUTPUT ON feedback off
          DECLARE
               type x is table of varchar2(20000) index by pls_integer;
               xx x;
          begin
               begin
                    execute immediate
                         'select upper(decode(vp.con_id, null, d.NAME,d.NAME||''.''||vp.name))
                              || ''|'' || dbf.file_name
                              || ''|'' || dbf.tablespace_name
                              || ''|'' || dbf.fstatus
                              || ''|'' || dbf.AUTOEXTENSIBLE
                              || ''|'' || dbf.blocks
                              || ''|'' || dbf.maxblocks
                              || ''|'' || dbf.USER_BLOCKS
                              || ''|'' || dbf.INCREMENT_BY
                              || ''|'' || dbf.ONLINE_STATUS
                              || ''|'' || dbf.BLOCK_SIZE
                              || ''|'' || decode(tstatus,''READ ONLY'', ''READONLY'', tstatus)
                              || ''|'' || dbf.free_blocks
                              || ''|'' || dbf.contents
                              || ''|'' || i.version
                         from v$database d
                         join v$instance i on 1=1
                         join (
                              select f.con_id, f.file_name, f.tablespace_name, f.status fstatus, f.AUTOEXTENSIBLE,
                                   f.blocks, f.maxblocks, f.USER_BLOCKS, f.INCREMENT_BY,
                                   f.ONLINE_STATUS, t.BLOCK_SIZE, t.status tstatus, nvl(sum(fs.blocks),0) free_blocks, t.contents
                              from cdb_data_files f
                              join cdb_tablespaces t on f.tablespace_name = t.tablespace_name
                                   and f.con_id = t.con_id
                              left outer join cdb_free_space fs on f.file_id = fs.file_id
                                   and f.con_id = fs.con_id
                              group by f.con_id, f.file_name, f.tablespace_name, f.status, f.autoextensible,
                                   f.blocks, f.maxblocks, f.user_blocks, f.increment_by, f.online_status,
                                   t.block_size, t.status, t.contents
                         ) dbf on 1=1
                         left outer join v$pdbs vp on dbf.con_id = vp.con_id
                         where d.database_role = ''PRIMARY'''
                    bulk collect into xx;
                    if xx.count >= 1 then
                         for i in 1 .. xx.count loop
                              dbms_output.put_line(xx(i));
                         end loop;
                    end if;
                    exception
                         when others then
                              for cur1 in (select upper(name) name from  v$database) loop
                                   dbms_output.put_line(cur1.name || '| Debug (121) 1: ' ||sqlerrm);
                              end loop;
               end;
          END;
/
          DECLARE
               type x is table of varchar2(20000) index by pls_integer;
               xx x;
          begin
               begin
                    execute immediate
                         'select upper(decode(dbf.con_id, null, d.NAME,dbf.name))
                              || ''|'' || dbf.file_name
                              || ''|'' || dbf.tablespace_name
                              || ''|'' || dbf.fstatus
                              || ''|'' || dbf.AUTOEXTENSIBLE
                              || ''|'' || dbf.blocks
                              || ''|'' || dbf.maxblocks
                              || ''|'' || dbf.USER_BLOCKS
                              || ''|'' || dbf.INCREMENT_BY
                              || ''|'' || dbf.ONLINE_STATUS
                              || ''|'' || dbf.BLOCK_SIZE
                              || ''|'' || decode(tstatus,''READ ONLY'', ''READONLY'', tstatus)
                              || ''|'' || dbf.free_blocks
                              || ''|'' || ''TEMPORARY''
                              || ''|'' || i.version
                         FROM v$database d
                         JOIN v$instance i ON 1 = 1
                         JOIN (
                              SELECT vp.name,
                                   vp.con_id,
                                   f.file_name,
                                   t.tablespace_name,
                                   f.status fstatus,
                                   f.autoextensible,
                                   f.blocks,
                                   f.maxblocks,
                                   f.user_blocks,
                                   f.increment_by,
                                   ''ONLINE'' online_status,
                                   t.block_size,
                                   t.status tstatus,
                                   f.blocks - nvl(SUM(tu.blocks),0) free_blocks,
                                   t.contents
                              FROM cdb_tablespaces t
                              JOIN (
                                   SELECT vp.con_id,d.name || ''.''|| vp.name name
                                   FROM v$containers vp
                                   JOIN v$database d ON 1 = 1
                                   WHERE d.cdb = ''YES''
                                        AND vp.con_id <> 2
                                   UNION ALL
                                   SELECT 0,name
                                   FROM v$database
                              ) vp ON t.con_id = vp.con_id
                              LEFT OUTER JOIN cdb_temp_files f ON t.con_id = f.con_id
                                   AND t.tablespace_name = f.tablespace_name
                              LEFT OUTER JOIN gv$tempseg_usage tu ON f.con_id = tu.con_id
                                   AND f.tablespace_name = tu.tablespace
                                   AND f.RELATIVE_FNO = tu.SEGRFNO#
                              WHERE t.contents = ''TEMPORARY''
                              GROUP BY vp.name,
                                        vp.con_id,
                                        f.file_name,
                                        t.tablespace_name,
                                        f.status,
                                        f.autoextensible,
                                        f.blocks,
                                        f.maxblocks,
                                        f.user_blocks,
                                        f.increment_by,
                                        t.block_size,
                                        t.status,
                                        t.contents
                         ) dbf ON 1 = 1
                         where d.database_role = ''PRIMARY'''
                    bulk collect into xx;
                    if xx.count >= 1 then
                          for i in 1 .. xx.count loop
                              dbms_output.put_line(xx(i));
                          end loop;
                    end if;
               exception
                    when others then
                         for cur1 in (select upper(name) name from  v$database) loop
                              dbms_output.put_line(cur1.name || '| Debug (121) 2: ' ||sqlerrm);
                         end loop;
               end;
          END;
/
              set serverout off

'@
          echo $query_tablespace
     }
     elseif ($DBVERSION -gt 102000) {
          $query_tablespace = @'
          prompt <<<oracle_tablespaces:sep(124)>>>;
          SET SERVEROUTPUT ON feedback off
          DECLARE
               type x is table of varchar2(20000) index by pls_integer;
               xx x;
          begin
               begin
                    execute immediate
                         'select upper(i.instance_name)
                              || ''|'' || file_name ||''|''|| tablespace_name ||''|''|| fstatus ||''|''|| AUTOEXTENSIBLE
                              ||''|''|| blocks ||''|''|| maxblocks ||''|''|| USER_BLOCKS ||''|''|| INCREMENT_BY
                              ||''|''|| ONLINE_STATUS ||''|''|| BLOCK_SIZE
                              ||''|''|| decode(tstatus,''READ ONLY'', ''READONLY'', tstatus) || ''|'' || free_blocks
                              ||''|''|| contents
                              ||''|''|| iversion
                         from v$database d , v$instance i, (
                              select f.file_name, f.tablespace_name, f.status fstatus, f.AUTOEXTENSIBLE,
                                   f.blocks, f.maxblocks, f.USER_BLOCKS, f.INCREMENT_BY,
                                   f.ONLINE_STATUS, t.BLOCK_SIZE, t.status tstatus, nvl(sum(fs.blocks),0) free_blocks, t.contents,
                                   (select version from v$instance) iversion
                              from dba_data_files f, dba_tablespaces t, dba_free_space fs
                              where f.tablespace_name = t.tablespace_name
                                   and f.file_id = fs.file_id(+)
                              group by f.file_name, f.tablespace_name, f.status, f.autoextensible,
                                   f.blocks, f.maxblocks, f.user_blocks, f.increment_by, f.online_status,
                                   t.block_size, t.status, t.contents)
                              where d.database_role = ''PRIMARY'''
                    bulk collect into xx;
                    if xx.count >= 1 then
                         for i in 1 .. xx.count loop
                              dbms_output.put_line(xx(i));
                         end loop;
                    end if;
               exception
                    when others then
                         for cur1 in (select upper(name) name from  v$database) loop
                              dbms_output.put_line(cur1.name || '| Debug (102) 1: ' ||sqlerrm);
                         end loop;
               end;
          END;
/

          DECLARE
               type x is table of varchar2(20000) index by pls_integer;
               xx x;
          begin
               begin
                    execute immediate
                         'select upper(i.instance_name)
                              || ''|'' || dbf.file_name
                              || ''|'' || dbf.tablespace_name
                              || ''|'' || dbf.fstatus
                              || ''|'' || dbf.AUTOEXTENSIBLE
                              || ''|'' || dbf.blocks
                              || ''|'' || dbf.maxblocks
                              || ''|'' || dbf.USER_BLOCKS
                              || ''|'' || dbf.INCREMENT_BY
                              || ''|'' || dbf.ONLINE_STATUS
                              || ''|'' || dbf.BLOCK_SIZE
                              || ''|'' || decode(tstatus,''READ ONLY'', ''READONLY'', tstatus)
                              || ''|'' || dbf.free_blocks
                              || ''|'' || ''TEMPORARY''
                              || ''|'' || i.version
                         FROM v$database d
                         JOIN v$instance i ON 1 = 1
                         JOIN (
                              SELECT vp.name,
                                   f.file_name,
                                   t.tablespace_name,
                                   f.status fstatus,
                                   f.autoextensible,
                                   f.blocks,
                                   f.maxblocks,
                                   f.user_blocks,
                                   f.increment_by,
                                   ''ONLINE'' online_status,
                                   t.block_size,
                                   t.status tstatus,
                                   f.blocks - nvl(SUM(tu.blocks),0) free_blocks,
                                   t.contents
                              FROM dba_tablespaces t
                              JOIN ( SELECT 0
                                   ,name
                                   FROM v$database
                              ) vp ON 1=1
                              LEFT OUTER JOIN dba_temp_files f ON t.tablespace_name = f.tablespace_name
                              LEFT OUTER JOIN gv$tempseg_usage tu ON f.tablespace_name = tu.tablespace
                                   AND f.RELATIVE_FNO = tu.SEGRFNO#
                              WHERE t.contents = ''TEMPORARY''
                              GROUP BY vp.name,
                                   f.file_name,
                                   t.tablespace_name,
                                   f.status,
                                   f.autoextensible,
                                   f.blocks,
                                   f.maxblocks,
                                   f.user_blocks,
                                   f.increment_by,
                                   t.block_size,
                                   t.status,
                                   t.contents
                         ) dbf ON 1 = 1'
                    bulk collect into xx;
                    if xx.count >= 1 then
                         for i in 1 .. xx.count loop
                              dbms_output.put_line(xx(i));
                         end loop;
                    end if;
               exception
                    when others then
                         for cur1 in (select upper(name) name from  v$database) loop
                              dbms_output.put_line(cur1.name || '| Debug (102) 2: ' ||sqlerrm);
                         end loop;
               end;
          END;
/
          set serverout off

'@
          echo $query_tablespace
     }
     elseif ($DBVERSION -gt 92000) {
          $query_tablespace = @'
          prompt <<<oracle_tablespaces:sep(124)>>>;
          select upper(d.NAME)
               || '|' || file_name
               || '|' || tablespace_name
               || '|' || fstatus
               || '|' || AUTOEXTENSIBLE
               || '|' || blocks
               || '|' || maxblocks
               || '|' || USER_BLOCKS
               || '|' || INCREMENT_BY
               || '|' || ONLINE_STATUS
               || '|' || BLOCK_SIZE
               || '|' || decode(tstatus,'READ ONLY', 'READONLY', tstatus)
               || '|' || free_blocks
               || '|' || contents
          from v$database d , (
               select
                    f.file_name,
                    f.tablespace_name,
                    f.status fstatus,
                    f.AUTOEXTENSIBLE,
                    f.blocks,
                    f.maxblocks,
                    f.USER_BLOCKS,
                    f.INCREMENT_BY,
                    'ONLINE' ONLINE_STATUS,
                    t.BLOCK_SIZE,
                    t.status tstatus,
                    nvl(sum(fs.blocks),0) free_blocks,
                    t.contents
               from dba_data_files f, dba_tablespaces t, dba_free_space fs
               where f.tablespace_name = t.tablespace_name
               and f.file_id = fs.file_id(+)
               group by
                    f.file_name,
                    f.tablespace_name,
                    f.status,
                    f.autoextensible,
                    f.blocks,
                    f.maxblocks,
                    f.user_blocks,
                    f.increment_by,
                    'ONLINE',
                    t.block_size,
                    t.status,
                    t.contents
               UNION
               select
                    f.file_name,
                    f.tablespace_name,
                    'ONLINE' status,
                    f.AUTOEXTENSIBLE,
                    f.blocks,
                    f.maxblocks,
                    f.USER_BLOCKS,
                    f.INCREMENT_BY,
                    'TEMP',
                    t.BLOCK_SIZE,
                    'TEMP' status,
                    sum(sh.blocks_free) free_blocks,
                    'TEMPORARY'
               from v$thread th, dba_temp_files f, dba_tablespaces t, v$temp_space_header sh
               WHERE f.tablespace_name = t.tablespace_name and f.file_id = sh.file_id
               GROUP BY
                    th.instance,
                    f.file_name,
                    f.tablespace_name,
                    'ONLINE',
                    f.autoextensible,
                    f.blocks,
                    f.maxblocks,
                    f.user_blocks,
                    f.increment_by,
                    'TEMP',
                    t.block_size,
                    t.status
          );
          select * from v$instance;

'@

          echo $query_tablespace
     }

}





################################################################################
# SQL for Dataguard Statistics
################################################################################
Function sql_dataguard_stats {
     if ($DBVERSION -gt 102000) {
          $query_dataguard_stats = @'
          prompt <<<oracle_dataguard_stats:sep(124)>>>;
          SELECT upper(i.instance_name)
                 ||'|'|| upper(d.DB_UNIQUE_NAME)
                 ||'|'|| d.DATABASE_ROLE
                 ||'|'|| ds.name
                 ||'|'|| ds.value
                 ||'|'|| d.SWITCHOVER_STATUS
                 ||'|'|| d.DATAGUARD_BROKER
                 ||'|'|| d.PROTECTION_MODE
                 ||'|'|| d.FS_FAILOVER_STATUS
                 ||'|'|| d.FS_FAILOVER_OBSERVER_PRESENT
                 ||'|'|| d.FS_FAILOVER_OBSERVER_HOST
                 ||'|'|| d.FS_FAILOVER_CURRENT_TARGET
                 ||'|'|| ms.status
          FROM v$database d
          JOIN v$parameter vp on 1=1
          JOIN v$instance i on 1=1
          left outer join V$dataguard_stats ds on 1=1
          left outer join v$managed_standby ms on ms.process = 'MRP0'
          WHERE vp.name = 'log_archive_config'
          AND   vp.value is not null
          ORDER BY 1;

'@
          echo $query_dataguard_stats
     }
}


################################################################################
# SQL for Recovery status
################################################################################
Function sql_recovery_status {
     if ($DBVERSION -gt 121000) {
          $query_recovery_status = @'
          prompt <<<oracle_recovery_status:sep(124)>>>;
          SELECT upper(i.instance_name)
                 ||'|'|| d.DB_UNIQUE_NAME
                 ||'|'|| d.DATABASE_ROLE
                 ||'|'|| d.open_mode
                 ||'|'|| dh.file#
                 ||'|'|| round((dh.CHECKPOINT_TIME-to_date('01.01.1970','dd.mm.yyyy'))*24*60*60)
                 ||'|'|| round((sysdate-dh.CHECKPOINT_TIME)*24*60*60)
                 ||'|'|| dh.STATUS
                 ||'|'|| dh.RECOVER
                 ||'|'|| dh.FUZZY
                 ||'|'|| dh.CHECKPOINT_CHANGE#
                 ||'|'|| nvl(vb.STATUS, 'unknown')
                 ||'|'|| nvl2(vb.TIME, round((sysdate-vb.TIME)*24*60*60), 0)
          FROM V$datafile_header dh
          JOIN v$database d on 1=1
          JOIN v$instance i on 1=1
          LEFT OUTER JOIN v$backup vb on vb.file# = dh.file#
          LEFT OUTER JOIN V$PDBS vp on dh.con_id = vp.con_id
          ORDER BY dh.file#;

'@
          echo $query_recovery_status
     }

     elseif ($DBVERSION -gt 101000) {
          $query_recovery_status = @'
          prompt <<<oracle_recovery_status:sep(124)>>>;
          SELECT upper(d.NAME)
                     ||'|'|| d.DB_UNIQUE_NAME
                     ||'|'|| d.DATABASE_ROLE
                     ||'|'|| d.open_mode
                     ||'|'|| dh.file#
                     ||'|'|| round((dh.CHECKPOINT_TIME-to_date('01.01.1970','dd.mm.yyyy'))*24*60*60)
                     ||'|'|| round((sysdate-dh.CHECKPOINT_TIME)*24*60*60)
                     ||'|'|| dh.STATUS
                     ||'|'|| dh.RECOVER
                     ||'|'|| dh.FUZZY
                     ||'|'|| dh.CHECKPOINT_CHANGE#
              FROM  V$datafile_header dh, v$database d, v$instance i
              ORDER BY dh.file#;

'@
          echo $query_recovery_status
     }
     elseif ($DBVERSION -gt 92000) {
          $query_recovery_status = @'
          prompt <<<oracle_recovery_status:sep(124)>>>;
          SELECT upper(d.NAME)
                     ||'|'|| d.NAME
                     ||'|'|| d.DATABASE_ROLE
                     ||'|'|| d.open_mode
                     ||'|'|| dh.file#
                     ||'|'|| round((dh.CHECKPOINT_TIME-to_date('01.01.1970','dd.mm.yyyy'))*24*60*60)
                     ||'|'|| round((sysdate-dh.CHECKPOINT_TIME)*24*60*60)
                     ||'|'|| dh.STATUS
                     ||'|'|| dh.RECOVER
                     ||'|'|| dh.FUZZY
                     ||'|'|| dh.CHECKPOINT_CHANGE#
              FROM  V$datafile_header dh, v$database d, v$instance i
              ORDER BY dh.file#;

'@

          echo $query_recovery_status
     }
}


################################################################################
# SQL for RMAN Backup information
################################################################################
Function sql_rman {
     if ($DBVERSION -gt 121000) {
          $query_rman = @'
          prompt <<<oracle_rman:sep(124)>>>;
          select /* check_mk rman1 */ upper(name)
               || '|'|| 'COMPLETED'
               || '|'|| to_char(COMPLETION_TIME, 'YYYY-mm-dd_HH24:MI:SS')
               || '|'|| to_char(COMPLETION_TIME, 'YYYY-mm-dd_HH24:MI:SS')
               || '|'|| case when INCREMENTAL_LEVEL IS NULL
                        then 'DB_FULL'
                        else 'DB_INCR'
                        end
               || '|'|| INCREMENTAL_LEVEL
               || '|'|| round(((sysdate-COMPLETION_TIME) * 24 * 60), 0)
               || '|'|| INCREMENTAL_CHANGE#
          from (
               select upper(i.instance_name) name
                    , bd2.INCREMENTAL_LEVEL, bd2.INCREMENTAL_CHANGE#, min(bd2.COMPLETION_TIME) COMPLETION_TIME
               from (
                    select bd.file#, bd.INCREMENTAL_LEVEL, max(bd.COMPLETION_TIME) COMPLETION_TIME
                    from v$backup_datafile bd
                    join v$datafile_header dh on dh.file# = bd.file#
                    where dh.status = 'ONLINE'
                         and dh.con_id <> 2
                    group by bd.file#, bd.INCREMENTAL_LEVEL
               ) bd
               join v$backup_datafile bd2 on bd2.file# = bd.file#
                    and bd2.COMPLETION_TIME = bd.COMPLETION_TIME
               join v$database vd on vd.RESETLOGS_CHANGE# = bd2.RESETLOGS_CHANGE#
               join v$instance i on 1=1
               group by upper(i.instance_name)
                    , bd2.INCREMENTAL_LEVEL
                    , bd2.INCREMENTAL_CHANGE#
               order by name, bd2.INCREMENTAL_LEVEL
          );

          select /* check_mk rman2 */ name
               || '|' || 'COMPLETED'
               || '|'
               || '|' || to_char(CHECKPOINT_TIME, 'yyyy-mm-dd_hh24:mi:ss')
               || '|' || 'CONTROLFILE'
               || '|'
               || '|' || round((sysdate - CHECKPOINT_TIME) * 24 * 60)
               || '|' || '0'
          from (
               select upper(i.instance_name) name
                    ,max(bcd.CHECKPOINT_TIME) CHECKPOINT_TIME
               from v$database d
               join V$BACKUP_CONTROLFILE_DETAILS bcd on d.RESETLOGS_CHANGE# = bcd.RESETLOGS_CHANGE#
               join v$instance i on 1=1
               group by upper(i.instance_name)
          );

          select /* check_mk rman3 */ name
               || '|COMPLETED'
               || '|'|| to_char(sysdate, 'YYYY-mm-dd_HH24:MI:SS')
               || '|'|| to_char(completed, 'YYYY-mm-dd_HH24:MI:SS')
               || '|ARCHIVELOG||'
               || round((sysdate - completed)*24*60,0)
               || '|'
          from (
               select upper(i.instance_name) name
                    , max(a.completion_time) completed
                    , case when a.backup_count > 0 then 1 else 0 end
               from v$archived_log a, v$database d, v$instance i
               where a.backup_count > 0
                    and a.dest_id in (
                         select b.dest_id
                         from v$archive_dest b
                         where b.target = 'PRIMARY'
                              and b.SCHEDULE = 'ACTIVE'
                    )
               group by d.NAME, i.instance_name
                    , case when a.backup_count > 0 then 1 else 0 end
          );

'@
          echo $query_rman
     }
     elseif ($DBVERSION -gt 102000) {
          $query_rman = @'
          prompt <<<oracle_rman:sep(124)>>>;
          select /* check_mk rman1 */ upper(name)
               || '|'|| 'COMPLETED'
               || '|'|| to_char(COMPLETION_TIME, 'YYYY-mm-dd_HH24:MI:SS')
               || '|'|| to_char(COMPLETION_TIME, 'YYYY-mm-dd_HH24:MI:SS')
               || '|'|| case when INCREMENTAL_LEVEL IS NULL
                         then 'DB_FULL'
                         else 'DB_INCR'
                         end
               || '|'|| INCREMENTAL_LEVEL
               || '|'|| round(((sysdate-COMPLETION_TIME) * 24 * 60), 0)
               || '|'|| INCREMENTAL_CHANGE#
          from (
               select upper(i.instance_name) name
                    , bd2.INCREMENTAL_LEVEL, bd2.INCREMENTAL_CHANGE#, min(bd2.COMPLETION_TIME) COMPLETION_TIME
               from (
                    select bd.file#, bd.INCREMENTAL_LEVEL, max(bd.COMPLETION_TIME) COMPLETION_TIME
                    from v$backup_datafile bd
                    join v$datafile_header dh on dh.file# = bd.file#
                    where dh.status = 'ONLINE'
                    group by bd.file#, bd.INCREMENTAL_LEVEL
               ) bd
               join v$backup_datafile bd2 on bd2.file# = bd.file#
                    and bd2.COMPLETION_TIME = bd.COMPLETION_TIME
               join v$database vd on vd.RESETLOGS_CHANGE# = bd2.RESETLOGS_CHANGE#
               join v$instance i on 1=1
               group by upper(i.instance_name)
                    , bd2.INCREMENTAL_LEVEL
                    , bd2.INCREMENTAL_CHANGE#
               order by name, bd2.INCREMENTAL_LEVEL
          );

          select /* check_mk rman2 */ name
               || '|' || 'COMPLETED'
               || '|'
               || '|' || to_char(CHECKPOINT_TIME, 'yyyy-mm-dd_hh24:mi:ss')
               || '|' || 'CONTROLFILE'
               || '|'
               || '|' || round((sysdate - CHECKPOINT_TIME) * 24 * 60)
               || '|' || '0'
          from (
               select upper(i.instance_name) name
                    ,max(bcd.CHECKPOINT_TIME) CHECKPOINT_TIME
               from v$database d
               join V$BACKUP_CONTROLFILE_DETAILS bcd on d.RESETLOGS_CHANGE# = bcd.RESETLOGS_CHANGE#
               join v$instance i on 1=1
               group by upper(i.instance_name)
          );

          select /* check_mk rman3 */ name
               || '|COMPLETED'
               || '|'|| to_char(sysdate, 'YYYY-mm-dd_HH24:MI:SS')
               || '|'|| to_char(completed, 'YYYY-mm-dd_HH24:MI:SS')
               || '|ARCHIVELOG||'
               || round((sysdate - completed)*24*60,0)
               || '|'
          from (
               select upper(i.instance_name) name
                    , max(a.completion_time) completed
                    , case when a.backup_count > 0 then 1 else 0 end
               from v$archived_log a, v$database d, v$instance i
               where a.backup_count > 0
                    and a.dest_id in (
                         select b.dest_id
                         from v$archive_dest b
                         where b.target = 'PRIMARY'
                              and b.SCHEDULE = 'ACTIVE'
                    )
               group by d.NAME, i.instance_name
                    , case when a.backup_count > 0 then 1 else 0 end
          );

'@
          echo $query_rman
     }
     elseif ($DBVERSION -gt 92000) {
          $query_rman = @'
          prompt <<<oracle_rman:sep(124)>>>;
          SELECT upper(d.NAME)
               ||'|'|| a.STATUS
               ||'|'|| to_char(a.START_TIME, 'YYYY-mm-dd_HH24:MI:SS')
               ||'|'|| to_char(a.END_TIME, 'YYYY-mm-dd_HH24:MI:SS')
               ||'|'|| replace(b.INPUT_TYPE, ' ', '_')
               ||'|'|| round(((sysdate - END_TIME) * 24 * 60),0)
          FROM V$RMAN_BACKUP_JOB_DETAILS a, v$database d, (
               SELECT input_type, max(command_id) as command_id
               FROM V$RMAN_BACKUP_JOB_DETAILS
               WHERE START_TIME > sysdate-14
                    and input_type != 'ARCHIVELOG'
                    and STATUS<>'RUNNING' GROUP BY input_type
          ) b
          WHERE a.COMMAND_ID = b.COMMAND_ID
          UNION ALL
          select name
               || '|COMPLETED'
               || '|'|| to_char(sysdate, 'YYYY-mm-dd_HH24:MI:SS')
               || '|'|| to_char(completed, 'YYYY-mm-dd_HH24:MI:SS')
               || '|ARCHIVELOG|'
               || round((sysdate - completed)*24*60,0)
          from (
               select d.name
                    , max(a.completion_time) completed
                    , case when a.backup_count > 0 then 1 else 0 end
               from v$archived_log a, v$database d
               where a.backup_count > 0
                    and a.dest_id in (
                         select b.dest_id
                         from v$archive_dest b
                         where b.target = 'PRIMARY'
                              and b.SCHEDULE = 'ACTIVE'
                    )
               group by d.name, case when a.backup_count > 0 then 1 else 0 end
          );

'@
          echo $query_rman
     }
}



################################################################################
# SQL for Flash Recovery Area information
################################################################################
Function sql_recovery_area {
     if ($DBVERSION -gt 102000) {
          $query_recovery_area = @'
          prompt <<<oracle_recovery_area:sep(124)>>>;
          select upper(i.instance_name)
                 ||'|'|| round((SPACE_USED-SPACE_RECLAIMABLE)/
                           (CASE NVL(SPACE_LIMIT,1) WHEN 0 THEN 1 ELSE SPACE_LIMIT END)*100)
                 ||'|'|| round(SPACE_LIMIT/1024/1024)
                 ||'|'|| round(SPACE_USED/1024/1024)
                 ||'|'|| round(SPACE_RECLAIMABLE/1024/1024)
                 ||'|'|| d.FLASHBACK_ON
          from V$RECOVERY_FILE_DEST, v$database d, v$instance i;

'@

          echo $query_recovery_area
     }
}




################################################################################
# SQL for UNDO information
################################################################################
Function sql_undostat {
     if ($DBVERSION -gt 121000) {
          $query_undostat = @'
          prompt <<<oracle_undostat:sep(124)>>>;
          select decode(vp.con_id, null, upper(i.INSTANCE_NAME)
                           ,upper(i.INSTANCE_NAME || '.' || vp.name))
                 ||'|'|| ACTIVEBLKS
                 ||'|'|| MAXCONCURRENCY
                 ||'|'|| TUNED_UNDORETENTION
                 ||'|'|| maxquerylen
                 ||'|'|| NOSPACEERRCNT
          from v$instance i
          join
              (select * from v$undostat
                where TUNED_UNDORETENTION > 0
               order by end_time desc
               fetch next 1 rows only
              ) u on 1=1
          left outer join v$pdbs vp on vp.con_id = u.con_id;

'@
          echo $query_undostat
     }
     elseif ($DBVERSION -gt 102000) {
          $query_undostat = @'
          prompt <<<oracle_undostat:sep(124)>>>;
          select upper(i.INSTANCE_NAME)
                     ||'|'|| ACTIVEBLKS
                     ||'|'|| MAXCONCURRENCY
                     ||'|'|| TUNED_UNDORETENTION
                     ||'|'|| maxquerylen
                     ||'|'|| NOSPACEERRCNT
              from v$instance i,
                  (select * from (select *
                                  from v$undostat order by end_time desc
                                 )
                            where rownum = 1
                              and TUNED_UNDORETENTION > 0
                  );

'@
          echo $query_undostat
     }
     elseif ($DBVERSION -gt 92000) {
          # TUNED_UNDORETENTION and ACTIVEBLKS are not available in Oracle <=9.2!
          # we set a -1 for filtering in check_undostat
          $query_undostat = @'
          prompt <<<oracle_undostat:sep(124)>>>;
          select upper(i.INSTANCE_NAME)
                     ||'|-1'
                     ||'|'|| MAXCONCURRENCY
                     ||'|-1'
                     ||'|'|| maxquerylen
                     ||'|'|| NOSPACEERRCNT
                  from v$instance i,
                  (select * from (select *
                                  from v$undostat order by end_time desc
                                 )
                            where rownum = 1
                  );

'@
          echo $query_undostat
     }
}




################################################################################
# SQL for resumable information
################################################################################
Function sql_resumable {
     $query_resumable = @'
          prompt <<<oracle_resumable:sep(124)>>>;
          SET SERVEROUTPUT ON feedback off
          DECLARE
               type x is table of varchar2(20000) index by pls_integer;
               xx x;
          begin
               begin
                    execute immediate
                         'select upper(i.INSTANCE_NAME)
                              ||''|''|| u.username
                              ||''|''|| a.SESSION_ID
                              ||''|''|| a.status
                              ||''|''|| a.TIMEOUT
                              ||''|''|| round((sysdate-to_date(a.SUSPEND_TIME,''mm/dd/yy hh24:mi:ss''))*24*60*60)
                              ||''|''|| a.ERROR_NUMBER
                              ||''|''|| to_char(to_date(a.SUSPEND_TIME, ''mm/dd/yy hh24:mi:ss''),''mm/dd/yy_hh24:mi:ss'')
                              ||''|''|| a.RESUME_TIME
                              ||''|''|| a.ERROR_MSG
                         from dba_resumable a, v$instance i, dba_users u
                         where a.INSTANCE_ID = i.INSTANCE_NUMBER
                         and u.user_id = a.user_id
                         and a.SUSPEND_TIME is not null
                         union all
                         select upper(i.INSTANCE_NAME)
                              || ''|||||||||''
                         from v$instance i'
                    bulk collect into xx;
                    if xx.count >= 1 then
                        for i in 1 .. xx.count loop
                            dbms_output.put_line(xx(i));
                        end loop;
                    end if;
               exception
                    when others then
                         for cur1 in (select upper(i.instance_name) instance_name from  v$instance i) loop
                              dbms_output.put_line(cur1.instance_name || '| Debug: '||sqlerrm);
                         end loop;
               end;
          END;
          /
          set serverout off

'@
     echo $query_resumable
}


################################################################################
# SQL for scheduler_jobs information
################################################################################
Function sql_jobs {
     if ($DBVERSION -gt 121000) {
          $query_scheduler_jobs = @'
          prompt <<<oracle_jobs:sep(124)>>>;
          SET SERVEROUTPUT ON feedback off
          DECLARE
              type x is table of varchar2(20000) index by pls_integer;
              xx x;
          begin
               begin
                    execute immediate
                         'SELECT upper(vp.name)
                              ||''|''|| j.OWNER
                              ||''|''|| j.JOB_NAME
                              ||''|''|| j.STATE
                              ||''|''|| ROUND((TRUNC(sysdate) + j.LAST_RUN_DURATION - TRUNC(sysdate)) * 86400)
                              ||''|''|| j.RUN_COUNT
                              ||''|''|| j.ENABLED
                              ||''|''|| NVL(j.NEXT_RUN_DATE, to_date(''1970-01-01'', ''YYYY-mm-dd''))
                              ||''|''|| NVL(j.SCHEDULE_NAME, ''-'')
                              ||''|''|| jd.STATUS
                         FROM cdb_scheduler_jobs j
                              JOIN (
                                   SELECT vp.con_id,d.name || ''|'' || vp.name name
                                   FROM v$containers vp
                                   JOIN v$database d on 1=1
                                   WHERE d.cdb = ''YES'' and vp.con_id <> 2
                                   AND d.database_role = ''PRIMARY''
                                   AND d.open_mode = ''READ WRITE''
                                   UNION ALL
                                   SELECT 0, name
                                   FROM v$database d
                                   WHERE d.database_role = ''PRIMARY''
                                   AND d.open_mode = ''READ WRITE''
                                   ) vp on j.con_id = vp.con_id
                              left outer join (SELECT con_id, owner, job_name, max(LOG_ID) log_id
                                   FROM cdb_scheduler_job_run_details dd
                                   group by con_id, owner, job_name
                                   ) jm on jm.JOB_NAME = j.JOB_NAME
                                   and jm.owner=j.OWNER
                                   and jm.con_id = j.con_id
                              left outer join cdb_scheduler_job_run_details jd
                                   on jd.con_id = jm.con_id
                                   AND jd.owner = jm.OWNER
                                   AND jd.JOB_NAME = jm.JOB_NAME
                                   AND jd.LOG_ID = jm.LOG_ID
                         WHERE not (j.auto_drop = ''TRUE'' and REPEAT_INTERVAL is null)'
                    bulk collect into xx;
                    if xx.count >= 1 then
                         for i in 1 .. xx.count loop
                              dbms_output.put_line(xx(i));
                         end loop;
                    end if;
               exception
                    when others then
                         for cur1 in (select upper(name) name from  v$database) loop
                              dbms_output.put_line(cur1.name || '| Debug (121): ' ||sqlerrm);
                         end loop;
               end;
          END;
          /
          set serverout off

'@
          echo $query_scheduler_jobs
     }
     elseif ($DBVERSION -gt 102000) {
          $query_scheduler_jobs = @'
          prompt <<<oracle_jobs:sep(124)>>>;
          SET SERVEROUTPUT ON feedback off
               DECLARE
                    type x is table of varchar2(20000) index by pls_integer;
                    xx x;
          begin
               begin
                    execute immediate
                         'SELECT upper(vd.NAME)
                              ||''|''|| j.OWNER
                              ||''|''|| j.JOB_NAME
                              ||''|''|| j.STATE
                              ||''|''|| ROUND((TRUNC(sysdate) + j.LAST_RUN_DURATION - TRUNC(sysdate)) * 86400)
                              ||''|''|| j.RUN_COUNT
                              ||''|''|| j.ENABLED
                              ||''|''|| NVL(j.NEXT_RUN_DATE, to_date(''1970-01-01'', ''YYYY-mm-dd''))
                              ||''|''|| NVL(j.SCHEDULE_NAME, ''-'')
                              ||''|''|| jd.STATUS
                         FROM dba_scheduler_jobs j
                         join v$database vd on 1 = 1
                         join v$instance i on 1 = 1
                         left outer join (
                              SELECT owner, job_name, max(LOG_ID) log_id
                              FROM dba_scheduler_job_run_details dd
                              group by owner, job_name
                              ) jm on jm.JOB_NAME = j.JOB_NAME
                              and jm.owner=j.OWNER
                         left outer join dba_scheduler_job_run_details jd
                              on jd.owner = jm.OWNER
                              AND jd.JOB_NAME = jm.JOB_NAME
                              AND jd.LOG_ID = jm.LOG_ID
                         WHERE vd.database_role = ''PRIMARY''
                         AND vd.open_mode = ''READ WRITE''
                         AND not (j.auto_drop = ''TRUE'' and REPEAT_INTERVAL is null)'
                    bulk collect into xx;
                    if xx.count >= 1 then
                         for i in 1 .. xx.count loop
                              dbms_output.put_line(xx(i));
                         end loop;
                    end if;
               exception
                    when others then
                         for cur1 in (select upper(name) name from  v$database) loop
                              dbms_output.put_line(cur1.name || '| Debug (102): ' ||sqlerrm);
                         end loop;
               end;
          END;
          /
          set serverout off

'@
          echo $query_scheduler_jobs
     }
}


################################################################################
# SQL for Tablespace quotas information
################################################################################
Function sql_ts_quotas {
     $query_ts_quotas = @'
     prompt <<<oracle_ts_quotas:sep(124)>>>;
     select upper(d.NAME)
          ||'|'|| Q.USERNAME
          ||'|'|| Q.TABLESPACE_NAME
          ||'|'|| Q.BYTES
          ||'|'|| Q.MAX_BYTES
     from dba_ts_quotas Q, v$database d
     where max_bytes > 0
     union all
     select upper(d.NAME)
          ||'|||'
     from v$database d
     order by 1;

'@
     echo $query_ts_quotas
}



################################################################################
# SQL for Oracle Version information
################################################################################
Function sql_version {
     $query_version = @'
     prompt <<<oracle_version:sep(124)>>>;
     select upper(i.INSTANCE_NAME)
	     || '|' || banner
	from v$version, v$instance i
	where banner like 'Oracle%';

'@
     echo $query_version
}



################################################################################
# SQL for sql_instance information
################################################################################
Function sql_instance {
     if ($ORACLE_SID.substring(0, 1) -eq "+") {
          $query_instance = @'
          prompt <<<oracle_instance:sep(124)>>>;
          select upper(i.instance_name)
               || '|' || i.VERSION
               || '|' || i.STATUS
               || '|' || i.LOGINS
               || '|' || i.ARCHIVER
               || '|' || round((sysdate - i.startup_time) * 24*60*60)
               || '|' || '0'
               || '|' || 'NO'
               || '|' || 'ASM'
               || '|' || 'NO'
               || '|' || i.instance_name
          from v$instance i;

'@
     }
     else {
          if ($DBVERSION -gt 121010) {
               $query_instance = @'
               prompt <<<oracle_instance:sep(124)>>>;
               select upper(instance_name)
                    || '|' || version
                    || '|' || status
                    || '|' || logins
                    || '|' || archiver
                    || '|' || round((sysdate - startup_time) * 24*60*60)
                    || '|' || dbid
                    || '|' || log_mode
                    || '|' || database_role
                    || '|' || force_logging
                    || '|' || name
                    || '|' || to_char(created, 'ddmmyyyyhh24mi')
                    || '|' || upper(value)
                    || '|' || con_id
                    || '|' || pname
                    || '|' || pdbid
                    || '|' || popen_mode
                    || '|' || prestricted
                    || '|' || ptotal_time
                    || '|' || precovery_status
                    || '|' || round(nvl(popen_time, -1))
                    || '|' || pblock_size
               from(
                    select i.instance_name, i.version, i.status, i.logins, i.archiver
                         ,i.startup_time, d.dbid, d.log_mode, d.database_role, d.force_logging
                         ,d.name, d.created, p.value, vp.con_id, vp.name pname
                         ,vp.dbid pdbid, vp.open_mode popen_mode, vp.restricted prestricted, vp.total_size ptotal_time
                         ,vp.block_size pblock_size, vp.recovery_status precovery_status
                         ,(cast(systimestamp as date) - cast(open_time as date))  * 24*60*60 popen_time
                    from v$instance i
                    join v$database d on 1=1
                    join v$parameter p on 1=1
                    join v$pdbs vp on 1=1
                    where p.name = 'enable_pluggable_database'
                    union all
                    select
                         i.instance_name, i.version, i.status, i.logins, i.archiver
                         ,i.startup_time, d.dbid, d.log_mode, d.database_role, d.force_logging
                         ,d.name, d.created, p.value, 0 con_id, null pname
                         ,0 pdbis, null popen_mode, null prestricted, null ptotal_time
                         ,0 pblock_size, null precovery_status, null popen_time
                    from v$instance i
                    join v$database d on 1=1
                    join v$parameter p on 1=1
                    where p.name = 'enable_pluggable_database'
                    order by con_id
               );

'@
          }
          else {
               $query_instance = @'
              prompt <<<oracle_instance:sep(124)>>>;
              select upper(i.instance_name)
                         || '|' || i.VERSION
                         || '|' || i.STATUS
                         || '|' || i.LOGINS
                         || '|' || i.ARCHIVER
                         || '|' || round((sysdate - i.startup_time) * 24*60*60)
                         || '|' || DBID
                         || '|' || LOG_MODE
                         || '|' || DATABASE_ROLE
                         || '|' || FORCE_LOGGING
                         || '|' || d.name
                         || '|' || to_char(d.created, 'ddmmyyyyhh24mi')
                    from v$instance i, v$database d;

'@
          }
     }
     echo $query_instance
}




################################################################################
# SQL for sql_sessions information
################################################################################
Function sql_sessions {
     if ($DBVERSION -gt 121000) {
          $query_sessions = @'
          prompt <<<oracle_sessions:sep(124)>>>;
          SELECT upper(vp.name)
               || '|' || ltrim(COUNT(1))
               || decode(vp.con_id, 0, '|'||ltrim(rtrim(LIMIT_VALUE))||'|-1')
          FROM (
               SELECT vp.con_id
                    ,i.instance_name || '.' || vp.name name
               FROM v$containers vp
               JOIN v$instance i ON 1 = 1
               JOIN v$database d on 1=1
               WHERE d.cdb = 'YES' and vp.con_id <> 2
               UNION ALL
               SELECT 0, instance_name
               FROM v$instance
               ) vp
          JOIN v$resource_limit rl on RESOURCE_NAME = 'sessions'
          LEFT OUTER JOIN v$session vs ON vp.con_id = vs.con_id
          GROUP BY vp.name, vp.con_id, rl.LIMIT_VALUE
          ORDER BY 1;

'@
          echo $query_sessions
     }
     else {
          $query_sessions = @'
          prompt <<<oracle_sessions:sep(124)>>>;
          select upper(i.instance_name)
               || '|' || CURRENT_UTILIZATION
               || '|' || ltrim(LIMIT_VALUE)
               || '|' || MAX_UTILIZATION
          from v$resource_limit, v$instance i
          where RESOURCE_NAME = 'sessions';

'@
          echo $query_sessions
     }
}



################################################################################
# SQL for sql_processes information
################################################################################
Function sql_processes {
     $query_processes = @'
     prompt <<<oracle_processes:sep(124)>>>;
     select upper(i.instance_name)
          || '|' || CURRENT_UTILIZATION
          || '|' || ltrim(rtrim(LIMIT_VALUE))
     from v$resource_limit, v$instance i
     where RESOURCE_NAME = 'processes';

'@
     echo $query_processes
}



################################################################################
# SQL for sql_logswitches information
################################################################################
Function sql_logswitches {
     $query_logswitches = @'
     prompt <<<oracle_logswitches:sep(124)>>>;
     select upper(i.instance_name)
          || '|' || logswitches
     from v$instance i ,
          (select count(1) logswitches
           from v$loghist h , v$instance i
           where h.first_time > sysdate - 1/24
           and h.thread# = i.instance_number);

'@
     echo $query_logswitches
}


################################################################################
# SQL for database lock information
################################################################################
Function sql_locks {
     if ($DBVERSION -gt 121000) {
          $query_locks = @'
          prompt <<<oracle_locks:sep(124)>>>;
          select upper(vp.name)
               || '|' || b.sid
               || '|' || b.serial#
               || '|' || b.machine
               || '|' || b.program
               || '|' || b.process
               || '|' || b.osuser
               || '|' || b.username
               || '|' || b.SECONDS_IN_WAIT
               || '|' || b.BLOCKING_SESSION_STATUS
               || '|' || bs.inst_id
               || '|' || bs.sid
               || '|' || bs.serial#
               || '|' || bs.machine
               || '|' || bs.program
               || '|' || bs.process
               || '|' || bs.osuser
               || '|' || bs.username
          from v$session b
          join gv$session bs on bs.inst_id = b.BLOCKING_INSTANCE
               and bs.sid = b.BLOCKING_SESSION
               and bs.con_id = b.con_id
          join (
               SELECT vp.con_id,i.instance_name || '.' || vp.name name
               FROM v$containers vp
               JOIN v$instance i ON 1 = 1
               JOIN v$database d on 1=1
               WHERE d.cdb = 'YES' and vp.con_id <> 2
               UNION ALL
               SELECT 0, instance_name
               FROM v$instance
          ) vp on b.con_id = vp.con_id
          where b.BLOCKING_SESSION is not null;
          SELECT upper(i.instance_name || '.' || vp.name)
               || '|||||||||||||||||'
          FROM v$containers vp
          JOIN v$instance i ON 1 = 1
          JOIN v$database d on 1=1
          WHERE d.cdb = 'YES' and vp.con_id <> 2
          UNION ALL
          SELECT upper(i.instance_name)
               || '|||||||||||||||||'
          FROM v$instance i;

'@
          echo $query_locks
     }
     elseif ($DBVERSION -gt 102000) {
          $query_locks = @'
          select upper(i.instance_name)
               || '|' || b.sid
               || '|' || b.serial#
               || '|' || b.machine
               || '|' || b.program
               || '|' || b.process
               || '|' || b.osuser
               || '|' || b.username
               || '|' || b.SECONDS_IN_WAIT
               || '|' || b.BLOCKING_SESSION_STATUS
               || '|' || bs.inst_id
               || '|' || bs.sid
               || '|' || bs.serial#
               || '|' || bs.machine
               || '|' || bs.program
               || '|' || bs.process
               || '|' || bs.osuser
               || '|' || bs.username
          from v$session b
          join v$instance i on 1=1
          join gv$session bs on bs.inst_id = b.BLOCKING_INSTANCE
               and bs.sid = b.BLOCKING_SESSION
          where b.BLOCKING_SESSION is not null;
          select upper(i.instance_name)
               || '|||||||||||||||||'
          from v$instance i;

'@
          echo $query_locks
     }
}

Function sql_locks_old {
     if ($DBVERSION -gt 101000) {
          $query_locks = @'
          prompt <<<oracle_locks:sep(124)>>>;
          SET SERVEROUTPUT ON feedback off
          DECLARE
               type x is table of varchar2(20000) index by pls_integer;
               xx x;
          begin
               begin
                    execute immediate
                         'select upper(i.instance_name)
                              || ''|'' || a.sid
                              || ''|'' || b.serial#
                              || ''|'' || b.machine
                              || ''|'' || b.program
                              || ''|'' || b.process
                              || ''|'' || b.osuser
                              || ''|'' || a.ctime
                              || ''|'' || decode(c.owner,NULL,''NULL'',c.owner)
                              || ''|'' || decode(c.object_name,NULL,''NULL'',c.object_name)
                         from V$LOCK a, v$session b, dba_objects c, v$instance i
                         where (a.id1, a.id2, a.type)
                         IN (
                              SELECT id1, id2, type
                              FROM GV$LOCK
                              WHERE request>0
                         )
                         and request=0
                         and a.sid = b.sid
                         and a.id1 = c.object_id (+)
                         union all
                         select upper(i.instance_name) || ''|||||||||''
                         from  v$instance i'
                    bulk collect into xx;
                    if xx.count >= 1 then
                         for i in 1 .. xx.count loop
                              dbms_output.put_line(xx(i));
                         end loop;
                    end if;
               exception
                    when others then
                         for cur1 in (select upper(i.instance_name) instance_name from  v$instance i) loop
                              dbms_output.put_line(cur1.instance_name || '|||||||||'||sqlerrm);
                         end loop;
               end;
          END;
          /
          set serverout off

'@
          echo $query_locks
     }
}




################################################################################
# SQL for long active session information
################################################################################
Function sql_longactivesessions {
     if ($DBVERSION -gt 121000) {
          $query_longactivesessions = @'
          prompt <<<oracle_longactivesessions:sep(124)>>>;
          select upper(vp.name)
               || '|' || s.sid
               || '|' || s.serial#
               || '|' || s.machine
               || '|' || s.process
               || '|' || s.osuser
               || '|' || s.program
               || '|' || s.last_call_et
               || '|' || s.sql_id
          from v$session s
          join (
               SELECT vp.con_id
                    ,i.instance_name || '.' || vp.name name
               FROM v$containers vp
               JOIN v$instance i ON 1 = 1
               JOIN v$database d on 1=1
               WHERE d.cdb = 'YES' and vp.con_id <> 2
               UNION ALL
               SELECT 0, instance_name
               FROM v$instance
          ) vp on 1=1
          where s.status = 'ACTIVE'
               and s.type != 'BACKGROUND'
               and s.username is not null
               and s.username not in('PUBLIC')
               and s.last_call_et > 60*60;
          SELECT upper(i.instance_name || '.' || vp.name)
               || '||||||||'
          FROM v$containers vp
          JOIN v$instance i ON 1 = 1
          JOIN v$database d on 1=1
          WHERE d.cdb = 'YES' and vp.con_id <> 2
          UNION ALL
          SELECT upper(i.instance_name)
               || '||||||||'
          FROM v$instance i;

'@
          echo $query_longactivesessions
     }
     elseif ($DBVERSION -gt 101000) {
          $query_longactivesessions = @'
          prompt <<<oracle_longactivesessions:sep(124)>>>;
          select upper(i.instance_name)
               || '|' || s.sid
               || '|' || s.serial#
               || '|' || s.machine
               || '|' || s.process
               || '|' || s.osuser
               || '|' || s.program
               || '|' || s.last_call_et
               || '|' || s.sql_id
          from v$session s, v$instance i
          where s.status = 'ACTIVE'
               and type != 'BACKGROUND'
               and s.username is not null
               and s.username not in('PUBLIC')
               and s.last_call_et > 60*60
          union all
          select upper(i.instance_name)
               || '||||||||'
          from v$instance i;

'@
          echo $query_longactivesessions
     }
}





################################################################################
# SQL for sql_logswitches information
################################################################################
Function sql_asm_diskgroup {
     if ($DBVERSION -gt 112000) {
          $query_asm_diskgroup = @'
          prompt <<<oracle_asm_diskgroup:sep(124)>>>;
          select STATE
               || '|' || g.type
               || '|' || g.name
               || '|' || g.BLOCK_SIZE
               || '|' || g.ALLOCATION_UNIT_SIZE
               || '|' || g.REQUIRED_MIRROR_FREE_MB
               || '|' || sum(d.total_mb)
               || '|' || sum(d.free_mb)
               || '|' || d.failgroup
               || '|' || max(d.VOTING_FILE)
               || '|' || d.FAILGROUP_TYPE
               || '|' || g.offline_disks
               || '|' || min(decode(d.REPAIR_TIMER, 0, 8640000, d.REPAIR_TIMER))
               || '|' || count(*)
          FROM v$asm_diskgroup g
          LEFT OUTER JOIN v$asm_disk d on d.group_number = g.group_number
               and d.group_number = g.group_number
               and d.group_number <> 0
          GROUP BY g.name
               , g.state
               , g.type
               , d.failgroup
               , d.VOTING_FILE
               , g.BLOCK_SIZE
               , g.ALLOCATION_UNIT_SIZE
               , g.REQUIRED_MIRROR_FREE_MB
               , g.offline_disks
               , d.FAILGROUP_TYPE
               , d.REPAIR_TIMER
          ORDER BY g.name, d.failgroup;

'@
     }
     elseif ($DBVERSION -gt 101000) {
          $query_asm_diskgroup = @'
          prompt <<<oracle_asm_diskgroup:sep(124)>>>;
          select STATE
                     || '|' || TYPE
                     || '|' || 'N'
                     || '|' || sector_size
                     || '|' || block_size
                     || '|' || allocation_unit_size
                     || '|' || total_mb
                     || '|' || free_mb
                     || '|' || required_mirror_free_mb
                     || '|' || usable_file_mb
                     || '|' || offline_disks
                     || '|' || 'N'
                     || '|' || name || '/'
                from v$asm_diskgroup;

'@
     }
     echo $query_asm_diskgroup
}


#.
#   .--Main----------------------------------------------------------------.
#   |                        __  __       _                                |
#   |                       |  \/  | __ _(_)_ __                           |
#   |                       | |\/| |/ _` | | '_ \                          |
#   |                       | |  | | (_| | | | | |                         |
#   |                       |_|  |_|\__,_|_|_| |_|                         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Iterate over all instances and execute sync and async sections.     |
#   '----------------------------------------------------------------------'


#########################################################
# we now call all the functions to give us the SQL output
#########################################################
# get a list of all running Oracle Instances
$list_inst = (get-service -Name "Oracle*Service*" -include "OracleService*", "OracleASMService*" | Where-Object { $_.status -eq "Running" })


# the following line ensures that the output of the files generated by calling
# Oracle SQLplus through Powershell are not limited to 80 character width. The
# 80 character width limit is the default
$Host.UI.RawUI.BufferSize = New-Object Management.Automation.Host.Size (512, 150)

# We have to set some value for the ORACLE_SID, although here a nonsense value
# This value is used when we want to simply list all the banners
$NO_SID = "NO_SID"


if ( $SYNC_SECTIONS.count -gt 0) {
     foreach ($section in $SYNC_SECTIONS) {
          echo "<<<oracle_${section}>>>"
     }
}
if ( $ASYNC_SECTIONS.count -gt 0) {
     foreach ($section in $ASYNC_SECTIONS) {
          echo "<<<oracle_${section}>>>"
     }
}
if ( $SYNC_ASM_SECTIONS.count -gt 0) {
     foreach ($section in $SYNC_ASM_SECTIONS) {
          echo "<<<oracle_${section}>>>"
     }
}
if ( $ASYNC_ASM_SECTIONS.count -gt 0) {
     foreach ($section in $ASYNC_ASM_SECTIONS) {
          echo "<<<oracle_${section}>>>"
     }
}

$ORIG_SYNC_SECTIONS = $SYNC_SECTIONS
$ORIG_ASYNC_SECTIONS = $ASYNC_SECTIONS

# get a count of running instances to avoid next code if no instances are running
$the_count = ($list_inst | measure-object).count
# we only continue if an Oracle instance is running
if ($the_count -gt 0) {
     # loop through each instance
     ForEach ($inst in $list_inst) {
          # get the real instance name
          $inst.name = $inst.name.replace("OracleService", "")
          $inst_name = $inst.name.replace("OracleASMService", "")
          $ORACLE_SID = $inst_name
          $key = 'HKLM:\SYSTEM\CurrentControlSet\services\OracleService' + $ORACLE_SID
          $val = (Get-ItemProperty -Path $key).ImagePath
          $ORACLE_HOME = $val.SubString(0, $val.LastIndexOf('\') - 4)

          # reset errors found for this instance to zero
          $ERROR_FOUND = 0

          $DBVERSION = get_dbversion_database($ORACLE_HOME)
          debug_echo "value of inst_name= ${inst_name}"
          debug_echo "value of ORACLE_HOME= ${ORACLE_HOME}"
          debug_echo "value of DBVERSION database= ${DBVERSION}"
          # if this is an ASM instance, then switch sections to ASM
          $ASM_FIRST_CHAR = "+"
          $CHECK_FIRST_CHAR = $inst_name.Substring(0, 1)
          if ( $CHECK_FIRST_CHAR.compareTo($ASM_FIRST_CHAR) -eq 0 ) {
               $SYNC_SECTIONS = $SYNC_ASM_SECTIONS
               $ASYNC_SECTIONS = $ASYNC_ASM_SECTIONS
          }
          else {
               $SYNC_SECTIONS = $ORIG_SYNC_SECTIONS
               $ASYNC_SECTIONS = $ORIG_ASYNC_SECTIONS
          }

          # we presume we do not want to skip this instance
          $SKIP_INSTANCE = 0
          # check if $ONLY_SIDS is used
          if ( $ONLY_SIDS -ne $null) {
               # if used, then we presume we want to skip this instance
               $SKIP_INSTANCE = 1
               # if this SID is in our ONLY_SIDS then it will not be skipped
               if ($ONLY_SIDS -contains $inst_name) {
                    $SKIP_INSTANCE = 0
               }
          }
          if ($SKIP_INSTANCE -eq 0) {
               $THE_SQL = ""
               $THE_NEW_SQL = ""
               # call all function as defined in the $SYNC_SECTIONS, running synchronously
               if ( $SYNC_SECTIONS.count -gt 0) {
                    foreach ($section in $SYNC_SECTIONS) {
                         $the_section = "sql_" + $section
                         # we presume we do not want to skip this section
                         $SKIP_SECTION = 0


                         # if $EXCLUDE_SID is not used, then we will get an error here
                         # Powershell cannot really use dynamic variables, as a workaround we silently continue
                         # for this section of code
                         $ErrorActionPreference = "SilentlyContinue"
                         # check if $EXCLUDE_SID is used
                         if ("$EXCLUDE_$inst_name" -ne $null) {
                              # if used, then we at first presume that we do not want to skip this section
                              $SKIP_SECTION = 0
                              # if this SECTION is in our ONLY_SIDS then it will be skipped
                              if (((get-variable "EXCLUDE_$inst_name").value -contains "ALL") -or ((get-variable "EXCLUDE_$inst_name").value -contains $the_section)) {
                                   $SKIP_SECTION = 1
                              }
                         }
                         # now we set our action on error back to our normal value
                         $ErrorActionPreference = $NORMAL_ACTION_PREFERENCE
                         debug_echo "value of the_section = ${the_section}"
                         if ($SKIP_SECTION -eq 0) {
                              $THE_NEW_SQL = invoke-expression "${the_section}"
                              $THE_SQL = $THE_SQL + $THE_NEW_SQL
                         }
                    }
                    debug_echo "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX now calling multiple SQL"
                    $ERROR_FOUND = 0
                    if ($THE_SQL) {
                         sqlcall -sql_message "sync_SQLs" -sqltext "$THE_SQL" -run_async 0 -sqlsid $inst_name
                    }
               }

               if ($ERROR_FOUND -eq 0) {
                    # call all function as defined in the $ASYNC_SECTIONS, running asynchronously
                    $THE_SQL = " "
                    $THE_NEW_SQL = ""
                    if ( $ASYNC_SECTIONS.count -gt 0) {
                         foreach ($section in $ASYNC_SECTIONS) {
                              $the_section = "sql_" + $section
                              # we presume we do not want to skip this section
                              $SKIP_SECTION = 0
                              # if $EXCLUDE_SID is not used, then we will get an error here
                              # Powershell cannot really use dynamic variables, as a workaround we silently continue
                              # for this section of code
                              $ErrorActionPreference = "SilentlyContinue"
                              # check if $EXCLUDE_SID is used
                              if ("$EXCLUDE_$inst_name" -ne $null) {
                                   # if used, then we at first presume that we do not want to skip this section
                                   $SKIP_SECTION = 0
                                   # if this SECTION is in our ONLY_SIDS then it will be skipped
                                   # "dynamic variables" are not supported in powershell. For example, $inst_name holds the value of the oracle_sid, let's say "ORCL"
                                   # in powershell, I need to find the value of the variable EXCLUDE_ORCL, I cannot use "EXCLUDE_$inst_name" to reference that
                                   # and so I built the following workaround...
                                   if (((get-variable "EXCLUDE_$inst_name").value -contains "ALL") -or ((get-variable "EXCLUDE_$inst_name").value -contains $the_section)) {
                                        $SKIP_SECTION = 1
                                   }
                              }
                              # now we set our action on error back to our normal value
                              $ErrorActionPreference = $NORMAL_ACTION_PREFERENCE
                              if ($SKIP_SECTION -eq 0) {
                                   $THE_NEW_SQL = invoke-expression "$the_section"
                                   $THE_SQL = $THE_SQL + $THE_NEW_SQL
                              }
                         }
                         debug_echo "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX now calling multiple asyn SQL"
                         if ("$THE_SQL") {
                              sqlcall -sql_message "async_SQLs" -sqltext "$THE_SQL" -run_async 1 -sqlsid $inst_name
                         }
                    }
               }
          }
     }
     # We need an line break after last output from sections
     # otherwise the agent adds <<<local>>> as parameter to the last line of plugin
     echo ""

}
debug_echo "got to the end"


