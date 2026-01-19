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
$argBuildOnly = $false
$argClean = $false
$argCtl = $false
$argSign = $false
$argMsi = $false
$argOhm = $false
$argOracle = $false
$argExt = $false
$argSql = $false
$argDetach = $false
$argWin = $false
$argSkipSqlTest = $false

$msbuild_exe = & "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe" `
    -latest `
    -requires Microsoft.Component.MSBuild `
    -find MSBuild\**\Bin\MSBuild.exe

$repo_root = (get-item $pwd).parent.parent.FullName
$results_dir = "$repo_root\artefacts"
$build_dir = "$pwd\build"
$ohm_dir = "$build_dir\ohm\"
$env:ExternalCompilerOptions = "/DDECREASE_COMPILE_TIME"
$hash_file = "$results_dir\windows_files_hashes.txt"
$usbip_exe = "c:\common\usbip-win-0.3.6-dev\usbip.exe"
$make_exe = where.exe make | Out-String
$signing_folder = "signed-files"


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
    Write-Host "  -?, -h, --help          display help and exit"
    Write-Host "  -A, --all               shortcut to -C -O -T -M -E -Q -R:  ctl, ohm, unit, msi, extensions, mk-sql, mk-oracle"
    Write-Host "  --clean-all             clean literally all, use with care"
    Write-Host "  --clean-artifacts       clean artifacts"
    Write-Host "  -C, --ctl               make controller"
    Write-Host "  -Q, --mk-sql            make mk-sql"
    Write-Host "  -R, --mk-oracle         make mk-oracle"
    Write-Host "  -B, --build             do not test, just build"
    Write-Host "  -W, --win-agent         make windows agent"
    Write-Host "  -M, --msi               make msi"
    Write-Host "  -O, --ohm               make ohm"
    Write-Host "  -E, --extensions        make extensions"
    Write-Host "  -S, --skip-sql-test     skip sql test to be able to build msi in case sql is not configured"
    Write-Host "  --detach                detach USB before running"
    Write-Host "  --sign                  sign controller using Yubikey based Code Certificate"
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
            { $("-B", "--build") -contains $_ } { $argBuildOnly = $true }
            { $("-W", "--win-agent") -contains $_ } { $argWin = $true }
            { $("-M", "--msi") -contains $_ } { $argMsi = $true }
            { $("-O", "--ohm") -contains $_ } { $argOhm = $true }
            { $("-R", "--mk-oracle") -contains $_ } { $argOracle = $true }
            { $("-Q", "--mk-sql") -contains $_ } { $argSql = $true }
            { $("-E", "--extensions") -contains $_ } { $argExt = $true }
            { $("-S", "--skip-sql-test") -contains $_ } { $argSkipSqlTest = $true }
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
    $argOhm = $true
    $argOracle = $true
    $argCtl = $true
    $argSql = $true
    $argExt = $true
    $argMsi = $true
    $argWin = $true
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
    if ($argWin -ne $true) {
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
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to install extlibs, error code is $LASTEXITCODE" -ErrorAction Stop
    }
    Write-Host "Start build" -ForegroundColor White
    & "$PSScriptRoot\parallel.ps1"
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to build Agent, error code is $LASTEXITCODE" -ErrorAction Stop
    }

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
    Copy-Item "$ohm_dir/OpenHardwareMonitorLib.dll" $results_dir -Force -ErrorAction Stop
    Copy-Item "$ohm_dir/OpenHardwareMonitorCLI.exe" $results_dir -Force -ErrorAction Stop
    Write-Host "Success building OHM" -foreground Green
}

function Build-MSI {
    if ($argMsi -ne $true) {
        Write-Host "Skipping Ext build..." -ForegroundColor Yellow
        return
    }
    Write-Host "Building MSI..." -ForegroundColor White
    Remove-Item "$build_dir/install/Release/check_mk_service.msi" -Force -ErrorAction SilentlyContinue

    & $msbuild_exe wamain.sln "/t:install" "/p:Configuration=Release,Platform=x86" "/p:EncryptedPluginsFolder=..\..\windows\plugins"
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
    if (($argBuildOnly -ne $true) -and ($argWin -eq $true) ) {
        Write-Host "Running unit tests..." -ForegroundColor White
        & ./run_tests.ps1 --plugins --unit
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Error unit Testing, error code is $LASTEXITCODE" -ErrorAction Stop
        }
        Write-Host "Success unit tests" -foreground Green
    }
    else {
        Write-Host "Skipping unit testing..." -ForegroundColor Yellow
        return
    }
}

function Test-SigningQuickly {
    if ($argSign -ne $true) {
        return
    }

    try {
        Write-Host "Validate signing..." -ForegroundColor White
        $TempFile = New-TemporaryFile
        $ps_name = $TempFile.BaseName + ".ps1"
        Rename-Item -NewName $ps_name -Path $TempFile
        $newfile = $TempFile.DirectoryName + $TempFile.BaseName + ".ps1"
        "Get-Date" | Out-File $newfile
        for ($i = 1; $i -le 15; $i++) {
            & ./scripts/sign_code_fast.cmd $newfile
            if ($LASTEXITCODE -eq 0) {
                break
            }
            Write-Host "Waiting 1 seconds before retry" -ForegroundColor White
            Start-Sleep -Seconds 1
        }
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Failed to sign test file" $LASTEXITCODE -foreground Red
        }
        else {
            Write-Host "Success signing test file" -ForegroundColor Green
        }
        Remove-Item -Path $newfile -Force -ErrorAction SilentlyContinue

    }
    catch {
        Write-Host "Failed to create temporary file" -ForegroundColor Red
    }


}



function Invoke-Attach($usbip, $addr, $port) {
    if ($argSign -ne $true) {
        Write-Host "Skipping attach" -ForegroundColor Yellow
        return
    }
    &$usbip attach -r $addr -b $port
    for ($i = 1; $i -le 20; $i++) {
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
    Test-SigningQuickly
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
        "$results_dir\cmk-agent-ctl.exe",
        "$results_dir\mk-sql.exe",
        "$results_dir\mk-oracle.exe",
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

# TODO(sk): remove the function as deprecated after switch to bazel signing
function Start-Ps1Signing {
    Write-Host "Skipping PS1 Signing..." -ForegroundColor Yellow
    return

    # code below is a reference for bazel signing

    Write-Host "Ps1 signing..." -ForegroundColor White

    $source_folder = "$repo_root\agents\windows\plugins"
    $target_folder = "$results_dir\$signing_folder"

    $fileList = @("windows_tasks.ps1", "mk_msoffice.ps1")  # Modify as needed

    if (Test-Path $target_folder) {
        Remove-Item -Path $target_folder -Recurse -Force
    }

    New-Item -ItemType Directory -Path $target_folder | Out-Null

    foreach ($file in $fileList) {
        $sourcePath = Join-Path -Path $source_folder -ChildPath $file
        $targetPath = Join-Path -Path $target_folder -ChildPath $file

        if (Test-Path $sourcePath) {
            Copy-Item -Path $sourcePath -Destination $targetPath -Force
        }
        else {
            Write-Warning "File not found: $sourcePath"
        }
    }

    Get-ChildItem -Path $target_folder | ForEach-Object {
        $file = $($_.FullName)
        Write-Host "Signing $file" -ForegroundColor White
        & ./scripts/sign_code.cmd $file
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Error Signing, error code is $LASTEXITCODE" -ErrorAction Stop
            throw
        }
    }

    Write-Host "Success PS1 signing" -foreground Green
}

function Start-BazelSigning {
    if ($argSign -ne $true) {
        Write-Host "Skipping Bazel Signing..." -ForegroundColor Yellow
        return
    }

    Write-Host "Bazel signing..." -ForegroundColor White

    try {
        $env:BAZELISK_BASE_URL = "https://github.com/aspect-build/aspect-cli/releases/download"
        $env:USE_BAZEL_VERSION = "aspect/2025.11.0"
        &bazel build //agents/windows/plugins:all
        if ($LASTEXITCODE -eq 0) {
            $signed_dir = (&bazel info bazel-bin )
            Write-Host "Signed files are located in $signed_dir"
        }
        else {
            Write-Host "Error during signing $LASTEXITCODE"
        }
        Write-Host "Success Bazel signing" -foreground Green
    }
    catch {
        Write-Host "Exception during Bazel signing: $_" -ForegroundColor Red
    }
}


function Start-ArtifactUploading {
    if ($argMsi -ne $true) {
        Write-Host "Skipping upload to artifacts..." -ForegroundColor Yellow
        return
    }

    Write-Host "Artifact upload..." -ForegroundColor White
    $artifacts = @(
        @("$build_dir/install/Release/check_mk_service.msi", "$results_dir/check_mk_agent.msi"),
        @("$build_dir/check_mk_service/x64/Release/check_mk_service64.exe", "$results_dir/check_mk_agent-64.exe"),
        @("$build_dir/check_mk_service/Win32/Release/check_mk_service32.exe", "$results_dir/check_mk_agent.exe"),
        @("$build_dir/ohm/OpenHardwareMonitorCLI.exe", "$results_dir/OpenHardwareMonitorCLI.exe"),
        @("$build_dir/ohm/OpenHardwareMonitorLib.dll", "$results_dir/OpenHardwareMonitorLib.dll"),
        @("./install/resources/check_mk.user.yml", "$results_dir/check_mk.user.yml"),
        @("./install/resources/check_mk.yml", "$results_dir/check_mk.yml")
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
    Copy-Item $results_dir/check_mk_agent.msi $results_dir/check_mk_agent_unsigned.msi -Force
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
    & ./scripts/sign_code.cmd $results_dir\check_mk_agent.msi
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed sign MSI " $LASTEXITCODE -foreground Red
        throw
    }
    Add-HashLine $results_dir/check_mk_agent.msi $hash_file
    Invoke-Detach $argSign
    & ./scripts/call_signing_tests.cmd
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed test MSI " $LASTEXITCODE -foreground Red
        throw
    }
    Write-Host "Hash check is disabled python is missing" -foreground Red
    #& py "-3" "./scripts/check_hashes.py" "$hash_file"
    #if ($LASTEXITCODE -ne 0) {
    #    Write-Host "Failed hashing test " $LASTEXITCODE -foreground Red
    #    throw
    #}
    powershell Write-Host "MSI signing succeeded" -Foreground Green
}

function Clear-Artifacts() {
    if ($argCleanArtifacts -ne $true) {
        return
    }
    Write-Host "Cleaning artifacts..."
    $masks = "*.msi", "*.exe", "*.log", "*.yml"
    foreach ($mask in $masks) {
        Remove-Item -Path "$results_dir\$mask" -Force -ErrorAction SilentlyContinue
    }
}

function Clear-All() {
    if ($argClean -ne $true) {
        return
    }

    Write-Host "Cleaning packages..."
    Build-Package $true "cmk-agent-ctl" "Controller" "--clean"
    Build-Package $true "mk-sql" "MK-SQL" "--clean"
    Build-Package $true "mk-oracle" "mk-oracle" "--clean"

    Clear-Artifacts

    Write-Host "Cleaning $build_dir..."
    Remove-Item -Path "$build_dir" -Recurse -Force -ErrorAction SilentlyContinue
}

function Update-ArtefactDirs() {
    If (Test-Path -PathType container $results_dir) {
        Write-Host "Using results dir: '$results_dir'" -ForegroundColor White
    }
    else {
        Remove-Item $results_dir -ErrorAction SilentlyContinue     # we may have find strange files from bad scripts
        Write-Host "Creating results dir: '$results_dir'" -ForegroundColor White
        New-Item -ItemType Directory -Path $results_dir -ErrorAction Stop > nul
    }
}

function Test-MsiSigning($file) {
    if ($argSign -ne $true) {
        Write-Host "Skipping Validate signing..." -ForegroundColor Yellow
        return
    }

    Write-Host "Validate signing $file ..." -ForegroundColor White
    $random_dir = Join-Path $Env:Temp $(New-Guid); New-Item -Type Directory -Path $random_dir | Out-Null
    try{
        & 7z x "$results_dir\$file" -aoa -o"$random_dir\" *.cab > nul
        & 7z x "$random_dir\fixed.cab" -aoa -o"$random_dir\" *.exe > nul

        $exe_files = @(
            "cmk_agent_ctl.exe",
            "check_mk_svc32.exe",
            "check_mk_svc64.exe"
        )

        foreach ($exe in $exe_files) {
            Write-Host "Validate executable $exe ..." -ForegroundColor White
            $state = Get-AuthenticodeSignature -FilePath $random_dir\$exe -ErrorAction Stop
            if ($state.Status -ne "Valid") {
                Write-Host "Signature check Failed: $($state.Status) status: $($state.StatusMessage)" -ForegroundColor Red
                Write-Host "BUILD FAILED - EXITING..." -ForegroundColor Red
                throw
            }
            else {
                Write-Host "Signature check Valid"
            }
        }
    }
    catch {
        Write-Host "Failed to validate signing for $file - $_" -ForegroundColor Red
        throw
    }
    finally {
        Remove-Item -Path $random_dir -Recurse -Force -ErrorAction SilentlyContinue
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
    if ($argBuildOnly){
        $build_arg = "--build"
    }
    else
    {
        $build_arg = ""
    }

    Build-Package $argCtl "cmk-agent-ctl" "Controller" $build_arg
    if ($argSkipSqlTest -ne $true) {
        Build-Package $argSql "mk-sql" "MK-SQL" $build_arg
        Build-Package $argOracle "mk-oracle" "mk-oracle"  $build_arg
    }
    else {
        Build-Package $argSql "mk-sql" "MK-SQL" --build
        Build-Package $argOracle "mk-oracle" "mk-oracle" --build
    }
    Build-Ohm
    Build-Ext

    Start-UnitTests

    # SIGNING
    Invoke-TestSigning $usbip_exe
    Start-MsiControlBuild
    Invoke-Attach $usbip_exe "yubi-usbserver.lan.checkmk.net" "1-1.2"
    if ($argSign -eq $true) {
        $argAttached = $true
        $env:pin_cert_windows_usb | Out-File -Path .\check-signing-param.txt  -Append
    }
    Start-BinarySigning
    Start-BazelSigning
    Build-MSI
    Set-Msi-Version
    Start-ArtifactUploading
    Start-MsiPatching
    Start-MsiSigning
    Test-MsiSigning "check_mk_agent.msi"
    Test-MsiSigning "check_mk_agent_unsigned.msi"

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
