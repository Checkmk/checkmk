# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# This agent plugin is meant to be used on a windows server which
# is running one or multiple MySQL server instances locally.

$CMK_VERSION = "2.5.0b4"

# Entries which assumed as safe during testing security permission check
# ----------------------------------------------------------------------
# Add to the list of entries which
# 1. May have write access to Mysql binaries
# 2. Are not Administrators
# Typical example: 'DOMAIN\DbInstaller' or 'MYPC\SpecialUser'
# For the case above you need to add $CURRENT_SAFE_ENTRIES = @("DOMAIN\\DbInstaller", "MYPC\\SpecialUser)
$CURRENT_SAFE_ENTRIES = @()
$SKIP_MYSQL_SECURITY_CHECK = 0

function Test-Administrator {
     return (([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator))
}
$is_admin = Test-Administrator


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

function CreateMysqlLocalIni {
    try {
        # The following logic exists as well in the linux bash script mk_mysql
        $cfgDir = GetCfgDir
        if (-not $cfgDir) {
            Write-Debug "CreateMysqlLocalIni failed: configuration directory not initialized"
            return
        }

        if (-not (Test-Path $cfgDir -PathType Container)) {
            Write-Debug "CreateMysqlLocalIni: configuration directory doesn't exist or is not a directory: $cfgDir"
            return
        }

        $mysqlLocalIni = Join-Path $cfgDir "mysql.local.ini"
        if (Test-Path $mysqlLocalIni) {
            Write-Debug "CreateMysqlLocalIni: $mysqlLocalIni file already exists, skipping creation"
            return
        }

        $content = "# This file is created by mk_mysql.ps1 because some versions of mysqladmin`n# issue a warning if there are missing includes."
        Set-Content -Path $mysqlLocalIni -Value $content -ErrorAction SilentlyContinue -ErrorVariable writeError

        if ($writeError) {
            Write-Debug "CreateMysqlLocalIni: failed to create file $mysqlLocalIni - $writeError"
            return
        }

        Write-Debug "CreateMysqlLocalIni: successfully created $mysqlLocalIni"
    }
    catch {
        Write-Debug "Exception in CreateMysqlLocalIni: $($_.Exception.Message)"
        return
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

<#
    .SYNOPSIS
        Checks that some sid is allowed
    .DESCRIPTION
        As for now allowed are 'Domain Admins' = 'S-1-5-32-512' and 'Enterprise Admins' 'S-1-5-32-519'.
        The reason: those groups must not be included in Administrators group but certainly are safe.
#>
function Test-DomainSid([string]$sid) {
     $domain_sid_pattern = "S-1-5-(.*)-51[2,9]"
     ($sid -match $domain_sid_pattern)[0]
     # TODO(sk): check whether domain is valid, matches[1] contains domain id
     # it is highly unlikely that domain id will mismatch
     # still we may check it, but in the future
}

<#
    .SYNOPSIS
        Checks that some entry is allowed to have write permission to the file.
    .DESCRIPTION
        Uses two lists of safe entries: CURRENT_SAFE_ENTRIES and WINDOWS_SAFE_ENTRIES where
        CURRENT_SAFE_ENTRIES is hardcoded in this script
        WINDOWS_SAFE_ENTRIES is generated by WATO
#>
function Test-SafeEntry([string]$entry) {
     $safe_entries = $CURRENT_SAFE_ENTRIES + $WINDOWS_SAFE_ENTRIES
     foreach ( $safe in $safe_entries ) {
          if (-not $safe ) {
               continue
          }
          if ( $entry.ToLower() -eq $safe.ToLower()) {
               return $True
          }
     }
     return $False
}

<#
    .SYNOPSIS
        Checks that file AND its parent folder are safe.
    .DESCRIPTION
        If non-admin users have Write, Modify or Full Control to the file
        OR the folder containing the file, returns error.
#>
function Invoke-SafetyCheck( [String]$file ) {
     # 1. Clean the input string (remove quotes)
     $file = $file.Trim('"')

     if (-not (Test-Path -path $file)) {
          return
     }

     # 2. Check both the file AND the parent folder
     $parentDir = Split-Path -Parent $file
     $pathsToCheck = @($file)
     if ($parentDir -and (Test-Path $parentDir)) {
         $pathsToCheck += $parentDir
     }

     $admin_sids = @(
          "S-1-5-18", # SYSTEM
          "S-1-5-32-544" # Administrators
     )
     $forbidden_rights = @("Modify", "FullControl", "Write")

     class Actor {
          [string]$name
          [string]$sid
          [string]$rights
     }

     foreach ($targetPath in $pathsToCheck) {
         try {
              $acl = Get-Acl $targetPath -ErrorAction Stop
              $access = $acl.Access
              $admins = Get-LocalGroupMember -SID "S-1-5-32-544"

              $actors = $access | ForEach-Object {
                   $a = [Actor]::new()
                   $object = New-Object System.Security.Principal.NTAccount -ArgumentList $_.IdentityReference
                   $a.name = $object
                   try {
                        $a.sid = $object.Translate([System.Security.Principal.SecurityIdentifier])
                        $a.rights = $_.FileSystemRights.ToString()
                        $a
                   }
                   catch {
                        # Silently skip translation errors
                   }
              }

              foreach ($entry in $actors ) {
                   $name = $entry.name
                   $sid = $entry.sid

                   # --- SAFEGUARDS ---

                   # 1. Check Predefined SIDs (System, Local Admin)
                   if ( $admin_sids -contains $sid ) { continue }

                   # 2. Check Name: TrustedInstaller
                   if ($name -match "TrustedInstaller") { continue }

                   # 3. Check Domain Admins
                   if (Test-DomainSid $sid) { continue }

                   # 4. Check Whitelist variable
                   if ( Test-SafeEntry $name ) { continue }

                   # 5. Check Local Admin Group Membership
                   if ( $admins.Name -contains "$name" ) { continue }

                   # --- PERMISSION CHECK ---
                   $rights = $entry.rights
                   $forbidden_rights |
                   Foreach-Object {
                        if ($rights -match $_) {
                             return "'$name' has '$_' access permissions on '$targetPath'"
                        }
                   }
              }
         }
         catch {
              return "Exception '$_' during check '$targetPath'"
         }
     }
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

    if ($is_admin -and ($SKIP_MYSQL_SECURITY_CHECK -ne 1)) {
        # administrators should use only safe binary
        $result = Invoke-SafetyCheck($cmd)
        if ($Null -ne $result) {
            Write-Output "<<<mysql>>>"
            Write-Output "Execution is blocked because: $result"
            exit
        }
    }


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
