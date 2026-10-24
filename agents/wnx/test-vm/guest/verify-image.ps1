# Guest-side state verification for make_image.py: everything the test
# tiers rely on must hold before the image is published. Runs in its
# verification boot, with the device set the tests use, as the
# Administrator in the console session (qemu_windows/session.py), as the
# tests do.
# -SqlVersion: the SQL Server build (RTM + CU) every instance must run;
# -SqlMaxMemoryMB: their max server memory. make_image.py passes both from
# its MSSQL_* settings.
param(
    [Parameter(Mandatory)][string]$SqlVersion,
    [Parameter(Mandatory)][int]$SqlMaxMemoryMB
)
$failures = @()
$InstallationType = (Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion').InstallationType
Write-Output "InstallationType: $InstallationType"
if ($InstallationType -ne 'Server Core') {
    $failures += "InstallationType is '$InstallationType', expected Server Core"
}

if (-not ((bcdedit | Select-String testsigning) -match 'Yes')) {
    $failures += 'testsigning not enabled'
}
# The guest agent (first-logon.ps1 steps 1-2): its virtio-serial port with
# the vioser driver, and qemu-ga, started automatically. (That it answers,
# make_image.py has seen.)
$port = @(Get-PnpDevice -PresentOnly -InstanceId 'PCI\VEN_1AF4&DEV_1003*' -ErrorAction SilentlyContinue)
if ($port.Count -ne 1 -or $port[0].Status -ne 'OK' -or $port[0].Service -ne 'VirtioSerial') {
    $failures += "virtio-serial device is [$(($port | ForEach-Object { "$($_.Service) $($_.Status)" }) -join ', ')], expected one VirtioSerial OK"
}
$qga = Get-Service QEMU-GA -ErrorAction SilentlyContinue
if (-not $qga -or $qga.Status -ne 'Running' -or $qga.StartType -ne 'Automatic') {
    $failures += "QEMU-GA service is $($qga.Status)/$($qga.StartType), expected Running/Automatic"
}
# Its event source in a log of its own (step 2a), not in the Application
# log that the regression suite's event log tests count.
$qgaLog = [Diagnostics.EventLog]::LogNameFromSourceName('qemu-ga', '.')
if ($qgaLog -ne 'qemu-ga') {
    $failures += "qemu-ga event source is in the log '$qgaLog', expected 'qemu-ga'"
}
# The serial console (step 3): EMS on COM1 at 115200 baud.
$ems = (bcdedit /enum '{current}') + (bcdedit /enum '{emssettings}')
foreach ($setting in '^ems\s+Yes$', '^emsport\s+1$', '^emsbaudrate\s+115200$') {
    if (-not ($ems -match $setting)) { $failures += "boot configuration lacks '$setting' (EMS)" }
}
if ((tzutil /g) -ne 'W. Europe Standard Time') {
    $failures += "timezone is '$(tzutil /g)', expected W. Europe Standard Time"
}
$adapterStates = (Get-NetAdapter).Status
if (-not ($adapterStates -contains 'Up' -and $adapterStates -contains 'Disconnected')) {
    $failures += "adapters are [$($adapterStates -join ', ')], need one Up and one Disconnected"
}
# The Up adapter is the hostfwd one (net0): it must hold slirp's 10.0.2.15
# as a usable address, not a duplicate/APIPA fallback. Windows' "Ethernet"
# names do not follow QEMU device order, so select by status.
$up = Get-NetAdapter | Where-Object Status -EQ 'Up'
$v4 = Get-NetIPAddress -AddressFamily IPv4 -InterfaceIndex $up.ifIndex -ErrorAction SilentlyContinue
if (-not ($v4 | Where-Object { $_.IPAddress -eq '10.0.2.15' -and $_.AddressState -eq 'Preferred' })) {
    $failures += "Up adapter has [$(($v4 | ForEach-Object { "$($_.IPAddress)/$($_.AddressState)" }) -join ', ')], expected 10.0.2.15/Preferred"
}
if (-not ((query session) -match 'console.*Active')) {
    $failures += 'no active interactive console session (autologon)'
}
# Exactly $false: a cmdlet that fails, or returns nothing, is no pass.
try { $autoLaunch = (Get-SConfig -ErrorAction Stop).AutoLaunch }
catch { $autoLaunch = "unknown ($($_.Exception.Message))" }
if ($autoLaunch -ne $false) {
    $failures += "SConfig AutoLaunch is '$autoLaunch', expected False"
}
if (-not (Test-Path 'HKLM:\SYSTEM\CurrentControlSet\Control\Network\NewNetworkWindowOff')) {
    $failures += 'new-network flyout not suppressed (NewNetworkWindowOff key missing)'
}
# Microsoft Defender Antivirus removed (first-logon.ps1 step 4): the
# feature with its payload (Removed, not just Available), its service
# and engine, and its scheduled tasks.
$wd = Get-WindowsFeature -Name Windows-Defender
if ($wd.InstallState -ne 'Removed') {
    $failures += "Windows-Defender feature is $($wd.InstallState), expected Removed"
}
if (Get-Service WinDefend -ErrorAction SilentlyContinue) {
    $failures += 'WinDefend service still exists'
}
if (Get-Process MsMpEng -ErrorAction SilentlyContinue) {
    $failures += 'MsMpEng.exe is running'
}
$wdTasks = @(Get-ScheduledTask -TaskPath '\Microsoft\Windows\Windows Defender\' -ErrorAction SilentlyContinue)
if ($wdTasks.Count -gt 0) {
    $failures += "Defender scheduled tasks still exist: $($wdTasks.TaskName -join ', ')"
}
Write-Output "Defender: feature $($wd.InstallState), $($wdTasks.Count) scheduled tasks"

# NGEN queue flushed (make_image.py, before the shutdown for the
# compressed copy). Asked again after that cold boot, ngen must have
# nothing left to compile. (The "Critical" tasks' state says nothing: they
# stay Ready until their idle trigger first fires, queue empty or not.)
foreach ($fw in 'Framework64', 'Framework') {
    $out = & "$env:windir\Microsoft.NET\$fw\v4.0.30319\ngen.exe" executeQueuedItems /nologo 2>&1
    if (-not ($out -match 'All compilation targets are up to date')) {
        $failures += "NGEN ($fw) still had queued work: $(@($out)[0])"
    }
}

# Fixed 256 MB pagefile (first-logon.ps1 step 6a), in effect since the
# reboot. It must exist: watest's FileInfoTest.MakeFileInfoPagefile.
if ((Get-CimInstance Win32_ComputerSystem).AutomaticManagedPagefile) {
    $failures += 'pagefile is still system-managed'
}
$pfu = @(Get-CimInstance Win32_PageFileUsage)
if ($pfu.Count -ne 1 -or $pfu[0].Name -ne 'C:\pagefile.sys' -or $pfu[0].AllocatedBaseSize -ne 256) {
    $failures += "pagefile is [$(($pfu | ForEach-Object { "$($_.Name) $($_.AllocatedBaseSize) MB" }) -join ', ')], expected C:\pagefile.sys 256 MB"
}

# SQL Server 2022 Developer, three instances (install-mssql.ps1), as the
# mk-sql Windows-local tests expect them: names and IDs in the registry,
# TCP enabled, MSSQLSERVER on static 1433, the named instances on dynamic
# ports behind SQL Browser, and this account (Administrator, as the test
# runner) a sysadmin over Windows auth on all three.
$sqlExpected = [ordered]@{
    'MSSQLSERVER'     = 'MSSQL16.MSSQLSERVER'
    'SQLEXPRESS_NAME' = 'MSSQL16.SQLEXPRESS_ID'
    'SQLEXPRESS_WOW'  = 'MSSQL16.SQLEXPRESS_WOW'
}
$sqlKey = 'HKLM:\SOFTWARE\Microsoft\Microsoft SQL Server'
$names = Get-ItemProperty "$sqlKey\Instance Names\SQL" -ErrorAction SilentlyContinue
$registered = @($names.PSObject.Properties | Where-Object Name -NotLike 'PS*' |
        ForEach-Object { "$($_.Name)=$($_.Value)" })
$wanted = @($sqlExpected.Keys | ForEach-Object { "$_=$($sqlExpected[$_])" })
# Compare-Object refuses an empty list (Windows PowerShell 5.1).
if ($registered.Count -eq 0 -or (Compare-Object $registered $wanted)) {
    $failures += "SQL instances registered as [$($registered -join ', ')], expected [$($wanted -join ', ')]"
}
$sqlServices = @('MSSQLSERVER', 'MSSQL$SQLEXPRESS_NAME', 'MSSQL$SQLEXPRESS_WOW', 'SQLBrowser')
# They start with the other automatic services, so possibly after the
# guest agent: give them a minute before judging. The engines must not be on delayed
# start (install-mssql.ps1 switches setup's default off): that would
# leave them stopped for ~2 min after every cold boot.
$sqlWait = [Diagnostics.Stopwatch]::StartNew()
while ($sqlWait.Elapsed.TotalSeconds -lt 60 -and
    @(Get-Service $sqlServices -ErrorAction SilentlyContinue | Where-Object Status -EQ 'Running').Count -lt $sqlServices.Count) {
    Start-Sleep 2
}
foreach ($svc in $sqlServices) {
    $s = Get-Service $svc -ErrorAction SilentlyContinue
    if ($svc -ne 'SQLBrowser' -and
        (Get-ItemProperty "HKLM:\SYSTEM\CurrentControlSet\Services\$svc" -ErrorAction SilentlyContinue).DelayedAutostart -ne 0) {
        $failures += "service $svc is on delayed start"
    }
    if (-not $s -or $s.Status -ne 'Running' -or $s.StartType -ne 'Automatic') {
        $failures += "service $svc is $($s.Status)/$($s.StartType), expected Running/Automatic"
    }
}
# Agent Manual and the CEIP telemetry service Disabled (install-mssql.ps1):
# neither is used by the tests, both would cost memory in every saved state.
foreach ($name in $sqlExpected.Keys) {
    $suffix = if ($name -eq 'MSSQLSERVER') { '' } else { "`$$name" }
    $agent = if ($name -eq 'MSSQLSERVER') { 'SQLSERVERAGENT' } else { "SQLAgent$suffix" }
    foreach ($svc in @(@($agent, 'Manual'), @("SQLTELEMETRY$suffix", 'Disabled'))) {
        $s = Get-Service $svc[0] -ErrorAction SilentlyContinue
        if (-not $s -or $s.StartType -ne $svc[1]) {
            $failures += "service $($svc[0]) StartType is $($s.StartType), expected $($svc[1])"
        }
    }
}
foreach ($name in $sqlExpected.Keys) {
    $id = $sqlExpected[$name]
    $tcp = "$sqlKey\$id\MSSQLServer\SuperSocketNetLib\Tcp"
    if ((Get-ItemProperty $tcp -ErrorAction SilentlyContinue).Enabled -ne 1) {
        $failures += "${name}: TCP not enabled"
    }
    $ipAll = Get-ItemProperty "$tcp\IPAll" -ErrorAction SilentlyContinue
    if ($name -eq 'MSSQLSERVER') {
        if ($ipAll.TcpPort -ne '1433') { $failures += "${name}: TcpPort is '$($ipAll.TcpPort)', expected 1433" }
    }
    elseif ($ipAll.TcpPort -or -not $ipAll.TcpDynamicPorts) {
        $failures += "${name}: TcpPort '$($ipAll.TcpPort)' / TcpDynamicPorts '$($ipAll.TcpDynamicPorts)', expected a dynamic port only"
    }
    # Default instance by its port, the named ones by name, which the
    # client resolves through SQL Browser (UDP 1434). tcp: forces TCP, not
    # shared memory. Integrated Security: this session's Administrator.
    $server = if ($name -eq 'MSSQLSERVER') { 'tcp:127.0.0.1,1433' } else { "tcp:localhost\$name" }
    $conn = New-Object System.Data.SqlClient.SqlConnection "Server=$server;Integrated Security=SSPI;Connect Timeout=30"
    try {
        $conn.Open()
        $cmd = $conn.CreateCommand()
        $cmd.CommandText = @"
SELECT ISNULL(CAST(SERVERPROPERTY('InstanceName') AS nvarchar(128)), 'MSSQLSERVER'),
       CAST(SERVERPROPERTY('ProductVersion') AS nvarchar(128)),
       CAST(SERVERPROPERTY('Edition') AS nvarchar(128)),
       CAST(SERVERPROPERTY('IsIntegratedSecurityOnly') AS int),
       SUSER_SNAME(),
       IS_SRVROLEMEMBER('sysadmin', SUSER_SNAME()),
       (SELECT CAST(value_in_use AS int) FROM sys.configurations WHERE name = 'max server memory (MB)'),
       (SELECT net_transport FROM sys.dm_exec_connections WHERE session_id = @@SPID),
       (SELECT local_tcp_port FROM sys.dm_exec_connections WHERE session_id = @@SPID)
"@
        $r = $cmd.ExecuteReader()
        [void]$r.Read()
        $row = 0..8 | ForEach-Object { $r.GetValue($_) }
        $r.Close()
        Write-Output ("SQL {0}: {1} {2}, login {3} (sysadmin {4}), max server memory {5} MB, {6} port {7}" -f
            $row[0], $row[1], $row[2], $row[4], $row[5], $row[6], $row[7], $row[8])
        if ($row[0] -ne $name) { $failures += "${name}: connected to instance '$($row[0])'" }
        if ($row[1] -ne $SqlVersion) { $failures += "${name}: version $($row[1]), expected $SqlVersion" }
        if ($row[2] -notlike 'Developer Edition*') { $failures += "${name}: edition '$($row[2])', expected Developer" }
        if ($row[3] -ne 0) { $failures += "${name}: Windows authentication only, expected mixed mode" }
        if ($row[4] -ne "$env:COMPUTERNAME\Administrator" -or $row[5] -ne 1) {
            $failures += "${name}: login $($row[4]) sysadmin=$($row[5]), expected $env:COMPUTERNAME\Administrator as sysadmin"
        }
        if ($row[6] -ne $SqlMaxMemoryMB) { $failures += "${name}: max server memory $($row[6]) MB, expected $SqlMaxMemoryMB" }
        if ($row[7] -ne 'TCP') { $failures += "${name}: connected over $($row[7]), expected TCP" }
        # The Administrator login itself, not only via BUILTIN\Administrators.
        $cmd.CommandText = "SELECT IS_SRVROLEMEMBER('sysadmin', N'$env:COMPUTERNAME\Administrator')"
        if ($cmd.ExecuteScalar() -ne 1) { $failures += "${name}: $env:COMPUTERNAME\Administrator is not a sysadmin login" }
    }
    catch {
        $failures += "${name}: cannot connect to $server with Windows auth: $($_.Exception.Message)"
    }
    finally {
        $conn.Close()
    }
}
# mk-sql picks its ODBC driver with Get-OdbcDriver -Name '* SQL Server'
# -Platform 32-Bit (src/platform.rs), so a 32-bit registration must exist.
$odbc32 = @(Get-OdbcDriver -Name '* SQL Server' -Platform 32-Bit -ErrorAction SilentlyContinue)
$odbc64 = @(Get-OdbcDriver -Name '* SQL Server' -Platform 64-Bit -ErrorAction SilentlyContinue)
Write-Output "ODBC drivers: 32-bit [$($odbc32.Name -join ', ')], 64-bit [$($odbc64.Name -join ', ')]"
if (-not ($odbc32.Name -contains 'ODBC Driver 17 for SQL Server') -or
    -not ($odbc64.Name -contains 'ODBC Driver 17 for SQL Server')) {
    $failures += 'ODBC Driver 17 for SQL Server not registered for both 32 and 64 bit'
}

# Time and account settings the saved VM states rely on (first-logon.ps1
# steps 7a, 7a2): the RTC read as UTC, w32time running (the agent's w32time
# sections), no password expiry.
$tzi = Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\TimeZoneInformation'
if ($tzi.RealTimeIsUniversal -ne 1) {
    $failures += 'RealTimeIsUniversal is not 1'
}
if ((Get-Service w32time).Status -ne 'Running') {
    $failures += "w32time is $((Get-Service w32time).Status), expected Running"
}
if ((Get-LocalUser Administrator).PasswordExpires) {
    $failures += "Administrator password expires $((Get-LocalUser Administrator).PasswordExpires)"
}

# Windows Update (the answer file, first-logon.ps1 step 5): no automatic
# updates, the service available on demand for the windows_updates.ps1
# Pester suite.
if ((Get-ItemProperty 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU' -ErrorAction SilentlyContinue).NoAutoUpdate -ne 1) {
    $failures += 'Windows Update policy NoAutoUpdate is not 1'
}
if ((Get-Service wuauserv).StartType -ne 'Manual') {
    $failures += "wuauserv StartType is $((Get-Service wuauserv).StartType), expected Manual"
}
# Nor did it download or install anything during the build: updates it
# downloaded would install in a test VM, at any later boot.
$wuDownloads = @(Get-ChildItem C:\Windows\SoftwareDistribution\Download -Recurse -File -ErrorAction SilentlyContinue)
if ($wuDownloads.Count) {
    $failures += "Windows Update downloaded $($wuDownloads.Count) files during the build"
}
# 19/20: installed or failed, 43: install started, 44: download started.
$wuEvents = @(Get-WinEvent -FilterHashtable @{ LogName = 'System'; ProviderName = 'Microsoft-Windows-WindowsUpdateClient'; Id = 19, 20, 43, 44 } -ErrorAction SilentlyContinue)
if ($wuEvents.Count) {
    $failures += "Windows Update downloaded or installed updates during the build: $(($wuEvents | Select-Object -First 3 | ForEach-Object { $_.Message }) -join ' / ')"
}

# The volume the agent tests read (first-logon.ps1 step 7b3, the answer
# file): a label the regression suite's df test matches with \w+, and
# C: mounted at C:\mnt\c, without which watest's
# DfTest.ProduceMountPointsOutput skips.
$cVolume = Get-Volume -DriveLetter C
if ($cVolume.FileSystemLabel -notmatch '^\w+$') {
    $failures += "C: label is '$($cVolume.FileSystemLabel)', expected a \w+ label"
}
$mounted = (mountvol C:\mnt\c /L 2>$null | Out-String).Trim()
if ($mounted -ne $cVolume.Path) {
    $failures += "C:\mnt\c mounts '$mounted', expected the C: volume $($cVolume.Path)"
}

# No provisioning leftovers (make_image.py removes C:\setup before the TRIM).
if (Test-Path C:\setup) {
    $failures += 'C:\setup still exists'
}

# The Eval licence: activated, with the expiry make_image.py prints (the
# VM shuts down hourly once it has expired).
$lic = Get-CimInstance SoftwareLicensingProduct -Filter "PartialProductKey IS NOT NULL AND ApplicationID='55c92734-d682-4d71-983e-d6ec3f16059f'"
$expiry = (Get-Date).AddMinutes($lic.GracePeriodRemaining).ToUniversalTime().ToString('yyyy-MM-dd')
Write-Output "licence: $($lic.Name), LicenseStatus $($lic.LicenseStatus), expires $expiry"
Write-Output "EVAL_EXPIRY=$expiry"
if ($lic.LicenseStatus -ne 1) {
    $failures += "licence status $($lic.LicenseStatus), expected 1 (Licensed)"
}

# No reboot pending: the saved VM states would carry the pending servicing
# into every test run (a failed DISM cleanup, a setup's 3010 left over).
$pending = @()
if (Test-Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootPending') {
    $pending += 'component servicing (CBS RebootPending)'
}
if (Test-Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired') {
    $pending += 'Windows Update (RebootRequired)'
}
$renames = @((Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager' -Name PendingFileRenameOperations -ErrorAction Ignore).PendingFileRenameOperations |
        Where-Object { $_ })
if ($renames.Count -gt 0) {
    $pending += "file renames [$($renames -join ', ')]"
}
if ($pending.Count -gt 0) {
    $failures += "reboot pending: $($pending -join '; ')"
}

if ($failures.Count -gt 0) {
    $failures | ForEach-Object { Write-Output "FAIL: $_" }
    exit 1
}
Write-Output 'guest state OK'
