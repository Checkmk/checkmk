#!/usr/bin/env pwsh
# Copyright (C) 2025 Checkmk GmbH
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

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
$cargo_toolchain = "1.90.0" # to be in sync with rust toolchain/bazel/etc
$cargo_target = "x86_64-pc-windows-msvc"

$packBuild = $false
$packClippy = $false
$packFormat = $false
$packCheckFormat = $false
$packTest = $false
$packDoc = $false
$packOci = $false

# repo/branch specific short path
# TODO(sk): move it to CI upon confirmation that screen works as intended
$shortenPath = "workdir\workspace\checkmk\2.5.0"
$shortenLink = "y5"

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
    Write-Host "  -A, --all            shortcut to -B -C -T -F:  build, clippy, test, check format"
    Write-Host "  --clean              clean"
    Write-Host "  -C, --clippy         run  $package_name clippy"
    Write-Host "  -D, --documentation  create  $package_name documentation"
    Write-Host "  -f, --format         format  $package_name sources"
    Write-Host "  -F, --check-format   check for  $package_name correct formatting"
    Write-Host "  -B, --build          build binary $package_name"
    Write-Host "  -T, --component-tests execute  $package_name component tests"
    Write-Host "  -O, --oci            repackage Oracle Instant Client"
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
            { $("-T", "--component-tests") -contains $_ } { $packTest = $true }
            { $("-D", "--documentation") -contains $_ } { $packDoc = $true }
            { $("-O", "--oci") -contains $_ } { $packOci = $true }
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


function Invoke-Cargo-With-Explicit-Package {
    param(
        [Parameter(
            Mandatory = $True,
            Position = 0
        )]
        $cmd,
        [Parameter(
            Mandatory = $False,
            ValueFromRemainingArguments = $true,
            Position = 1
        )]
        $further_args
    )
    $further_args_string = $further_args -join ' '
    Write-Host "${package_name}: $cmd --package $package_name $further_args_string" -ForegroundColor White
    & cargo $cmd  --package $package_name $further_args

    if ($LASTEXITCODE -ne 0) {
        Write-Error "${package_name}: Failed to $cmd --package $package_name $further_args_string with code $LASTEXITCODE" -ErrorAction Stop
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
    &rustup target add $cargo_target --toolchain $cargo_toolchain
    & rustc --target $cargo_target -V
    & cargo -V

    # shorten path
    Start-ShortenPath "$shortenLink" "$shortenPath"
    Update-Dirs

    if ($packClean) {
        Invoke-Cargo-With-Explicit-Package "clean"
    }
    if ($packBuild -or $packTest -or - $packOci) {
        $target = "//omd/packages/oci:oci_light_win_x64"
        $env:BAZELISK_BASE_URL = "https://github.com/aspect-build/aspect-cli/releases/download"
        $env:USE_BAZEL_VERSION = "aspect/2025.11.0"
        & bazel build $target
        if ($LASTEXITCODE -eq 0) {
            $oci_light_win_x64_zip = (& bazel cquery $target --output=starlark  --starlark:expr='target.files.to_list()[0].path' )
            $packaged = Split-Path "$oci_light_win_x64_zip" -leaf
            Write-Host "Oracle runtime light/win/x64: $oci_light_win_x64_zip with name $packaged" -ForegroundColor Green
            Copy-Item -Path "$root_dir/$oci_light_win_x64_zip" -Destination "$arte_dir/" -Force -ErrorAction Stop
            $source_hash = (Get-FileHash "$arte_dir/$packaged" -Algorithm SHA256).Hash
            $runtime_path = "runtimes/plugins/packages/mk-oracle/runtime"
            & mkdir "$runtime_path" -ErrorAction SilentlyContinue | Out-Null
            if (!(Test-Path "$runtime_path/.hash") -or
                ((Get-Content "$runtime_path/.hash" -ErrorAction Stop) -ne $source_hash)) {
                Write-Host "Oracle runtime light/win/x64: hash updated $source_hash" -ForegroundColor Green
                Set-Content "$runtime_path/.hash" $source_hash -ErrorAction Stop
            }
            Expand-Archive -Path "$arte_dir/$packaged" -DestinationPath "$runtime_path" -Force -ErrorAction Stop
        }
        else {
            Write-Host "Failed Oracle runtime light/win/x64: $oci_light_win_x64" -ForegroundColor Red
            exit(1)
        }
    }
    if ($packBuild) {
        $cwd = Get-Location
        $target_dir = Join-Path (cargo metadata --no-deps | ConvertFrom-json).target_directory "$cargo_target"
        Write-Host "Killing processes in $target_dir" -ForegroundColor White
        Get-Process | Where-Object { $_.path -and ($_.path -like "$target_dir\*") } | Stop-Process -Force
        Invoke-Cargo-With-Explicit-Package "build" "--release" "--target" $cargo_target
        $exe_dir = Join-Path (cargo metadata --no-deps | ConvertFrom-json).target_directory "$cargo_target" "release"
        Write-Host "Uploading artifacts: [ $exe_dir/$exe_name -> $arte_dir/$exe_name ] ..." -Foreground White
        Copy-Item $exe_dir/$exe_name $arte_dir/$exe_name -Force -ErrorAction Stop
    }
    if ($packClippy) {
        Invoke-Cargo-With-Explicit-Package "clippy" "--release" "--tests" "--" "--deny" "warnings"
    }

    if ($packFormat) {
        Invoke-Cargo-With-Explicit-Package "fmt"
    }

    if ($packCheckFormat) {
        Invoke-Cargo-With-Explicit-Package "fmt" "--" "--check"
    }
    if ($packTest) {
        # for local test you may add this
        # $env:CI_ORA1_DB_TEST="localhost:SYS:Oracle-dba:1521:XE:sysdba::_:_:"
        Write-Host "Component test!" -Foreground White
        if ($env:CI_ORA2_DB_TEST_PASSWORD -eq "") {
            Write-Host "CI_ORA2_DB_TEST_PASSWORD is absent, component testing may fail" -ForegroundColor Red
        }
        $pass = $env:CI_ORA2_DB_TEST_PASSWORD
        $env:CI_ORA2_DB_TEST = "ora-rocktest.dev.checkmk.net:system:${pass}:1521:FREE::FREE.cmkoratest:_:_:"
        Write-Host "CI_ORA2_DB_TEST set from CI_ORA2_DB_TEST_PASSWORD" -ForegroundColor Green
        Invoke-Cargo-With-Explicit-Package "test" "--release" "--target" $cargo_target  "--" "--test-threads=4"
    }
    if ($packDoc) {
        Invoke-Cargo-With-Explicit-Package "doc"
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
