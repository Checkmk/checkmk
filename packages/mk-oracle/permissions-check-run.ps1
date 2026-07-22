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

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# --root: run only the escalated (elevated) checks, skip the current-user ones.
$only_escalated = $false
foreach ($a in $args) {
    switch ($a) {
        "--root" { $only_escalated = $true }
        default { Write-Error "Unknown argument: $a (supported: --root)" }
    }
}

$package_name = "mk-oracle"
$exe_name = "$package_name.exe"
$cargo_target = "x86_64-pc-windows-msvc"

# 1. Find repo root
$root_dir = $PSScriptRoot
while (!(Test-Path "$root_dir/.werks" -ErrorAction SilentlyContinue)) {
    $root_dir = Split-Path -Parent $root_dir
    if ($root_dir -eq "") {
        Write-Error "Repo root not found"
    }
}

# 2. Build binary
Write-Host "Building $package_name..." -ForegroundColor White
Push-Location $PSScriptRoot
$temp_dir = Join-Path $env:TEMP "mk-oracle-perms-check-$([System.IO.Path]::GetRandomFileName())"
New-Item -ItemType Directory -Path $temp_dir -Force | Out-Null
try {
    & cargo build --release --package $package_name --target $cargo_target
    if ($LASTEXITCODE -ne 0) { Write-Error "Build failed" }
    $target_dir = Join-Path (cargo metadata --no-deps | ConvertFrom-Json).target_directory $cargo_target "release"
    $binary = Join-Path $target_dir $exe_name
    Write-Host "Binary: $binary" -ForegroundColor Green

    # 3. Download and unpack Oracle instant client via bazel
    Write-Host "Downloading OCI runtime..." -ForegroundColor White
    $target = "//omd/packages/oci:oci_light_win_x64"
    $env:BAZELISK_BASE_URL = "https://github.com/aspect-build/aspect-cli/releases/download"
    $env:USE_BAZEL_VERSION = "aspect/2025.11.0"
    & bazel build $target
    if ($LASTEXITCODE -ne 0) { Write-Error "OCI download failed" }

    $oci_zip = & bazel cquery $target --output=starlark --starlark:expr='target.files.to_list()[0].path'
    $runtime_path = "$temp_dir/runtimes/plugins/packages/mk-oracle/runtime"
    New-Item -ItemType Directory -Path $runtime_path -Force | Out-Null
    Expand-Archive -Path "$root_dir/$oci_zip" -DestinationPath $runtime_path -Force

    # Grant BUILTIN\Users write access so the runtime dir is no longer
    # only-admin-writable — otherwise, on a box where the current account is
    # itself a local admin, Step 4's negative check can never trigger.
    Write-Host "Granting BUILTIN\Users write access to $runtime_path..." -ForegroundColor White
    & icacls $runtime_path /grant "*S-1-5-32-545:(OI)(CI)M" /T /C | Out-Null
    if ($LASTEXITCODE -ne 0) { Write-Error "icacls grant failed" }

    # Custom-metric SQL fixture: created unconditionally — the elevated check
    # needs an existing Users-writable SQL file to refuse reading.
    $orasql_dir = "$temp_dir/runtimes/plugins/packages/mk-oracle/orasql"
    New-Item -ItemType Directory -Path $orasql_dir -Force | Out-Null
    Copy-Item -Path "runtimes/plugins/packages/mk-oracle/orasql/simple_custom_metric.sql" -Destination (Join-Path $orasql_dir "simple_custom_metric.sql") -Force

    if ($only_escalated) {
        Write-Host "--root: skipping current-user checks" -ForegroundColor Yellow
    }
    else {
        # 4. Run as current user — expect at least 3 lines
        Write-Host "Step 3: running as current user..." -ForegroundColor White
        $env:MK_LIBDIR = "$temp_dir/runtimes"
        $output = & $binary -c tests/files/test-mini-one-section.yml 2>&1 | Out-String
        $lines = ($output -split "`n" | Where-Object { $_ -ne "" })
        $line_count = $lines.Count
        Write-Host $output
        Write-Host "---"
        Write-Host "Lines: $line_count"
        if ($line_count -lt 3) {
            Write-Error "FAIL: expected at least 3 lines, got $line_count"
        }
        Write-Host "OK: non-root can exec non-root code" -ForegroundColor Green

        # 3b. Run the custom-metric config as current user — expect the SQL file is read and executed
        Write-Host "Step 3b: running custom-metric config as current user..." -ForegroundColor White
        $sql_output = & $binary -c tests/files/test-custom-metric.yml 2>&1 | Out-String
        Write-Host $sql_output
        Write-Host "---"
        if ($sql_output -notmatch "details:hello") {
            Write-Error "FAIL: expected custom SQL file output 'details:hello'"
        }
        Write-Host "OK: non-root reads and executes custom SQL file" -ForegroundColor Green
    }

    # 5+6. Single elevated session: verify the Users-writable dir is refused,
    # restrict it to Administrators-only (elevated, so the ACL reset itself
    # isn't fighting a UAC-filtered token), then verify it's trusted again.
    Write-Host "Step 4: running elevated checks..." -ForegroundColor White
    $admin_out_before = "$env:TEMP\perms-check-stdout-before.txt"
    $admin_out_after = "$env:TEMP\perms-check-stdout-after.txt"
    $admin_sql_out_before = "$env:TEMP\perms-check-sql-stdout-before.txt"
    $admin_script = Join-Path $temp_dir "admin-check.ps1"
    @"
`$ErrorActionPreference = 'Stop'
Set-Location '$PSScriptRoot'
`$env:MK_LIBDIR = '$temp_dir/runtimes'
& '$binary' -c tests/files/test-mini-one-section.yml *> '$admin_out_before'
& '$binary' -c tests/files/test-custom-metric.yml *> '$admin_sql_out_before'
icacls '$runtime_path' /inheritance:r /remove:g '*S-1-5-32-545' /grant:r '*S-1-5-32-544:(OI)(CI)F' '*S-1-5-18:(OI)(CI)F' /T /C | Out-Null
if (`$LASTEXITCODE -ne 0) { exit 2 }
& '$binary' -c tests/files/test-mini-one-section.yml *> '$admin_out_after'
"@ | Set-Content -Path $admin_script -Encoding utf8
    $proc = Start-Process pwsh -ArgumentList "-NoProfile -File `"$admin_script`"" -Verb RunAs -Wait -PassThru -WindowStyle Hidden
    if ($proc.ExitCode -ne 0) {
        Write-Error "FAIL: elevated check script exited with code $($proc.ExitCode) (2 = icacls restrict failed)"
    }

    # Missing output file means the elevated run never executed the binary —
    # that must FAIL, not pass as "empty output".
    foreach ($f in @($admin_out_before, $admin_sql_out_before, $admin_out_after)) {
        if (!(Test-Path $f)) {
            Write-Error "FAIL: elevated run produced no output file: $f"
        }
    }

    $output_before = Get-Content $admin_out_before -Raw
    Remove-Item $admin_out_before -ErrorAction SilentlyContinue
    if ($output_before -and $output_before.Trim() -ne "") {
        Write-Host $output_before -ForegroundColor Red
        Write-Error "FAIL: expected empty output from admin run before restricting permissions"
    }
    Write-Host "OK: root can't exec non-root code" -ForegroundColor Green

    $sql_output_before = Get-Content $admin_sql_out_before -Raw
    Remove-Item $admin_sql_out_before -ErrorAction SilentlyContinue
    if ($sql_output_before -and $sql_output_before.Trim() -ne "") {
        Write-Host $sql_output_before -ForegroundColor Red
        Write-Error "FAIL: expected empty output from admin run with custom SQL file"
    }
    Write-Host "OK: root can't read non-root custom SQL file" -ForegroundColor Green

    $output_after = Get-Content $admin_out_after -Raw
    Remove-Item $admin_out_after -ErrorAction SilentlyContinue
    # Same shape as the non-elevated run (step 3): real section output, not
    # just any bytes — error text on stderr must not count as success.
    $after_lines = ($output_after -split "`n" | Where-Object { $_.Trim() -ne "" })
    if ($after_lines.Count -ge 3 -and $output_after -match '<<<') {
        Write-Host $output_after
        Write-Host "---"
        Write-Host "OK: root can exec root code" -ForegroundColor Green
    }
    else {
        Write-Host $output_after -ForegroundColor Red
        Write-Error ("FAIL: expected section output (>=3 non-empty lines containing '<<<') " +
            "from admin run after restricting permissions")
    }

}
finally {
    Remove-Item $temp_dir -Recurse -Force -ErrorAction SilentlyContinue
    Pop-Location
}
