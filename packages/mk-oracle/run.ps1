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

if ((Get-Host).version.major -lt 7) {
    Write-Host "PowerShell version 7 or higher is required." -ForegroundColor Red
    exit
}

$package_name = Split-Path -Path (Get-Location) -Leaf

$exe_name = "$package_name.exe"
$work_dir = "$pwd"
$cargo_toolchain = "1.94.1" # to be in sync with rust toolchain/bazel/etc
$cargo_target = "x86_64-pc-windows-msvc"

# Test database endpoints: constants shared with the bash runners.
$db_endpoints = @{}
Get-Content "$PSScriptRoot/test-db-endpoints.conf" -ErrorAction Stop | ForEach-Object {
    if ($_ -match '^([a-z0-9_]+)=(.*)$') { $db_endpoints[$Matches[1]] = $Matches[2] }
}

# Export CI_ORA2_DB_TEST for the component tests: the PowerShell port of
# resolve_test_endpoint in db-endpoint.sh. A pre-set CI_ORA2_DB_TEST is
# used verbatim; otherwise the CI endpoint is constructed from
# CI_ORA_TEST_PASSWORD.
function Resolve-TestDbEndpoint {
    if ([string]::IsNullOrEmpty($env:CI_ORA2_DB_TEST)) {
        if ([string]::IsNullOrEmpty($env:CI_ORA_TEST_PASSWORD)) {
            throw ("no test database configured; either set CI_ORA2_DB_TEST (full endpoint) " +
                "or CI_ORA_TEST_PASSWORD (CI database)")
        }
        $e = $db_endpoints
        $env:CI_ORA2_DB_TEST = "$($e.ci_host):$($e.ci_user):$($env:CI_ORA_TEST_PASSWORD):" +
        "$($e.ci_port):$($e.ci_instance)::$($e.ci_service):$($e.ci_sid):_:"
    }
    $endpoint_host = $env:CI_ORA2_DB_TEST.Split(':')[0]
    Write-Host "component tests use the database at $endpoint_host" -ForegroundColor Green
}

# Remote host for the local-connection component tests (--remote-host).
# The test binary is shipped to this Windows Oracle host and run there against
# localhost, exercising local sysdba connections and registry-based instance
# discovery that the network model never touches. All overridable from CI;
# defaults describe the ORACLE-WIN-CI VM (see tests/README.md).
$remote_host = if ($env:CI_ORA_WIN_REMOTE_HOST) { $env:CI_ORA_WIN_REMOTE_HOST } else { "oracle-win-ci.lan.checkmk.net" }
$remote_user = if ($env:CI_ORA_WIN_REMOTE_USER) { $env:CI_ORA_WIN_REMOTE_USER } else { "administrator" }
$remote_dir = if ($env:CI_ORA_WIN_REMOTE_DIR) { $env:CI_ORA_WIN_REMOTE_DIR } else { "C:\ci\mk-oracle-test" }
$remote_oracle_home = if ($env:CI_ORA_WIN_ORACLE_HOME) { $env:CI_ORA_WIN_ORACLE_HOME } else { "C:\oracle\26ai\dbhomeFree" }
# DB host as seen from the VM. The listeners bind the host address, not loopback,
# so the on-VM connection must use the host name (or IP), never "localhost".
$remote_db_host = if ($env:CI_ORA_WIN_DB_HOST) { $env:CI_ORA_WIN_DB_HOST } else { "oracle-win-ci" }

$packBuild = $false
$packClippy = $false
$packFormat = $false
$packCheckFormat = $false
$packTest = $false
$packRemoteTest = $false
$packDoc = $false
$packOci = $false

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
    Write-Host "  -A, --all            shortcut to -B -C -T -F:  build, clippy, test, check format"
    Write-Host "  --clean              clean"
    Write-Host "  -C, --clippy         run  $package_name clippy"
    Write-Host "  -D, --documentation  create  $package_name documentation"
    Write-Host "  -f, --format         format  $package_name sources"
    Write-Host "  -F, --check-format   check for  $package_name correct formatting"
    Write-Host "  -B, --build          build binary $package_name"
    Write-Host "  -T, --component-tests execute  $package_name component tests"
    Write-Host "  -R, --remote-host    run component tests on the remote Oracle host (localhost DB)"
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
            { $("-R", "--remote-host") -contains $_ } { $packRemoteTest = $true }
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
    while (!(Test-Path "$root_dir/.werks" -ErrorAction SilentlyContinue)) {
        $root_dir = Split-Path -Parent $root_dir -ErrorAction Stop
        if ($root_dir -eq "") {
            Write-Error "Not found repo root"  -ErrorAction Stop
        }
    }
    $global:root_dir = $root_dir
    Write-Host "Found root dir: '$global:root_dir'" -ForegroundColor White

    $arte_dir = "$root_dir/artefacts"
    if (!(Test-Path -PathType container $arte_dir)) {
        Remove-Item $arte_dir -ErrorAction SilentlyContinue     # we may have find strange files from bad scripts
        Write-Host "Creating output dir: '$arte_dir'" -ForegroundColor White
        New-Item -ItemType Directory -Path $arte_dir -ErrorAction Stop > nul
    }
    $global:arte_dir = "$arte_dir"
    Write-Host "Using output dir: '$global:arte_dir'" -ForegroundColor White
}

function Invoke-RemoteComponentTest {
    # Build the Windows test binaries, ship them to the Oracle host, and run
    # them there against the host's own DB. Registry-based instance discovery
    # only works on a machine with an Oracle installation.
    if ([string]::IsNullOrEmpty($env:CI_ORA_WIN_TEST_PASSWORD)) {
        Write-Error "CI_ORA_WIN_TEST_PASSWORD is absent, remote component testing cannot run" -ErrorAction Stop
    }
    $pass = $env:CI_ORA_WIN_TEST_PASSWORD
    $target = "$remote_user@$remote_host"

    # Non-interactive SSH. CI must authenticate with a key (point
    # CI_ORA_WIN_SSH_KEYFILE at it); interactive local runs may omit it and rely
    # on an already-open agent/ControlMaster session.
    $ssh_opts = @("-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=accept-new")
    $ssh_keyfile = $null
    if (-not [string]::IsNullOrEmpty($env:CI_ORA_WIN_SSH_KEYFILE)) {
        # Windows OpenSSH rejects key files with permissive ACLs, and Jenkins
        # materialises the credential with inherited workspace permissions, so
        # use a private copy restricted to the current user.
        $ssh_keyfile = Join-Path ([System.IO.Path]::GetTempPath()) "mk-oracle-ssh-key-$PID"
        Copy-Item $env:CI_ORA_WIN_SSH_KEYFILE $ssh_keyfile -Force
        & icacls $ssh_keyfile /inheritance:r /grant:r "$($env:USERNAME):R" | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Failed to restrict ACL on $ssh_keyfile" -ErrorAction Stop
        }
        $ssh_opts += @("-i", $ssh_keyfile)
    }

    # 1. Build the component-test binaries for the Windows target without running them.
    Invoke-Cargo-With-Explicit-Package "test" "--release" "--target" $cargo_target "--no-run"
    $deps_dir = Join-Path (cargo metadata --no-deps | ConvertFrom-Json).target_directory (Join-Path $cargo_target "release" "deps")
    $test_exes = foreach ($name in @("test_ora_no_db", "test_ora_discovery", "test_ora_with_db")) {
        $exe = Get-ChildItem -Path $deps_dir -Filter "$name-*.exe" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($null -eq $exe) {
            Write-Error "No $name-*.exe found in $deps_dir" -ErrorAction Stop
        }
        Write-Host "Remote component test binary: $($exe.FullName)" -ForegroundColor White
        $exe
    }
    $exe_list = ($test_exes | ForEach-Object { "'$($_.Name)'" }) -join ", "

    # 2. Generate the remote runner. Endpoints resolve to the co-located DB via
    #    $remote_db_host, using the installed Oracle client via ORACLE_HOME; the
    #    binaries resolve fixtures and TNS_ADMIN relative to their working dir.
    #    CI_ORA2 connects as system, CI_ORA1 as sys/sysdba.
    #    Field order: host:user:pass:port:instance:role:service:sid:_:_
    $conn_ref = "${remote_db_host}:system:${pass}:1521:_::FREE:FREE:_:"
    $conn_secondary = "${remote_db_host}:sys:${pass}:1521:_:sysdba:FREE:FREE:_:"
    $remote_script = Join-Path ([System.IO.Path]::GetTempPath()) "mk-oracle-remote-run.ps1"
    @"
`$ErrorActionPreference = "Stop"
Set-Location -Path `$PSScriptRoot
`$env:ORACLE_HOME = "$remote_oracle_home"
`$env:PATH = "`$env:ORACLE_HOME\bin;`$env:PATH"
# test_environment asserts this Windows build flag also at run time
`$env:CFLAGS = "-DNDEBUG"
`$env:CI_ORA2_DB_TEST = "$conn_ref"
`$env:CI_ORA1_DB_TEST = "$conn_secondary"
foreach (`$exe in @($exe_list)) {
    & "`$PSScriptRoot\`$exe" --test-threads=4
    if (`$LASTEXITCODE -ne 0) { exit `$LASTEXITCODE }
}
exit 0
"@ | Set-Content -Path $remote_script -Encoding utf8BOM

    try {
        # 3. Stage binaries, fixtures and runner on the remote host.
        & ssh @ssh_opts $target "powershell -NoProfile -Command `"New-Item -ItemType Directory -Force -Path '$remote_dir\tests' | Out-Null`""
        if ($LASTEXITCODE -ne 0) { Write-Error "Failed to create remote dir on $target" -ErrorAction Stop }
        foreach ($exe in $test_exes) {
            & scp @ssh_opts $exe.FullName "${target}:$remote_dir/"
            if ($LASTEXITCODE -ne 0) { Write-Error "Failed to copy $($exe.Name)" -ErrorAction Stop }
        }
        & scp @ssh_opts -r "tests/files" "${target}:$remote_dir/tests/"
        if ($LASTEXITCODE -ne 0) { Write-Error "Failed to copy test fixtures" -ErrorAction Stop }
        # The runtime-detection tests probe the factory runtime tree relative
        # to their working directory.
        & scp @ssh_opts -r "runtimes" "${target}:$remote_dir/"
        if ($LASTEXITCODE -ne 0) { Write-Error "Failed to copy factory runtimes" -ErrorAction Stop }
        & scp @ssh_opts $remote_script "${target}:$remote_dir/mk-oracle-remote-run.ps1"
        if ($LASTEXITCODE -ne 0) { Write-Error "Failed to copy remote runner" -ErrorAction Stop }

        # 4. Run the tests on the remote host against its local databases.
        Write-Host "Remote component test on $target ($remote_dir) ..." -ForegroundColor White
        & ssh @ssh_opts $target "powershell -NoProfile -ExecutionPolicy Bypass -File `"$remote_dir\mk-oracle-remote-run.ps1`""
        if ($LASTEXITCODE -ne 0) { Write-Error "Remote component tests failed with code $LASTEXITCODE" -ErrorAction Stop }
    }
    finally {
        # The runner embeds the password; remove it from both ends.
        Remove-Item $remote_script -ErrorAction SilentlyContinue
        & ssh @ssh_opts $target "powershell -NoProfile -Command `"Remove-Item -Recurse -Force -Path '$remote_dir' -ErrorAction SilentlyContinue`"" 2>$null
        if ($null -ne $ssh_keyfile) {
            Remove-Item $ssh_keyfile -Force -ErrorAction SilentlyContinue
        }
    }
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
    if ($packBuild -or $packTest -or $packOci -or $packRemoteTest) {
        $target = "//omd/packages/oci:oci_light_win_x64"
        $env:BAZELISK_BASE_URL = "https://github.com/aspect-build/aspect-cli/releases/download"
        $env:USE_BAZEL_VERSION = "aspect/2025.11.0"
        & bazel build $target
        if ($LASTEXITCODE -eq 0) {
            $oci_light_win_x64_zip = (& bazel cquery $target --output=starlark  --starlark:expr='target.files.to_list()[0].path' )
            $packaged = Split-Path "$oci_light_win_x64_zip" -Leaf
            Write-Host "Oracle runtime light/win/x64: $oci_light_win_x64_zip with name $packaged" -ForegroundColor Green
            Copy-Item -Path "$root_dir/$oci_light_win_x64_zip" -Destination "$arte_dir/" -Force -ErrorAction Stop
            $source_hash = (Get-FileHash "$arte_dir/$packaged" -Algorithm SHA256).Hash
            $runtime_path = "runtimes/plugins/libexec/mk-oracle/runtime"
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
        $target_dir = Join-Path (cargo metadata --no-deps | ConvertFrom-Json).target_directory "$cargo_target"
        Write-Host "Killing processes in $target_dir" -ForegroundColor White
        Get-Process | Where-Object { $_.path -and ($_.path -like "$target_dir\*") } | Stop-Process -Force
        Invoke-Cargo-With-Explicit-Package "build" "--release" "--target" $cargo_target
        $exe_dir = Join-Path (cargo metadata --no-deps | ConvertFrom-Json).target_directory "$cargo_target" "release"
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
        Resolve-TestDbEndpoint

        Invoke-Cargo-With-Explicit-Package "test" "--release" "--target" $cargo_target  "--" "--test-threads=4"

        if (Test-Administrator) {
            Write-Host "Escalated permission checks!" -Foreground White
            & "$PSScriptRoot/permissions-check-run.ps1" --root
        }
        else {
            Write-Host "Not elevated: permissions will not be checked" -ForegroundColor Red
        }
    }
    if ($packRemoteTest) {
        Invoke-RemoteComponentTest
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
