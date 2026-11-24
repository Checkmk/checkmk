# Guest-side, for msi-install-qemu (msi_install_qemu.py): validates the
# check_mk_agent.msi staged next to this script with WiX's smoke.exe,
# installs it, verifies the deployed agent's service answers on 6556,
# uninstalls again and verifies the service is gone. -ProductUpgradeCode is
# the agent's UpgradeCode (a GUID without braces), which identifies an
# installed agent of any build. -PlaceholderVersion is Product.wxs's
# ProductVersion, see Assert-MsiValid.
#
# Orchestrates validate, then install -> verify -> uninstall -> verify
# removal. Any failed step fails the run. The install runs after a failed
# validation too, and the uninstall always runs, so that its removal is
# checked after a partial install too. The exit code is the result.
param(
    [Parameter(Mandatory)][string]$ProductUpgradeCode,
    [Parameter(Mandatory)][string]$PlaceholderVersion
)
$ErrorActionPreference = 'Stop'
$rid = $PSScriptRoot
$upgradeCode = '{' + $ProductUpgradeCode + '}'

function Step($msg) { Write-Host "=== $msg" }

function Invoke-Msiexec($verb, $target, $log) {
    (Start-Process msiexec -Wait -PassThru -ArgumentList `
        $verb, $target, '/qn', '/norestart', '/l*v', "$rid\$log").ExitCode
}

# 3010: success, reboot required (suppressed by /norestart).
function Test-MsiOk($code) { $code -eq 0 -or $code -eq 3010 }

# The verbose log is the only record of which action failed: put the
# failing action's context (or the log's tail) into the output.
function Show-MsiFailure($log) {
    if (-not (Test-Path "$rid\$log")) { return }
    $hit = Select-String -Path "$rid\$log" -Pattern 'Return value 3' -Context 30, 0 |
        Select-Object -First 1
    $lines = if ($hit) {
        @($hit.Context.PreContext) + $hit.Line
    }
    else {
        Get-Content "$rid\$log" -Tail 40
    }
    $lines | ForEach-Object { Write-Host $_ }
}

# Runs the ICEs light.exe skips with -sval (WiX's darice.cub, which smoke.exe
# loads from its own directory) on the final MSI, after build_msi.sh's
# patch_agent_msi. ICE24 rejects the Checkmk version that sets as
# ProductVersion (3.0.0b1, 2026.11.12), so a copy gets Product.wxs's
# placeholder back and is validated with every ICE. Errors fail, warnings
# (SMOK1076) are only shown.
function Assert-MsiValid {
    Step "validating check_mk_agent.msi"
    $msi = "$rid\validate.msi"
    Copy-Item "$rid\check_mk_agent.msi" $msi
    $wi = New-Object -ComObject WindowsInstaller.Installer
    $db = $wi.OpenDatabase($msi, 1) # msiOpenDatabaseModeTransact
    $db.OpenView("UPDATE Property SET Value='$PlaceholderVersion' WHERE Property='ProductVersion'").Execute()
    $db.Commit()
    # Releases the database file for smoke.exe.
    [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($db)
    & "$rid\wix\smoke.exe" -nologo $msi | Out-Host
    if ($LASTEXITCODE) { throw "smoke.exe failed with $LASTEXITCODE" }
}

function Get-CheckmkProducts {
    $wi = New-Object -ComObject WindowsInstaller.Installer
    @($wi.RelatedProducts($upgradeCode))
}

function Install-Agent {
    Step "installing check_mk_agent.msi"
    $rc = Invoke-Msiexec '/i' "$rid\check_mk_agent.msi" 'install.log'
    if (-not (Test-MsiOk $rc)) {
        Show-MsiFailure 'install.log'
        throw "msiexec /i failed with $rc"
    }
}

# Reads the whole payload, not just the accepted connection: a listener
# that answers with zero bytes is a broken deployment, and a bare
# TcpClient.Connected check would call that a pass. Until the deadline,
# an answer without the check_mk section (the controller up before the
# agent behind it) is retried.
function Assert-AgentAnswers {
    $out = ''
    $probeError = $null
    $until = (Get-Date).AddSeconds(120)
    while ($out -notmatch '<<<check_mk>>>' -and (Get-Date) -lt $until) {
        $out = ''
        $c = $null
        try {
            $c = New-Object Net.Sockets.TcpClient('127.0.0.1', 6556)
            $c.ReceiveTimeout = 30000
            $out = (New-Object IO.StreamReader($c.GetStream())).ReadToEnd()
        }
        catch {
            $probeError = $_
        }
        finally {
            if ($c) { $c.Close() }
        }
        if ($out -notmatch '<<<check_mk>>>') { Start-Sleep 2 }
    }
    $sections = ([regex]::Matches($out, '(?m)^<<<[^>]+>>>')).Count
    if ($out -notmatch '<<<check_mk>>>') {
        throw "agent output on 6556 lacks <<<check_mk>>> (sections=$sections, bytes=$($out.Length), last error: $probeError)"
    }
    Step "agent served $sections sections on 6556"
}

function Uninstall-Agent($installed) {
    Step "uninstalling"
    $rc = Invoke-Msiexec '/x' "$rid\check_mk_agent.msi" 'uninstall.log'
    # 1605 (not installed) is expected when a failed /i rolled back.
    if ((Test-MsiOk $rc) -or ($rc -eq 1605 -and -not $installed)) { return }
    Show-MsiFailure 'uninstall.log'
    throw "msiexec /x failed with $rc"
}

# Checks all of what an uninstall removes, and reports every leftover.
function Assert-AgentRemoved {
    # A service marked for deletion disappears once its last handle
    # closes, and the controller holding 6556 may outlive it by a moment;
    # give both that moment.
    $until = (Get-Date).AddSeconds(30)
    while (((Get-Service CheckmkService -ErrorAction SilentlyContinue) -or
            (Get-NetTCPConnection -LocalPort 6556 -State Listen -ErrorAction SilentlyContinue)) -and
        (Get-Date) -lt $until) { Start-Sleep 1 }
    $left = @()
    if (Get-Service CheckmkService -ErrorAction SilentlyContinue) {
        $left += 'CheckmkService is still registered'
    }
    if (Get-NetTCPConnection -LocalPort 6556 -State Listen -ErrorAction SilentlyContinue) {
        $left += 'port 6556 is still listening'
    }
    $products = @(Get-CheckmkProducts)
    if ($products.Count) {
        $left += "products still installed: $($products -join ', ')"
    }
    if ($left.Count) { throw "after the uninstall: $($left -join '; ')" }
}

$failed = $false
$installed = $false
try { Assert-MsiValid } catch { Step "error: $_"; $failed = $true }
try {
    Install-Agent
    $installed = $true
    Assert-AgentAnswers
}
catch {
    Step "error: $_"
    $failed = $true
}
finally {
    try { Uninstall-Agent $installed } catch { Step "error: $_"; $failed = $true }
    try { Assert-AgentRemoved } catch { Step "error: $_"; $failed = $true }
    exit $(if ($failed) { 1 } else { 0 })
}
