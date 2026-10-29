# Guest-side, for watest-qemu (watest_qemu.py): the
# \\%COMPUTERNAME%\shared_public share of FileInfoTest.Unc and
# FileInfoTest.Unicode, as windows_setup_test.cmd sets it up on developer
# machines: test.txt from test_files/shared_public plus a Cyrillic-named file
# (test_russian_file in test-utf-names.h), which that script leaves to be
# created by hand. Without the share both tests return early and pass
# without testing anything. The name is built from code points so that this
# file stays ASCII (Windows PowerShell reads a BOM-less script as ANSI).
$ErrorActionPreference = 'Stop'
$dir = Join-Path $PSScriptRoot 'shared_public'
New-Item -ItemType Directory -Force -Path $dir | Out-Null
Copy-Item (Join-Path $PSScriptRoot 'agents\wnx\test_files\shared_public\test.txt') $dir
$russian = -join [char[]](0x0444, 0x0430, 0x0439, 0x043B, 0x2E, 0x0442, 0x0435, 0x0441, 0x0442)
Set-Content -LiteralPath (Join-Path $dir $russian) -Value 'test'
& net share "shared_public=$dir" '/grant:everyone,FULL' | Out-Null
if ($LASTEXITCODE -ne 0) { throw "net share failed: $LASTEXITCODE" }
if (-not (Test-Path -LiteralPath "\\$env:COMPUTERNAME\shared_public\test.txt")) {
    throw "share \\$env:COMPUTERNAME\shared_public is not reachable"
}
