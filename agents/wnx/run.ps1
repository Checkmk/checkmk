# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# This is reinterpretation of our standard run script
# Some features are not implemented because it is top level script
# -format
# -check-format
# -documentation
# -setup

if ((get-host).version.major -lt 7) {
    Write-Host "PowerShell version 7 or higher is required." -ForegroundColor Red
    exit
}

$argAll = $false
$argClean = $false
$argCtl = $false
$argBuild = $false
$argTest = $false
$argSign = $false
$argMsi = $false
$argOhm = $false
$argExt = $false
$argSql = $false
$argDetach = $false

$msbuild_exe = "C:\Program Files\Microsoft Visual Studio\2022\Professional\MSBuild\Current\Bin\msbuild.exe"
$repo_root = (get-item $pwd).parent.parent.FullName
$arte = "$repo_root\artefacts"
$build_dir = "$pwd\build"
$ohm_dir = "$build_dir\ohm\"
$env:ExternalCompilerOptions = "/DDECREASE_COMPILE_TIME"
$hash_file = "$arte\windows_files_hashes.txt"
$usbip_exe = "c:\common\usbip-win-0.3.6-dev\usbip.exe"
$make_exe = where.exe make | Out-String


if ("$env:arg_var_value" -ne "") {
    $env:arg_val_name = $env:arg_var_value
}
else {
    $env:arg_val_name = ""
}

function Write-Help() {
    $x = Get-Item $PSCommandPath
    $x.BaseName
    $name = "powershell -File " + $x.BaseName + ".ps1"

    Write-Host "Usage:"
    Write-Host ""
    Write-Host "$name [arguments]"
    Write-Host ""
    Write-Host "Available arguments:"
    Write-Host "  -?, -h, --help       display help and exit"
    Write-Host "  -A, --all            shortcut to -B -C -O -T -M -E -Q:  build, ctl, ohm, unit, msi, extensions, mk-sql"
    Write-Host "  --clean-all          clean literally all, use with care"
    Write-Host "  --clean-artifacts    clean artifacts"
    Write-Host "  -C, --ctl            build controller"
    Write-Host "  -Q, --mk-sql         build mk-sql"
    Write-Host "  -B, --build          build agent"
    Write-Host "  -M, --msi            build msi"
    Write-Host "  -O, --ohm            build ohm"
    Write-Host "  -E, --extensions     build extensions"
    Write-Host "  -T, --test           run agent component tests using binary in repo_root/artefacts"
    Write-Host "  --detach             detach USB before running"
    Write-Host "  --sign               sign controller using Yubikey based Code Certificate"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host ""
    Write-Host "$name --ctl"
    Write-Host "$name --build --test"
    Write-Host "$name --build -T --sign"
    Write-Host "$name -A"
    Write-Host "$name --all --sign"
}


if ($args.Length -eq 0) {
    Write-Host "No arguments provided. Running with default flags." -ForegroundColor Yellow
    $argAll = $true
}
else {
    for ($i = 0; $i -lt $args.Length; $i++) {
        switch ($args[$i]) {
            { $("-?", "-h", "--help") -contains "$_" } { Write-Help; return }
            { $("-A", "--all") -contains $_ } { $argAll = $true }
            { $("-C", "--controller") -contains $_ } { $argCtl = $true }
            { $("-B", "--build") -contains $_ } { $argBuild = $true }
            { $("-M", "--msi") -contains $_ } { $argMsi = $true }
            { $("-O", "--ohm") -contains $_ } { $argOhm = $true }
            { $("-Q", "--mk-sql") -contains $_ } { $argSql = $true }
            { $("-E", "--extensions") -contains $_ } { $argExt = $true }
            { $("-T", "--test") -contains $_ } { $argTest = $true }
            "--clean-all" { $argClean = $true; $argCleanArtifacts = $true }
            "--clean-artifacts" { $argCleanArtifacts = $true }
            "--detach" { $argDetach = $true }
            "--var" {
                [Environment]::SetEnvironmentVariable($args[++$i], $args[++$i])
            }
            "--sign" { $argSign = $true }
        }
    }
}


if ($argAll) {
    $argBuild = $true
    $argOhm = $true
    $argCtl = $true
    $argTest = $true
    $argSql = $true
    $argExt = $true
    $argMsi = $true
}


# Example of setting environment variables (equivalent to SETLOCAL in batch)
$env:LOGONSERVER = "YourLogonServerHere"
$env:USERNAME = "YourUsernameHere"

function Invoke-CheckApp( [String]$title, [String]$cmdline ) {
    try {
        Invoke-Expression $cmdline > $null
        if ($LASTEXITCODE -ne 0) {
            throw
        }
        Write-Host "[+] $title" -Fore Green
    }
    catch {
        Write-Host "[-] $title :$_" -Fore Red
        Exit 55
    }
}

function Add-HashLine($file_to_hash, $out_file) {
    Write-Host "$file_to_hash is to be hashed to $out_file"

    try {
        $file_to_hash_name = Get-ChildItem -Path $file_to_hash | Select-Object Name -ExpandProperty Name
        Add-Content -Path $out_file -Value ($file_to_hash_name + " ") -NoNewLine
        Get-FileHash $file_to_hash -Algorithm SHA256 -ErrorAction Stop | Select-Object Hash -ExpandProperty Hash | Add-Content -Path $out_file
    }
    catch {
        Write-Host "Failed to hash $file_to_hash with error $_" -ForegroundColor Red
    }
}


function Get-Version {
    $first_line = Get-Content -Path "include\common\wnx_version.h" -TotalCount 1
    if ($first_line.Substring(0, 29) -eq "#define CMK_WIN_AGENT_VERSION") {
        return $first_line.Substring(30, $first_line.Length - 30)
    }

    Write-Error "wnx_version not found in include\common\wnx_version.h" -ErrorAction Stop
}

function Build-Agent {
    if ($argBuild -ne $true) {
        Write-Host "Skipping Agent build..." -ForegroundColor Yellow
        return
    }

    Write-Host "Building agent..." -ForegroundColor White
    $env:msbuild_exe = $msbuild_exe
    $env:make_exe = $make_exe.trim()
    $env:wnx_version = Get-Version
    Write-Host "Used version: $env:wnx_version"
    Write-Host make is $env:make_exe 
    & $env:make_exe install_extlibs
    if ($lastexitcode -ne 0) {
        Write-Error "Failed to install extlibs, error code is $LASTEXITCODE" -ErrorAction Stop
    }
    Write-Host "Start build" -ForegroundColor White
    & "$PSScriptRoot\parallel.ps1"
    if ($lastexitcode -ne 0) {
        Write-Error "Failed to build Agent, error code is $LASTEXITCODE" -ErrorAction Stop
    }

    # upload test artifacts for separate testing
    Copy-Item $build_dir/watest/Win32/Release/watest32.exe $arte -Force -ErrorAction Stop
    Copy-Item $build_dir/watest/x64/Release/watest64.exe $arte -Force -ErrorAction Stop
    
    Write-Host "Success building agent" -ForegroundColor Green
}

function Build-Package([bool]$exec, [System.IO.FileInfo]$dir, [string]$name, [string]$cmd) {
    if ($exec -ne $true) {
        Write-Host "Skipping $name build..." -ForegroundColor Yellow
        return
    }

    Write-Host "Building $name..." -ForegroundColor White
    $cwd = Get-Location
    Set-Location "../../packages/$dir"
    & ./run.cmd $cmd
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Error building $name, error code is $LASTEXITCODE" -ErrorAction Stop
    }
    Set-Location $cwd
    Write-Host "Success building $name :" -foreground Green
}

function Build-Ext {
    if ($argExt -ne $true) {
        Write-Host "Skipping Ext build..." -ForegroundColor Yellow
        return
    }
    Write-Host "Building Ext..." -ForegroundColor White
    $cwd = Get-Location
    Set-Location "extensions\robotmk_ext"
    & ../../scripts/cargo_build_robotmk.cmd
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Error building Ext, error code is $LASTEXITCODE" -ErrorAction Stop
    }

    Write-Host "Success building Ext" -foreground Green
    Set-Location $cwd
}

function Build-OHM() {
    if ($argOhm -ne $true) {
        Write-Host "Skipping OHM build..." -ForegroundColor Yellow
        return
    }
    Write-Host "Building OHM..." -ForegroundColor White
    & $msbuild_exe .\ohm\ohm.sln "/p:OutDir=$ohm_dir;TargetFrameworkVersion=v4.6;Configuration=Release"
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Error building OHM, error code is $LASTEXITCODE" -ErrorAction Stop
    }

    Write-Host "Uploading OHM" -foreground Green
    Copy-Item "$ohm_dir/OpenHardwareMonitorLib.dll" $arte -Force -ErrorAction Stop
    Copy-Item "$ohm_dir/OpenHardwareMonitorCLI.exe" $arte -Force -ErrorAction Stop
    Write-Host "Success building OHM" -foreground Green
}

function Build-MSI {
    if ($argMsi -ne $true) {
        Write-Host "Skipping Ext build..." -ForegroundColor Yellow
        return
    }
    Write-Host "Building MSI..." -ForegroundColor White
    Remove-Item "$build_dir/install/Release/check_mk_service.msi" -Force -ErrorAction SilentlyContinue

    & $msbuild_exe wamain.sln "/t:install" "/p:Configuration=Release,Platform=x86"
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Error building MSI, error code is $LASTEXITCODE" -ErrorAction Stop
    }
    Write-Host "Success building MSI" -foreground Green
}


function Invoke-ChangeMsiProperties([string]$file, $version) {
    $Installer = new-object -comobject WindowsInstaller.Installer
    $MSIOpenDatabaseModeTransact = 2
    $MsiFilePath = $file

    $MsiDBCom = $Installer.GetType().InvokeMember(
        "OpenDatabase",
        "InvokeMethod",
        $Null,
        $Installer,
        @($MsiFilePath, $MSIOpenDatabaseModeTransact)
    )
    $query = "UPDATE `Property` SET `Property`.`Value`='$version_base' WHERE `Property`.`Property`='ProductVersion'"
    $Insert = $MsiDBCom.GetType().InvokeMember("OpenView", "InvokeMethod", $Null, $MsiDBCom, ($query))
    $Insert.GetType().InvokeMember("Execute", "InvokeMethod", $Null, $Insert, $Null)
    $Insert.GetType().InvokeMember("Close", "InvokeMethod", $Null, $Insert, $Null)
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($Insert) | Out-Null

    $MsiDBCom.GetType().InvokeMember("Commit", "InvokeMethod", $Null, $MsiDBCom, $Null)
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($MsiDBCom) | Out-Null
}

function Set-MSI-Version {
    if ($argMsi -ne $true) {
        Write-Host "Skipping Set MSI version..." -ForegroundColor Yellow
        return
    }

    $version = Get-Version
    $version_base = $version.substring(1, $version.length - 2)
    Write-Host "Setting MSI version: $version_base" -ForegroundColor White
    Invoke-ChangeMsiProperties $build_dir\install\Release\check_mk_service.msi $version_base
    # deprecated:
    # & echo cscript.exe //nologo scripts\WiRunSQL.vbs $build_dir\install\Release\check_mk_service.msi "UPDATE `Property` SET `Property`.`Value`='$version_base' WHERE `Property`.`Property`='ProductVersion'"
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Error setting version MSI, error code is $LASTEXITCODE" -ErrorAction Stop
    }
    Write-Host "Success setting version MSI" -foreground Green
}

function Start-UnitTests {
    if ($argTest -ne $true) {
        Write-Host "Skipping unit testing..." -ForegroundColor Yellow
        return
    }
    Write-Host "Running unit tests..." -ForegroundColor White
    & ./run_tests.ps1 --unit
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Error unit Testing, error code is $LASTEXITCODE" -ErrorAction Stop
    }
    Write-Host "Success unit tests" -foreground Green
}

function Invoke-Attach($usbip, $addr, $port) {
    if ($argSign -ne $true) {
        Write-Host "Skipping attach" -ForegroundColor Yellow
        return
    }
    &$usbip attach -r $addr -b $port
    for ($i = 1; $i -le 15; $i++) {
        if ($LASTEXITCODE -eq 0) {
            break
        }
        Write-Host "Waiting 2 seconds for USB to attach" -ForegroundColor White
        Start-Sleep -Seconds 2
    }
    if ($LASTEXITCODE -ne 0) {
        $argSign = $False
        Write-Host "Failed to attach USB token" $LASTEXITCODE -foreground Red
        throw "Attach to the signing key is not possible. Signing can't be done"
    }
    Write-Host "Attached USB, waiting a bit" -ForegroundColor Green
    Start-Sleep -Seconds 5
    return
}

function Test-Administrator {  
    [OutputType([bool])]
    param()
    process {
        [Security.Principal.WindowsPrincipal]$user = [Security.Principal.WindowsIdentity]::GetCurrent();
        return $user.IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator);
    }
}

function Invoke-TestSigning($usbip) {
    if ($argSign -ne $true) {
        Write-Host "Skipping Test Signing..." -ForegroundColor Yellow
        return
    }

    if (-not(Test-Path -Path $usbip -PathType Leaf)) {
        $argSign = $False
        Write-Host "$usbip doesn't exist" -ForegroundColor Red
        throw 
    }

    if (-not (Test-Administrator)) {
        Write-Host "This script must be executed as Administrator." -ForegroundColor Red
        $argSign = $False
        return
    }

    Write-Host "check port"
    &$usbip port
    if ($LastExitCode -eq 3) {
        $argSign = $False
        Write-Host "No chance"
        throw 
    }
    Write-Host "try to detach"

    &$usbip detach -p 00
    if ($LastExitCode -eq 0) {
        Write-Host "Should not happen: connection has been established"
    }

}

function Start-MsiControlBuild {
    if ($argSign -ne $true) {
        Write-Host "Skipping MSI Control Build..." -ForegroundColor Yellow
        return
    }

    Write-Host "Building controlly MSI..." -ForegroundColor White
    & $msbuild_exe wamain.sln "/t:install" "/p:Configuration=Release,Platform=x86"
    if ($LASTEXITCODE -ne 0 ) {
        Write-Error "Build Failed, error code is $LASTEXITCODE" -ErrorAction Stop
    }
}

function Start-BinarySigning {
    if ($argSign -ne $true) {
        Write-Host "Skipping Signing..." -ForegroundColor Yellow
        return
    }

    Write-Host "Binary signing..." -ForegroundColor White
    Remove-Item $hash_file -Force

    $files_to_sign = @(
        "$build_dir\check_mk_service\x64\Release\check_mk_service64.exe",
        "$build_dir\check_mk_service\Win32\Release\check_mk_service32.exe",
        "$arte\cmk-agent-ctl.exe",
        "$arte\mk-sql.exe",
        "$ohm_dir\OpenHardwareMonitorLib.dll",
        "$ohm_dir\OpenHardwareMonitorCLI.exe"
    )

    foreach ($file in $files_to_sign) {
        Write-Host "Signing $file" -ForegroundColor White
        & ./scripts/sign_code.cmd $file
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Error Signing, error code is $LASTEXITCODE" -ErrorAction Stop
            throw
        }
        Add-HashLine $file $hash_file

    }
    Write-Host "Success binary signing" -foreground Green
}


function Start-ArtifactUploading {
    if ($argMsi -ne $true) {
        Write-Host "Skipping upload to artifacts..." -ForegroundColor Yellow
        return
    }

    Write-Host "Artifact upload..." -ForegroundColor White
    $artifacts = @(
        @("$build_dir/install/Release/check_mk_service.msi", "$arte/check_mk_agent.msi"),
        @("$build_dir/check_mk_service/x64/Release/check_mk_service64.exe", "$arte/check_mk_agent-64.exe"),
        @("$build_dir/check_mk_service/Win32/Release/check_mk_service32.exe", "$arte/check_mk_agent.exe"),
        @("$build_dir/ohm/OpenHardwareMonitorCLI.exe", "$arte/OpenHardwareMonitorCLI.exe"),
        @("$build_dir/ohm/OpenHardwareMonitorLib.dll", "$arte/OpenHardwareMonitorLib.dll"),
        @("./install/resources/check_mk.user.yml", "$arte/check_mk.user.yml"),
        @("./install/resources/check_mk.yml", "$arte/check_mk.yml")
    )
    foreach ($artifact in $artifacts) {
        Copy-Item $artifact[0] $artifact[1] -Force -ErrorAction Stop
    }
    Write-Host "Success artifact uploading" -foreground Green
}


function Start-MsiPatching {
    if ($argMsi -ne $true) {
        Write-Host "Skipping MSI patching..." -ForegroundColor Yellow
        return
    }

    Write-Host "MSI Patching..." -ForegroundColor White
    & "$make_exe" msi_patch
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to patch MSI " $LASTEXITCODE -ErrorAction Stop
    }
    Copy-Item $arte/check_mk_agent.msi $arte/check_mk_agent_unsigned.msi -Force
    Write-Host "Success artifact uploading" -foreground Green
}

function Invoke-Detach($argFlag) {
    if ($argFlag -ne $true) {
        Write-Host "No need to detach"
        return
    }
    & $usbip_exe detach -p 00
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to detach " $LASTEXITCODE -foreground Yellow
        return
    }
    Start-Sleep -Seconds 2
    Write-Host "Detached!" -ForegroundColor Green
}



function Start-MsiSigning {
    if ($argSign -ne $true) {
        Write-Host "Skipping MSI signing..." -ForegroundColor Yellow
        return
    }

    Write-Host "MSI signing..." -ForegroundColor White
    & ./scripts/sign_code.cmd $arte\check_mk_agent.msi
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed sign MSI " $LASTEXITCODE -foreground Red
        throw
    }
    Add-HashLine $arte/check_mk_agent.msi $hash_file
    Invoke-Detach $argSign
    & ./scripts/call_signing_tests.cmd
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed test MSI " $LASTEXITCODE -foreground Red
        throw
    }
    & py "-3" "./scripts/check_hashes.py" "$hash_file"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed hashing test " $LASTEXITCODE -foreground Red
        throw
    }
    powershell Write-Host "MSI signing succeeded" -Foreground Green
}

function Clear-Artifacts() {
    if ($argCleanArtifacts -ne $true) {
        return
    }
    Write-Host "Cleaning artifacts..."
    $masks = "*.msi", "*.exe", "*.log", "*.yml"
    foreach ($mask in $masks) {
        Remove-Item -Path "$arte\$mask" -Force -ErrorAction SilentlyContinue
    }
}

function Clear-All() {
    if ($argClean -ne $true) {
        return
    }

    Write-Host "Cleaning packages..."
    Build-Package $true "host/cmk-agent-ctl" "Controller" "--clean"
    Build-Package $true "host/mk-sql" "MK-SQL" "--clean"

    Clear-Artifacts

    Write-Host "Cleaning $build_dir..."
    Remove-Item -Path "$build_dir" -Recurse -Force -ErrorAction SilentlyContinue
}

function Update-ArtefactDirs() {
    If (Test-Path -PathType container $arte) {
        Write-Host "Using arte dir: '$arte'" -ForegroundColor White
    }
    else {
        Remove-Item $arte -ErrorAction SilentlyContinue     # we may have find strange files from bad scripts
        Write-Host "Creating arte dir: '$arte'" -ForegroundColor White
        New-Item -ItemType Directory -Path $arte -ErrorAction Stop > nul
    }
}


Invoke-CheckApp "choco" "choco -v"
Invoke-CheckApp "perl" "perl -v"
Invoke-CheckApp "make" "make -v"
Invoke-CheckApp "msvc" "& ""$msbuild_exe"" --version"
Invoke-CheckApp "is_crlf" "python .\scripts\check_crlf.py"

$argAttached = $false
$result = 1
try {
    # SETTING UP
    $mainStartTime = Get-Date
    Invoke-Detach $argDetach
    Update-ArtefactDirs
    Clear-Artifacts
    Clear-All

    # BUILDING
    Build-Agent
    Build-Package $argCtl "host/cmk-agent-ctl" "Controller"
    Build-Package $argSql "host/mk-sql" "MK-SQL"
    Build-Ohm
    Build-Ext
    Build-MSI
    Set-Msi-Version
    Start-UnitTests

    # SIGNING
    Invoke-TestSigning $usbip_exe
    Start-MsiControlBuild
    Invoke-Attach $usbip_exe "yubi-usbserver.lan.checkmk.net" "1-1.2"
    if ($argSign -eq $true) {
        $argAttached = $true
    }
    $env:Path Out-File -Path .\check.txt 
    $env:CI_TEST_SQL_DB_ENDPOINT Out-File -Path .\check.txt 
    $env:pin_cert_windows_usb Out-File -Path .\check.txt 
    Start-BinarySigning
    Start-ArtifactUploading
    Start-MsiPatching
    Start-MsiSigning
    $endTime = Get-Date
    $elapsedTime = $endTime - $mainStartTime
    Write-Host "Elapsed time: $($elapsedTime.Hours):$($elapsedTime.Minutes):$($elapsedTime.Seconds)"
    $result = 0
}
catch {
    Write-Host "Error: " $_ -ForegroundColor Red
    Write-Host "Trace stack: " -ForegroundColor Yellow
    Write-Host $_.ScriptStackTrace -ForegroundColor Yellow
}
finally {
    Invoke-Detach $argAttached
}
exit $result


