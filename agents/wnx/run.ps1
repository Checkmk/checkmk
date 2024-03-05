# PowerShell script equivalent to the provided batch script

# Check for arguments and set flags
$argAll = $false
$argClean = $false
$argSetup = $false
$argFormat = $false
$argCheckFormat = $false
$argCtl = $false
$argBuild = $false
$argTest = $false
$argSign = $false
$argMsi = $false
$argOhm = $false
$argExt = $false
$argSql = $false
$argDoc = $false
$argDetach = $false
$argSignFile = $null
$argSignSecret = $null

$msbuild_exe = "C:\Program Files\Microsoft Visual Studio\2022\Professional\MSBuild\Current\Bin\msbuild.exe"
$arte = "$pwd/../../artefacts"
$build_dir = "$pwd/build"
$ohm_dir = "$build_dir/ohm/"

if ("$env:arg_var_value" -eq "") {
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
    Write-Host "  -A, --all            shortcut to -S -B -E -C -T -M:  setup, build, ctl, ohm, unit, msi, extensions"
    Write-Host "  -c, --clean          clean artifacts"
    Write-Host "  -S, --setup          check setup"
    Write-Host "  -C, --ctl            build controller"
    Write-Host "  -D, --documentation  create documentation"
    Write-Host "  -f, --format         format sources"
    Write-Host "  -F, --check-format   check for correct formatting"
    Write-Host "  -B, --build          build controller"
    Write-Host "  -M, --msi            build msi"
    Write-Host "  -O, --ohm            build ohm"
    Write-Host "  -E, --extensions     build extensions"
    Write-Host "  -T, --test           run unit test controller"
    Write-Host "  --sign file secret   sign controller with file in c:\common and secret"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host ""
    Write-Host "$name --ctl"
    Write-Host "$name --build --test"
    Write-Host "$name --build -T --sign the_file secret"
    Write-Host "$name -A"
}


if ($args.Length -eq 0) {
    Write-Host "No arguments provided. Running with default flags." -ForegroundColor Yellow
    $argAll = $true
}
else {
    for ($i = 0; $i -lt $args.Length; $i++) {
        switch ($args[$i]) {
            { $("-h", "--help") -contains "$_" } { Write-Help; return }
            { $("-A", "--all") -contains $_ } { $argAll = $true }
            { $("-c", "--clean") -contains $_ } { $argClean = $true }
            { $("-S", "--setup") -contains $_ } { $argSetup = $true }
            { $("-f", "--format") -contains $_ } { $argFormat = $true }
            { $("-F", "--check-format") -contains $_ } { $argCheckFormat = $true }
            { $("-C", "--controller") -contains $_ } { $argCtl = $true }
            { $("-B", "--build") -contains $_ } { $argBuild = $true }
            { $("-M", "--msi") -contains $_ } { $argMsi = $true }
            { $("-O", "--ohm") -contains $_ } { $argOhm = $true }
            { $("-Q", "--mk-sql") -contains $_ } { $argSql = $true }
            { $("-E", "--extensions") -contains $_ } { $argExt = $true }
            { $("-T", "--test") -contains $_ } { $argTest = $true }
            { $("-D", "--documentation") -contains $_ } { $argDoc = $true }
            "--detach" { $argDetach = $true }
            "--var" {
                [Environment]::SetEnvironmentVariable($args[++$i], $args[++$i])
            }
            "--sign" { 
                $argSign = $true
                $argSignFile = $args[++$i]
                $argSignSecret = $args[++$i]
            }
        }
    }
}


if ($argAll) {
    $argCtl = $true
    $argBuild = $true
    $argTest = $true
    $argSetup = $true
    $argOhm = $true
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

function Get-Version {
    $first_line = Get-Content -Path "include\common\wnx_version.h" -TotalCount 1
    if ($first_line.Substring(0, 29) -eq "#define CMK_WIN_AGENT_VERSION") {
        return $first_line.Substring(30, $first_line.Length - 30)
    }
    else {
        Write-Host "wnx_version not found in include\common\wnx_version.h" -ForegroundColor Red
        exit 12
    }
}

function Clear-Artifacts( [String]$arte) {
    Write-Host "Cleaning artifacts..."
    $masks = "*.msi", "*.exe", "*.log", "*.yml"
    foreach ($mask in $masks) {
        Remove-Item -Path "$arte\$mask" -Force -ErrorAction SilentlyContinue
    }
}

function Build-Agent {
    Write-Host "Building agent..." -ForegroundColor White
    $make_exe = where.exe make | Out-String
    $env:make_exe = $make_exe.trim()
    Write-Host make is $env:make_exe 
    try {
        Write-Host "Start build" -ForegroundColor White
        & "$PSScriptRoot\parallel.ps1"
        if ($lastexitcode -ne 0) {
            Write-Host "Error building 2: " $lastexitcode -ForegroundColor Red
            Exit 55
        }
    }
    catch {
        Write-Host "Error building 1: " $result -ForegroundColor Red
        Exit 55
    }

    Write-Host "Success building agent" -ForegroundColor Green
}

function Build-Controller {
    Write-Host "Building controller..." -ForegroundColor White
    $cwd = Get-Location
    Set-Location "../../packages/mk-sql"
    & ./run.cmd --all
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error building controller: " $LASTEXITCODE -foreground Red
    }
    else {
        Write-Host "Success building controller" -foreground Green
    }
    Set-Location $cwd
}

function Build-Ext {
    Write-Host "Building Ext..." -ForegroundColor White
    $cwd = Get-Location
    Set-Location "extensions\robotmk_ext"
    & ../../scripts/cargo_build_robotmk.cmd
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error building Ext: " $LASTEXITCODE -foreground Red
    }
    else {
        Write-Host "Success building Ext" -foreground Green
    }
    Set-Location $cwd
}

function Build-OHM {
    Write-Host "Building OHM..." -ForegroundColor White

    Write-Host "Building OHM" -Foreground White
    Write-Host $ohm_dir
    & $msbuild_exe .\ohm\ohm.sln "/p:OutDir=$ohm_dir;TargetFrameworkVersion=v4.6;Configuration=Release"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error building OHM: " $LASTEXITCODE -foreground Red
        exit 44
    }
    else {
        Write-Host "Success building OHM" -foreground Green
        try {
            Copy-Item "$ohm_dir/OpenHardwareMonitorLib.dll" $arte -Force    
            Copy-Item "$ohm_dir/OpenHardwareMonitorCLI.exe" $arte -Force
        }
        catch {
            Write-Host "Error copy files '$_'" -foreground Red
            exit 43
        }
    }
}

function Build-MSI {
    Write-Host "Building MSI..." -ForegroundColor White
    Remove-Item "$build_dir/install/Release/check_mk_service.msi" -Force

    & $msbuild_exe wamain.sln "/t:install" "/p:Configuration=Release,Platform=x86"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error building MSI: " $LASTEXITCODE -foreground Red
        exit 42
    }
    else {
        Write-Host "Success building MSI" -foreground Green
    }
}

function Set-MSI-Version {
    $version = Get-Version
    $version_base = $version.substring(1, $version.length - 2)
    Write-Host "Setting MSI version: $version_base" -ForegroundColor White
    Change-MsiProperties $build_dir\install\Release\check_mk_service.msi $version_base    
    # deprecated
    # & echo cscript.exe //nologo scripts\WiRunSQL.vbs $build_dir\install\Release\check_mk_service.msi "UPDATE `Property` SET `Property`.`Value`='$version_base' WHERE `Property`.`Property`='ProductVersion'"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error setting version MSI: " $LASTEXITCODE -foreground Red
        exit 42
    }
    else {
        Write-Host "Success setting version MSI" -foreground Green
    }
}

function Start-Unit-Tests {
    Write-Host "Running unit tests..." -ForegroundColor White

    & net stop WinRing0_1_2_0
    Copy-Item $build_dir/watest/Win32/Release/watest32.exe $arte -Force
    Copy-Item $build_dir/watest/x64/Release/watest64.exe $arte -Force
    & ./call_unit_tests.cmd -*_Simulation:*Component:*ComponentExt:*Flaky
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error in unit tests " $LASTEXITCODE -foreground Red
        exit 42
    }
    else {
        Write-Host "Success unittests" -foreground Green
    }
}


# Implement other flags and functionality as needed...

# Example of getting start time
$mainStartTime = Get-Date

Invoke-CheckApp "choco" "choco -v"
Invoke-CheckApp "perl" "perl -v"
Invoke-CheckApp "make" "make -v"
Invoke-CheckApp "msvc" "& ""$msbuild_exe"" --version"
Invoke-CheckApp "is_crlf" "python .\scripts\check_crlf.py"

if ($argClean) {
    Clear-Artifacts $arte
}

if ($argBuild) {
    $env:msbuild_exe = $msbuild_exe
    $env:wnx_version = Get-Version
    Write-Host "Used version: $env:wnx_version"
    Build-Agent
}
else {
    Write-Host "Skipping Agent build..." -ForegroundColor Yellow
}

if ($argCtl) {
    Build-Controller
}
else {
    Write-Host "Skipping controller build..." -ForegroundColor Yellow
}

if ($argOhm) {
    Build-Ohm
}
else {
    Write-Host "Skipping OHM build..." -ForegroundColor Yellow
}

if ($argExt) {
    Build-Ext
}
else {
    Write-Host "Skipping Ext build..." -ForegroundColor Yellow
}

if ($argMsi) {
    Build-MSI
    Set-Msi-Version
}
else {
    Write-Host "Skipping Ext build..." -ForegroundColor Yellow
}

if ($argTest) {
    Start-Unit-Tests
}
else {
    Write-Host "Skipping Unit testing..." -ForegroundColor Yellow
}



# Example of calculating elapsed time
$endTime = Get-Date
$elapsedTime = $endTime - $mainStartTime
Write-Host "Elapsed time: $($elapsedTime.Hours):$($elapsedTime.Minutes):$($elapsedTime.Seconds)"


# This script provides a framework to get you started with translating your batch script to PowerShell.
# You will need to fill in the implementation details for your specific requirements.
