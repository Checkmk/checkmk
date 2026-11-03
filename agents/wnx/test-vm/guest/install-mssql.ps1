# Guest-side: install SQL Server 2022 Developer with the three instances
# the mk-sql Windows-local tests expect (packages/mk-sql/tests in
# checkmk), from the Developer media (RTM, 16.0.1000.6) on a CD drive and
# the offline payload make_image.py copies to -Payload:
#
#   cu\SQLServer2022-KB*-x64.exe     latest CU, slipstreamed into each run
#   msodbcsql17.msi                  ODBC Driver 17 x64 (32- and 64-bit)
#
# One setup run per instance, all from the same media and one ini
# template (FEATURES=SQLENGINE only):
#
#   MSSQLSERVER       default instance, TCP static 1433
#   SQLEXPRESS_NAME   named, INSTANCEID=SQLEXPRESS_ID (ID differs from the
#                     name on purpose: the tests check that mk-sql maps it)
#   SQLEXPRESS_WOW    named (64-bit now; the name is what the tests match)
#
# The named instances listen on dynamic TCP ports and are found through
# SQL Browser (Automatic). Every instance: TCP enabled, mixed mode (sa
# password below), BUILTIN\Administrators and the local Administrator
# (the account the test runner uses, Windows auth) as sysadmin, engine
# service Automatic (not delayed, see below), max server memory capped
# (-MaxMemoryMB), Agent
# Manual and the CEIP telemetry service Disabled (neither is used by the
# tests, both would cost memory in every saved VM state).
#
# Exits non-zero on the first failed setup run; the setup logs are under
# C:\Program Files\Microsoft SQL Server\160\Setup Bootstrap\Log. A run
# that asks for a reboot (3010) stops it early, with
# $Payload\reboot-required: SQL Server setup refuses to run with a reboot
# pending, and so would the component store cleanup after this. make_image.py
# then cold boots and calls it again, and it skips the instances that are
# installed.
param(
    [string]$Payload = 'C:\setup\mssql',
    # Max server memory of every instance: make_image.py passes the value
    # verify-image.ps1 checks.
    [Parameter(Mandatory)][int]$MaxMemoryMB,
    # sa password (mixed mode needs one): make_image.py passes the test
    # image's Administrator password (PASSWORD, qemu_windows/guest.py).
    [Parameter(Mandatory)][string]$SaPassword
)
$ErrorActionPreference = 'Stop'

$Instances = @(
    @{ Name = 'MSSQLSERVER'; Id = 'MSSQLSERVER' },
    @{ Name = 'SQLEXPRESS_NAME'; Id = 'SQLEXPRESS_ID' },
    @{ Name = 'SQLEXPRESS_WOW'; Id = 'SQLEXPRESS_WOW' }
)

$cuDir = Join-Path $Payload 'cu'
$odbc = Join-Path $Payload 'msodbcsql17.msi'
foreach ($f in $cuDir, $odbc) {
    if (-not (Test-Path $f)) { throw "payload incomplete: $f not found" }
}

$sw = [Diagnostics.Stopwatch]::StartNew()
# The CD drive's letter may come a moment after the logon.
foreach ($try in 1..15) {
    $media = Get-Volume | Where-Object { $_.DriveType -eq 'CD-ROM' -and $_.DriveLetter -and
        (Test-Path "$($_.DriveLetter):\setup.exe") } | Select-Object -First 1
    if ($media) { break }
    Start-Sleep 2
}
if (-not $media) { throw 'no CD drive with the SQL Server media (setup.exe)' }
$setup = "$($media.DriveLetter):\setup.exe"
Write-Output "media at $($media.DriveLetter):, edition PID from its DefaultSetup.ini (Developer)"

$installed = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Microsoft SQL Server\Instance Names\SQL' -ErrorAction SilentlyContinue
$missing = @($Instances | Where-Object { -not ($installed -and $installed.PSObject.Properties[$_.Name]) })
foreach ($i in $Instances | Where-Object { $missing -notcontains $_ }) {
    Write-Output "instance $($i.Name) already installed"
}
for ($n = 0; $n -lt $missing.Count; $n++) {
    $i = $missing[$n]
    $name = $i.Name
    $ini = Join-Path $Payload "$name.ini"
    # One quoted value per sysadmin account, space separated.
    @"
[OPTIONS]
ACTION="Install"
FEATURES=SQLENGINE
INSTANCENAME="$name"
INSTANCEID="$($i.Id)"
SQLSVCSTARTUPTYPE="Automatic"
AGTSVCSTARTUPTYPE="Manual"
SQLTELSVCSTARTUPTYPE="Disabled"
BROWSERSVCSTARTUPTYPE="Automatic"
SQLSYSADMINACCOUNTS="BUILTIN\Administrators" "$env:COMPUTERNAME\Administrator"
SECURITYMODE="SQL"
TCPENABLED="1"
NPENABLED="0"
SQLMINMEMORY="0"
SQLMAXMEMORY="$MaxMemoryMB"
SQLTEMPDBFILECOUNT="1"
UPDATEENABLED="True"
UPDATESOURCE="$cuDir"
SUPPRESSPRIVACYSTATEMENTNOTICE="True"
IACCEPTSQLSERVERLICENSETERMS="True"
QUIET="True"
INDICATEPROGRESS="False"
"@ | Set-Content -Path $ini -Encoding ASCII
    $t0 = $sw.Elapsed.TotalSeconds
    Write-Output "installing instance $name (ID $($i.Id))..."
    # The sa password goes on the command line, not into the ini.
    $p = Start-Process -FilePath $setup -Wait -PassThru -NoNewWindow -ArgumentList `
        "/ConfigurationFile=`"$ini`"", "/SAPWD=`"$SaPassword`""
    Write-Output ("{0}: setup exit code {1} after {2:N0} s" -f $name, $p.ExitCode, ($sw.Elapsed.TotalSeconds - $t0))
    if ($p.ExitCode -ne 0 -and $p.ExitCode -ne 3010) {
        $summary = 'C:\Program Files\Microsoft SQL Server\160\Setup Bootstrap\Log\Summary.txt'
        if (Test-Path $summary) { Get-Content $summary | Select-Object -First 60 }
        throw "SQL Server setup for $name failed with exit code $($p.ExitCode)"
    }
    # 3010: success, reboot required, also after the last instance: the
    # rest of this script then runs after the cold boot.
    if ($p.ExitCode -eq 3010) {
        Write-Output "$name asks for a reboot"
        New-Item -ItemType File -Force (Join-Path $Payload 'reboot-required') | Out-Null
        exit 0
    }
}

# Setup registers the engines as Automatic (Delayed Start): after a cold
# boot they come up only ~2 min after the other services, which the
# verification in make_image.py (right after the cold boot) would race.
# Plain Automatic: sc.exe clears the delayed flag with start= auto.
foreach ($svc in 'MSSQLSERVER', 'MSSQL$SQLEXPRESS_NAME', 'MSSQL$SQLEXPRESS_WOW') {
    sc.exe config $svc start= auto | Out-Null
    if ((Get-ItemProperty "HKLM:\SYSTEM\CurrentControlSet\Services\$svc").DelayedAutostart -ne 0) {
        throw "${svc}: could not switch from delayed to plain automatic start"
    }
}

# After the setup runs: they install their own (older) ODBC Driver 17 as a
# prerequisite, which this MajorUpgrade replaces. The x64 package
# registers the 32-bit driver too, which mk-sql looks up
# (Get-OdbcDriver ... -Platform 32-Bit, src/platform.rs).
Write-Output "installing $(Split-Path -Leaf $odbc)..."
$p = Start-Process -FilePath msiexec.exe -Wait -PassThru -ArgumentList `
    '/i', "`"$odbc`"", '/qn', '/norestart', 'IACCEPTMSODBCSQLLICENSETERMS=YES'
Write-Output "msiexec exit code $($p.ExitCode)"
if ($p.ExitCode -ne 0 -and $p.ExitCode -ne 3010) {
    throw "ODBC driver install failed with exit code $($p.ExitCode)"
}

Get-Service MSSQLSERVER, 'MSSQL$SQLEXPRESS_NAME', 'MSSQL$SQLEXPRESS_WOW', SQLBrowser,
SQLSERVERAGENT, 'SQLAgent$SQLEXPRESS_NAME', 'SQLAgent$SQLEXPRESS_WOW' |
    Format-Table -AutoSize Name, Status, StartType | Out-String -Width 120
Get-OdbcDriver -Name '* SQL Server' | Format-Table -AutoSize Name, Platform | Out-String -Width 120
Write-Output ("SQL Server installed in {0:N0} s" -f $sw.Elapsed.TotalSeconds)
