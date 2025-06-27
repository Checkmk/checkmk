#!/usr/bin/env pwsh
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# This is adaptation of our standard run script to Windows reality
# Most noticeble change are artifacts upload and path shortening

# CI uses normally path d:\workspace\checkmk\master\checkout as a root to repo
# we add link d:\y to d:\workspace\checkmk\master\
# and as sctipt to use path d:\y\checkout
# The reason is inability of Windows to handle very long paths especially when
# we have to build  OpenSSL for Rust


Write-Host "run script starts" -ForegroundColor Gray

if ((get-host).version.major -lt 7) {
    Write-Host "PowerShell version 7 or higher is required." -ForegroundColor Red
    exit
}

$package_name = Split-Path -Path (Get-Location) -Leaf

$exe_name = "$package_name.exe"
$work_dir = "$pwd"
$cargo_target = "i686-pc-windows-msvc"

$packBuild = $false
$packClippy = $false
$packFormat = $false
$packCheckFormat = $false
$packTest = $false
$packDoc = $false

# repo/branch specific short path
# TODO(sk): move it to CI upon confirmation that screen works as intended
$shortenPath = "workdir\workspace\checkmk\master"
$shortenLink = "ym"

if ("$env:arg_var_value" -ne "") {
    $env:arg_val_name = $env:arg_var_value
}
else {
    $env:arg_val_name = ""
}

function Write-Help() {
    $x = Get-Item $PSCommandPath
    $x.BaseName
    $name = "pwsh -File " + $x.BaseName + ".ps1"

    Write-Host "Usage:"
    Write-Host ""
    Write-Host "$name [arguments]"
    Write-Host ""
    Write-Host "Available arguments:"
    Write-Host "  -?, -h, --help       display help and exit"
    Write-Host "  -A, --all            shortcut to -B -C -T -F:  build, cluippy, test, check format"
    Write-Host "  --clean              clean"
    Write-Host "  -C, --clippy         run  $package_name clippy"
    Write-Host "  -D, --documentation  create  $package_name documentation"
    Write-Host "  -f, --format         format  $package_name sources"
    Write-Host "  -F, --check-format   check for  $package_name correct formatting"
    Write-Host "  -B, --build          build binary $package_name"
    Write-Host "  -T, --test           run  $package_name unit tests"
    Write-Host "  --shorten link path  change dir from current using link"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host ""
    Write-Host "$name --clippy"
    Write-Host "$name --build --test"
    Write-Host "$name --shorten y workspace\checkout"
}


if ($args.Length -eq 0) {
    Write-Host "No arguments provided. Running with default flags." -ForegroundColor Yellow
    $packAll = $true
}
else {
    for ($i = 0; $i -lt $args.Length; $i++) {
        switch ($args[$i]) {
            { $("-?", "-h", "--help") -contains "$_" } { Write-Help; return }
            { $("-A", "--all") -contains $_ } { $packAll = $true }
            { $("-f", "--format") -contains $_ } { $packFormat = $true }
            { $("-F", "--check-format") -contains $_ } { $packCheckFormat = $true }
            { $("-B", "--build") -contains $_ } { $packBuild = $true }
            { $("-C", "--clippy") -contains $_ } { $packClippy = $true }
            { $("-T", "--test") -contains $_ } { $packTest = $true }
            { $("-D", "--documentation") -contains $_ } { $packDoc = $true }
            "--clean" { $packClean = $true }
            "--var" {
                [Environment]::SetEnvironmentVariable($args[++$i], $args[++$i])
            }
            "--shorten" { 
                $shortenLink = $args[++$i] 
                $shortenPath = $args[++$i] 
            }
        }
    }
}


if ($packAll) {
    $packBuild = $true
    $packClippy = $true
    $packCheckFormat = $true
    $packTest = $true
}


function Start-ShortenPath($tgt_link, $path) {
    if ($tgt_link -eq "" -and $path -eq "") {
        Write-Host "No path shortening $tgt_link $path" -ForegroundColor Yellow
        return
    }

    [string]$inp = Get-Location
    [string]$new = $inp.tolower().replace($path, $tgt_link)
    if ($new.tolower() -eq $inp) {
        Write-Host "Can't shorten path $inp doesn't contain $path" -ForegroundColor Yellow
        return
    }
    Write-Host "propose to shorten to: $new ($path, $tgt_link)"
    try {
        Set-Location $new -ErrorAction Stop
        Write-Host "current dir $pwd" -ForegroundColor White
    }
    catch {
        Write-Host "Failed to shorten path, $new doesn't exist" -ForegroundColor Yellow
    }
}


function Invoke-Cargo($cmd) {
    Write-Host "$cmd $package_name" -ForegroundColor White
    & cargo $cmd

    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to $cmd $package_name with code $LASTEXITCODE" -ErrorAction Stop
    }
}

function Invoke-Cargo($cmd) {
    Write-Host "$cmd $package_name" -ForegroundColor White
    & cargo $cmd

    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to $cmd $package_name with code $LASTEXITCODE" -ErrorAction Stop
    }
}

function Test-Administrator {  
    [OutputType([bool])]
    param()
    process {
        [Security.Principal.WindowsPrincipal]$user = [Security.Principal.WindowsIdentity]::GetCurrent();
        return $user.IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator);
    }
}

function Update-Dirs() {
    $root_dir = "$pwd"
    While (!(Test-Path "$root_dir/.werks" -ErrorAction SilentlyContinue)) {
        $root_dir = Split-Path -Parent $root_dir -ErrorAction Stop
        if ($root_dir -eq "") {
            Write-Error "Not found repo root"  -ErrorAction Stop
        }
    }
    $global:root_dir = $root_dir
    Write-Host "Found root dir: '$global:root_dir'" -ForegroundColor White

    $arte_dir = "$root_dir/artefacts"
    If (!(Test-Path -PathType container $arte_dir)) {
        Remove-Item $arte_dir -ErrorAction SilentlyContinue     # we may have find strange files from bad scripts
        Write-Host "Creating output dir: '$arte_dir'" -ForegroundColor White
        New-Item -ItemType Directory -Path $arte_dir -ErrorAction Stop > nul
    }
    $global:arte_dir = "$arte_dir"
    Write-Host "Using output dir: '$global:arte_dir'" -ForegroundColor White
}

$result = 1
try {
    $mainStartTime = Get-Date

    & rustup --version > nul
    if ($LASTEXITCODE -ne 0) {
        Write-Error "rustup not found, please install it and/or add to PATH" -ErrorAction Stop
    }
    &rustup update
    &rustup install
    &rustup target add $cargo_target
    & rustc --target $cargo_target -V
    & cargo -V

    # Disable assert()s in C/C++ parts (e.g. wepoll-ffi), they map to _assert()/_wassert(),
    # which is not provided by libucrt. The latter is needed for static linking.
    # https://github.com/rust-lang/cc-rs#external-configuration-via-environment-variables
    $env:CFLAGS = "-DNDEBUG"

    # shorten path
    Start-ShortenPath "$shortenLink" "$shortenPath"
    Update-Dirs

    if ($packClean) {
        Invoke-Cargo "clean"
    }
    if ($packBuild) {
        $cwd = Get-Location
        $target_dir = Join-Path (cargo metadata --no-deps | ConvertFrom-json).target_directory "$cargo_target"
        Write-Host "Killing processes in $target_dir" -ForegroundColor White
        Get-Process | Where-Object { $_.path -and ($_.path -like "$target_dir\*") } | Stop-Process -Force
        &cargo build --release --target $cargo_target
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Failed to build $package_name with code $LASTEXITCODE" -ErrorAction Stop
        }
    }
    if ($packClippy) {
        &cargo clippy --release --target $cargo_target --tests -- --deny warnings
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Failed to clippy $package_name with code $LASTEXITCODE" -ErrorAction Stop
        }
    }

    if ($packFormat) {
        Invoke-Cargo "fmt"
    }

    if ($packCheckFormat) {
        Write-Host "test format $package_name" -ForegroundColor White
        cargo fmt -- --check
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Failed to test format $package_name" -ErrorAction Stop
        }
    }
    if ($packTest) {
        if (-not (Test-Administrator)) {
            Write-Error "Testing must be executed as Administrator." -ErrorAction Stop
        }
        cargo test --release --target $cargo_target -- --test-threads=4
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Failed to test $package_name" -ErrorAction Stop
        }
    }
    if ($packBuild -and $packTest -and $packClippy) {
        $exe_dir = Join-Path (cargo metadata --no-deps | ConvertFrom-json).target_directory "$cargo_target" "release"
        Write-Host "Uploading artifacts: [ $exe_dir/$exe_name -> $arte_dir/$exe_name ] ..." -Foreground White
        Copy-Item $exe_dir/$exe_name $arte_dir/$exe_name -Force -ErrorAction Stop
    }
    if ($packDoc) {
        Invoke-Cargo "doc"
    }

    Write-Host "SUCCESS" -ForegroundColor Green
    $result = 0
}
catch {
    Write-Host "Error: " $_ -ForegroundColor Red
    Write-Host "Trace stack: " -ForegroundColor Yellow
    Write-Host $_.ScriptStackTrace -ForegroundColor Yellow
}
finally {
    Write-Host "Restore path to $work_dir" -ForegroundColor White
    Set-Location $work_dir
    $endTime = Get-Date
    $elapsedTime = $endTime - $mainStartTime
    Write-Host "Elapsed time: $($elapsedTime.Hours):$($elapsedTime.Minutes):$($elapsedTime.Seconds)"
    Write-Host "run script starts" -ForegroundColor Gray
}


exit $result
