# First-logon provisioning script.
# Runs once after OOBE auto-completes, via the FirstLogonCommand of
# answer/autounattend-core.xml (Server Core).
#
# What this does (the step numbers below):
#   1-2a  The guest agent: the virtio-serial driver, qemu-ga (virtio-win CD),
#         its event log
#   3     The serial console (EMS) on COM1
#   4     Remove Microsoft Defender Antivirus (with its payload)
#   5     Windows Update on demand only
#   6-6b  Test signing (OHM's WinRing0), a fixed 256 MB pagefile, autologon
#   7-7a2 Time zone, the RTC in UTC, no password expiry
#   7b*   Volume mount point, a quiet logon session
#   8     Write C:\setup\done.txt: 'ok', or the steps that failed
#   9     Power off
#
# There is no channel to the guest until this is done: make_image.py waits
# for the power-off and cold boots the guest (which makes test signing, the
# Defender removal and the pagefile take effect), then reads done.txt
# through the guest agent.
#
# Diagnostics: tee output to C:\setup\first-logon.log, which make_image.py
# shows if something fails.

$ErrorActionPreference = 'Continue'   # keep going past warnings; done.txt lists the failures
Start-Transcript -Path C:\setup\first-logon.log -Append

Write-Host "=== first-logon.ps1 starting at $(Get-Date) ==="

# Native commands do not throw: each call goes through this, and a non-zero
# exit code lands in done.txt, which fails the build. So does every cmdlet
# error in $Error (expected ones use -ErrorAction Ignore, which skips it).
$Failures = @()
$Error.Clear()
function Invoke-Native([string]$What, [scriptblock]$Command) {
    & $Command
    if ($LASTEXITCODE -ne 0) {
        $script:Failures += "${What}: exit code $LASTEXITCODE"
        Write-Host "FAILED: ${What}: exit code $LASTEXITCODE"
    }
}

# 1. The virtio-serial driver (vioser), for the port QEMU gives the guest
#    agent, from the virtio-win CD. Its Server 2022 build is
#    attestation-signed by Microsoft: it loads without test signing, which
#    is only on from the next boot.
$virtio = Get-Volume | Where-Object { $_.DriveType -eq 'CD-ROM' -and $_.DriveLetter -and
    (Test-Path "$($_.DriveLetter):\vioserial\2k22\amd64\vioser.inf") } | Select-Object -First 1
if (-not $virtio) {
    $Failures += 'no virtio-win CD (vioserial\2k22\amd64\vioser.inf)'
}
else {
    $cd = "$($virtio.DriveLetter):"
    Write-Host "Installing the virtio-serial driver from $cd..."
    Invoke-Native 'pnputil vioser.inf' { pnputil.exe /add-driver "$cd\vioserial\2k22\amd64\vioser.inf" /install }
    $port = @(Get-PnpDevice -PresentOnly -InstanceId 'PCI\VEN_1AF4&DEV_1003*' -ErrorAction Ignore)
    Write-Host "virtio-serial device: $(($port | ForEach-Object { "$($_.FriendlyName) $($_.Status)" }) -join ', ')"
    if ($port.Count -ne 1 -or $port[0].Status -ne 'OK') {
        $Failures += "virtio-serial device is [$(($port | ForEach-Object Status) -join ', ')], expected one OK"
    }

    # 2. The guest agent (qemu-ga), the service QEMU-GA (LocalSystem,
    #    Automatic): make_image.py drives every later boot through it. It
    #    waits for its port itself (--retry-path).
    Write-Host "Installing the QEMU guest agent from $cd..."
    $p = Start-Process -FilePath msiexec.exe -Wait -PassThru -ArgumentList `
        '/i', "`"$cd\guest-agent\qemu-ga-x86_64.msi`"", '/qn', '/norestart', '/l*v', 'C:\setup\qemu-ga-msi.log'
    if ($p.ExitCode -ne 0) { $Failures += "msiexec qemu-ga-x86_64.msi: exit code $($p.ExitCode)" }
    $qga = Get-Service QEMU-GA -ErrorAction Ignore
    Write-Host "QEMU-GA: Status=$($qga.Status) StartType=$($qga.StartType)"
    if (-not $qga -or $qga.Status -ne 'Running' -or $qga.StartType -ne 'Automatic') {
        $Failures += "QEMU-GA service is $($qga.Status)/$($qga.StartType), expected Running/Automatic"
    }

    # 2a. qemu-ga reports most commands to the event log, as the source
    #     qemu-ga, which its installer registers in the Application log.
    #     There, the commands that run a test's payload would add records to
    #     the log the regression suite's event log tests count: a log of its
    #     own instead, which Windows uses from the next boot on.
    if ([Diagnostics.EventLog]::LogNameFromSourceName('qemu-ga', '.') -eq 'Application') {
        Remove-EventLog -Source qemu-ga
        New-EventLog -LogName qemu-ga -Source qemu-ga
    }
    $qgaLog = [Diagnostics.EventLog]::LogNameFromSourceName('qemu-ga', '.')
    Write-Host "qemu-ga event source: log $qgaLog"
    if ($qgaLog -ne 'qemu-ga') { $Failures += "qemu-ga event source is in the log '$qgaLog', expected its own" }
}

# 3. Emergency Management Services on COM1, 115200 baud: the Special
#    Administration Console, a shell on a socket of the host for a guest
#    whose agent does not answer (README.md). Takes effect with the next
#    boot.
Write-Host "Enabling EMS on COM1..."
Invoke-Native 'bcdedit /ems on' { bcdedit /ems '{current}' on }
Invoke-Native 'bcdedit /emssettings' { bcdedit /emssettings EMSPORT:1 EMSBAUDRATE:115200 }

# 4. Microsoft Defender Antivirus: removed (Windows-Defender feature).
#    It used to be kept with real-time protection off and its four
#    scheduled tasks disabled, but its engine re-enables those tasks
#    about 10 min after every start, i.e. also on resumed VM states, and
#    still ran at several 10 % CPU whenever one came due. No test uses
#    it. The removal takes effect with the next boot; verify-image.ps1
#    checks that the feature, its service, MsMpEng and its scheduled tasks
#    are gone. -Remove also deletes the feature's payload from the
#    component store (state Removed instead of Available), so it takes no
#    space in the image; reinstalling it would need the install media as a
#    source, which a test image never does.
Write-Host "Removing Microsoft Defender Antivirus (Windows-Defender feature, with its payload)..."
$r = Uninstall-WindowsFeature -Name Windows-Defender -Remove
Write-Host "Uninstall-WindowsFeature Windows-Defender -Remove: Success=$($r.Success) RestartNeeded=$($r.RestartNeeded) ExitCode=$($r.ExitCode)"
if (-not $r.Success) { $Failures += 'Uninstall-WindowsFeature Windows-Defender' }

# 5. Windows Update: no automatic updates (the policy, set by the answer
#    file before the first logon), so no surprise reboots or updates in a
#    saved VM state; the image is rebuilt on a cadence instead (at least
#    every 180 days, for its Eval licence). The SERVICE stays available on
#    demand (Manual, not Disabled): the windows_updates.ps1 plugin's Pester
#    suite exercises the real Microsoft.Update.Session COM API, which needs
#    to be able to start wuauserv.
Write-Host "Windows Update on demand only..."
Set-Service wuauserv -StartupType Manual

# 6. Test-signing mode, required for OHM's WinRing0 driver to load.  Takes
#    effect with the next boot.
Write-Host "Enabling kernel test-signing..."
Invoke-Native 'bcdedit /set testsigning on' { bcdedit /set testsigning on }

# 6a. Fixed 256 MB pagefile on C:. System-managed, Windows sizes it at
#     1408 MB for this 4 GB guest, all of it in the image; a resumed guest
#     peaks at under 100 MB of pagefile use. A pagefile must still exist:
#     watest's FileInfoTest.MakeFileInfoPagefile reads c:\pagefile.sys.
#     Takes effect with the next boot.
Write-Host "Setting a fixed 256 MB pagefile on C:..."
$cs = Get-CimInstance Win32_ComputerSystem
if ($cs.AutomaticManagedPagefile) {
    Set-CimInstance -InputObject $cs -Property @{ AutomaticManagedPagefile = $false }
}
$pf = Get-CimInstance Win32_PageFileSetting | Where-Object Name -EQ 'C:\pagefile.sys'
if (-not $pf) {
    $pf = New-CimInstance -ClassName Win32_PageFileSetting -Property @{ Name = 'C:\pagefile.sys' }
}
Set-CimInstance -InputObject $pf -Property @{ InitialSize = [uint32]256; MaximumSize = [uint32]256 }
$mm = 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management'
Write-Host "PagingFiles: $((Get-ItemProperty $mm).PagingFiles -join '; ')"

# 6b. Permanent autologon: the run-as watest tests (WtoolsRunAsFixture,
#     PluginTest.SyncPluginsGroup*) spawn processes as freshly created users,
#     which needs an interactive window station: spawning from a
#     non-interactive session fails with STATUS_DLL_INIT_FAILED.  The legacy CI nodes are
#     auto-logged-on; mirror that.  The test runner executes the suite inside
#     this session via a scheduled task (schtasks /it).
Write-Host "Enabling permanent autologon..."
$wl = 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon'
Set-ItemProperty -Path $wl -Name AutoAdminLogon -Value '1' -Type String
Set-ItemProperty -Path $wl -Name DefaultUserName -Value 'Administrator' -Type String
Set-ItemProperty -Path $wl -Name DefaultPassword -Value '@@PASSWORD@@' -Type String
Remove-ItemProperty -Path $wl -Name AutoLogonCount -ErrorAction Ignore

# 7. Timezone: the legacy Windows CI nodes run Europe/Berlin and watest's
#    CheckMkHeader.{GetTimezoneOffset,IsoTime} hardcode Berlin offsets.
Write-Host "Setting timezone to W. Europe Standard Time..."
Invoke-Native 'tzutil' { tzutil /s "W. Europe Standard Time" }

# 7a. QEMU's RTC runs in UTC; without RealTimeIsUniversal Windows reads it
#     as local time and every cold boot starts 1-2 h off. After each resume
#     of a saved VM state (hours or days old) the test runner sets the guest
#     clock from the host: w32time alone would need internet, and it
#     refuses to correct more than 15 h (MaxPosPhaseCorrection). w32time
#     itself stays as installed: the agent's w32time sections need it.
Write-Host "RTC in UTC..."
$tzi = 'HKLM:\SYSTEM\CurrentControlSet\Control\TimeZoneInformation'
New-ItemProperty -Path $tzi -Name RealTimeIsUniversal -Value 1 -PropertyType DWord -Force | Out-Null

# 7a2. The Administrator password never expires. Windows' default maximum
#      age is 42 days; the runners bind their scheduled task to the session
#      with this password (schtasks /rp), which would fail 42 days after
#      the image was built once the guest clock follows the host.
Write-Host "Password expiry off..."
Invoke-Native 'net accounts' { net accounts /maxpwage:unlimited }
Set-LocalUser -Name Administrator -PasswordNeverExpires $true

# 7b3. Volume mount point: watest's DfTest.ProduceMountPointsOutput
#      GTEST_SKIPs unless C: hosts at least one volume mount point.
#      Self-mounting the C: volume at C:\mnt\c is enough.
Write-Host "Creating volume mount point C:\mnt\c..."
New-Item -Path C:\mnt\c -ItemType Directory -Force | Out-Null
$cVolume = (Get-Volume -DriveLetter C).Path
if (-not $cVolume) {
    $Failures += 'mount point C:\mnt\c: no volume path for C:'
}
else {
    Invoke-Native 'mountvol C:\mnt\c' { mountvol C:\mnt\c $cVolume }
}

# 7b4. Keep the auto-logged-on test session quiet: Server Core's logon
#      console runs SConfig (a PowerShell menu that queries Windows Update
#      and network state at every launch), so turn that off.
Write-Host "Keeping SConfig from launching at logon..."
Set-SConfig -AutoLaunch $false

# 7b5. No "Networks: allow your PC to be discoverable?" flyout. It pops
#      whenever an adapter joins a network Windows has not seen before,
#      e.g. nic1 if its link ever comes up; the key's presence turns it off.
Write-Host "Suppressing the new-network flyout..."
$nn = 'HKLM:\SYSTEM\CurrentControlSet\Control\Network\NewNetworkWindowOff'
if (!(Test-Path $nn)) { New-Item -Path $nn | Out-Null }

# Oldest first.
for ($e = $Error.Count - 1; $e -ge 0; $e--) {
    $Failures += "$($Error[$e].InvocationInfo.MyCommand): $($Error[$e].Exception.Message)"
}
Write-Host "=== first-logon.ps1 finished at $(Get-Date), $($Failures.Count) failures ==="
$Failures | ForEach-Object { Write-Host "FAILED: $_" }
Stop-Transcript

# 8. The marker make_image.py reads in the next boot: 'ok', or what failed.
$marker = if ($Failures.Count -eq 0) { 'ok' } else { $Failures -join "`r`n" }
Set-Content -Path C:\setup\done.txt -Value $marker -Encoding ASCII

# 9. Power off, which make_image.py waits for.
Stop-Computer -Force
