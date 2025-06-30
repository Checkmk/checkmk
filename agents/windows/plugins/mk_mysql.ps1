# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# This agent plugin is meant to be used on a windows server which
# is running one or multiple MySQL server instances locally.

$CMK_VERSION = "2.5.0b1"

function Initialize {
    # Add here all the needed preparations
    CreateMysqlLocalIni
}

function DetectInstancesAndOutputInfo {
    $instances = @{}

    # Detect all local instances. We only add services of instances
    # which service is currently reported as running
    Get-CimInstance -Query "SELECT * FROM Win32_Service WHERE (Name LIKE '%MySQL%' or Name LIKE '%MariaDB%') and State = 'Running'" | ForEach-Object {
        $instances.Add($_.Name, $_.PathName)
    }

    foreach ($instance in $instances.Keys) {
        OutputInfosForTheInstance -instanceName $instance -instanceCmd $instances[$instance]
    }
}

function Run {
    param (
        [string]$cmdCommand
    )
    cmd.exe /s /c $cmdCommand
}

function ReplaceSqlExeForMysql {
    param (
        [string]$cmd
    )
    return $cmd -replace "mysqld(?:-nt)?\.exe", "mysql.exe"
}

function BuildPrintDefaultsCmd {
    param (
        [string]$instanceName,
        [string]$instanceCmd
    )
    $printDefaultsCmd = $instanceCmd -replace "\s+$instanceName.*", " --print-defaults"
    return $printDefaultsCmd
}

function GetSqlExePathFromCmd {
    param (
        [string]$inputCmd
    )

    if ($inputCmd -match '("[^"]*mysql.exe")') {
        $exePath = $matches[1]
    }
    elseif ($inputCmd -match '([^"]*mysql.exe)') {
        $exePath = $matches[1]
    }

    return $exePath
}

function GetCfgDir {
    return $env:MK_CONFDIR
}

function InitCfgFile {
    param (
        [string]$instanceName
    )
    # Use either an instance specific config file named mysql_<instance-id>.ini
    # or the default mysql.ini file.
    $cfgDir = GetCfgDir
    $possiblePaths = @(
        Join-Path $cfgDir "mysql_$instanceName.ini"
        Join-Path $cfgDir "mysql.ini"
    )

    $cfgFile = ""
    foreach ($path in $possiblePaths) {
        if (Test-Path $path) {
            $cfgFile = $path
            break
        }
    }

    return $cfgFile
}

function CreateMysqlLocalIni {
    # The following logic exists as well in the linux bash script mk_mysql
    $cfgDir = GetCfgDir
    if ($cfgDir) {
        $mysqlLocalIni = Join-Path $cfgDir "mysql.local.ini"
        if (-Not (Test-Path $mysqlLocalIni)) {
            Set-Content -Path $mysqlLocalIni -Value "# This file is created by mk_mysql.ps1 because some versions of mysqladmin`n# issue a warning if there are missing includes."
        }
    }
    else {
        Write-Error "CreateMysqlLocalIni: configuration directory is not properly initialized"
    }
}

function GetConnectionArgsForTheInstance {
    param (
        [string]$instanceName,
        [string]$instanceCmd
    )
    # Now detect the correct socket / port to connect to this instance. This can be done by executing
    # mysql.exe with the --defaults-file found in the command line of the windows process together
    # with the option --print-defaults
    $output = & Run (BuildPrintDefaultsCmd $instanceName $instanceCmd)
    $connArgs = $output -split "`r`n" | Select-Object -Last 1

    if ($connArgs -match "(--port=\d+)") {
        $connArgs = $matches[1]
    }
    else {
        $connArgs = ""
    }

    return $connArgs
}

function OutputInfosForTheInstance {
    param (
        [string]$instanceName,
        [string]$instanceCmd
    )

    # Now we try to construct a mysql.exe client command which is able to connect to this database
    # based on the command uses by the database service.
    # In our development setup, where MySQL 5.6 has been used, the server command is:
    # "C:\Programme\MySQL\MySQL Server 5.6\bin\mysqld.exe" --defaults-file="C:\Dokumente und Einstellungen\All Users\Anwendungsdaten\MySQL\MySQL Server 5.6\my.ini" MySQL56
    # To get the client command we simply need to replace mysqld.exe with mysql.exe, remove the
    # my.ini and instance name from the end of the command and add our config as --defaults-extra-file.

    $cfgFile = InitCfgFile $instanceName
    $replacedInstanceCmd = ReplaceSqlExeForMysql $instanceCmd
    $connArgs = GetConnectionArgsForTheInstance $instanceName $replacedInstanceCmd
    $cmd = GetSqlExePathFromCmd $replacedInstanceCmd

    if ($cfgFile -ne "") {
        $cmd += " --defaults-extra-file=`"$cfgFile`""
    }

    $cmd += " $connArgs"

    Write-Output "<<<mysql_ping>>>"
    Write-Output "[[$instanceName]]"
    Run "$($cmd -replace "mysql.exe", "mysqladmin.exe") ping"

    Write-Output "<<<mysql>>>"
    Write-Output "[[$instanceName]]"
    Run "$cmd -B -sN -e `"show global status ; show global variables ;`""

    Write-Output "<<<mysql_capacity>>>"
    Write-Output "[[$instanceName]]"
    Run "$cmd -B -sN -e `"SELECT table_schema, sum(data_length + index_length), sum(data_free) FROM information_schema.TABLES GROUP BY table_schema`""

    Write-Output "<<<mysql_slave>>>"
    Write-Output "[[$instanceName]]"
    Run "$cmd -B -s -e `"show slave status\G`""
}

Initialize
DetectInstancesAndOutputInfo
