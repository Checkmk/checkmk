$CMK_VERSION = "2.0.0b6"
## filename for timestamp

$MK_CONFDIR = $env:MK_CONFDIR
## Fallback if the (old) agent does not provide the MK_CONFDIR
if (!$MK_CONFDIR) {
    $MK_CONFDIR = "C:\ProgramData\checkmk\agent\config"
}

function PathFromServicePathName($pathName) {
    if ($pathName.StartsWith("`"")) {
        $pathName = $pathName.Substring(1)
        $index = $pathName.IndexOf("`"")
        if ($index -gt -1) {
            return $pathName.Substring(0, $index)
        }
        else {
            return $pathName
        }
    }
    if ($pathName.Contains(".exe")) {
        $index = $pathName.IndexOf(".exe")
        return $pathName.Substring(0, $index + 4)
    }
    return
}

$CONFIG_FILE = "$MK_CONFDIR\mysql.ini"
if (Test-Path -path "$CONFIG_FILE" ) {
    $servicepathname = (Get-WmiObject win32_service | Where-Object { ($_.Name -like '*MySQL*' -or $_.Name -like '*MariaDB*') } | Select-Object PathName).PathName
    $path = PathFromServicePathName($servicepathname)
    $path = (Split-Path -Path ($path))
    Set-Location $path
    if (Test-Path -path "$path\mysqladmin.exe") {
        Write-Host "<<<mysql_ping>>>"
        .\mysqladmin.exe --defaults-extra-file="$CONFIG_FILE" ping
        if (Test-Path -path "$path\mysql.exe") {
            Write-Host "<<<mysql>>>"
            .\mysql.exe --defaults-extra-file="$CONFIG_FILE" -B -sN -e "show global status; show global variables;"
            Write-Host "<<<mysql_capacity>>>"
            .\mysql.exe --defaults-extra-file="$CONFIG_FILE" -B -sN -e "SELECT table_schema, sum(data_length + index_length), sum(data_free) FROM information_schema.TABLES GROUP BY table_schema;"
            Write-Host "<<<mysql_slave>>>"
            .\mysql.exe --defaults-extra-file="$CONFIG_FILE" -B -s -e "show slave status\G"
        } else { exit }
    } else { exit }
} else { exit }