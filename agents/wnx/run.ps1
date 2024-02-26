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
$arte = "$pwd\..\..\artefacts"
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
            { $("-T". "---test") -contains $_ } { $argTest = $true }
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
if ($argExt) {
    Write-Host "Cleaning..."
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

function Set-Version() {
    $first_line = Get-Content -Path "include\common\wnx_version.h" -TotalCount 1
    if ($first_line.Substring(0, 29) -eq "#define CMK_WIN_AGENT_VERSION") {
        $env:wnx_version = $first_line.Substring(30, $first_line.Length - 30)
        Write-Host "Used version: $env:wnx_version"
    }
    else {
        Write-Host "wnx_version not found in include\common\wnx_version.h" -ForegroundColor Red
    }
}

function Clear-Artifacts( [String]$arte) {
    Write-Host "Cleaning artifacts..."
    $masks = "*.msi", "*.exe", "*.log", "*.yml"
    foreach ($mask in $masks) {
        Remove-Item -Path "$arte\$mask" -Force -ErrorAction SilentlyContinue
    }
}

function Build-Project {
    # Build project
    Write-Host "Building project..."
    $make_exe = where.exe make | Out-String
    $env:make_exe = $make_exe.trim()
    Write-Host make is $env:make_exe 
    & ".\msb.ps1"
}

# Conditional execution based on arguments
if ($argAll) {
    # If --all is specified, set all relevant flags to true
    $argSetup = $true
    $argBuild = $true
    $argTest = $true
    $argMsi = $true
    $argOhm = $true
    $argExt = $true
}


# Implement other flags and functionality as needed...

# Example of getting start time
$mainStartTime = Get-Date

Invoke-CheckApp "choco" "choco -v"
Invoke-CheckApp "perl" "perl -v"
Invoke-CheckApp "make" "make -v"
Invoke-CheckApp "msvc" "&""$msbuild_exe"" --version"
Invoke-CheckApp "is_crlf" "python .\scripts\check_crlf.py"

if ($argClean) {
    Clear-Artifacts $arte
}

if ($argBuild) {
    Write-Host "Building Agent..." -ForegroundColor White
    $env:msbuild_exe = $msbuild_exe
    Set-Version
    Build-Project
}
else {
    Write-Host "Skipping Agent build..." -ForegroundColor Yellow
}





# Example of calculating elapsed time
$endTime = Get-Date
$elapsedTime = $endTime - $mainStartTime
Write-Host "Elapsed time: $($elapsedTime.Hours):$($elapsedTime.Minutes):$($elapsedTime.Seconds)"


# This script provides a framework to get you started with translating your batch script to PowerShell.
# You will need to fill in the implementation details for your specific requirements.
