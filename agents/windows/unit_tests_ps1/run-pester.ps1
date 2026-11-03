# Guest-side script for pester-qemu (pester_qemu.py). Runs every Pester
# suite under agents\windows\unit_tests_ps1, with the Pester module in
# pester\. Both are staged next to this script.
#
# PSModulePath holds only our Pester and Windows PowerShell's own modules.
# Otherwise PowerShell can load the image's old built-in Pester 3.4 in the
# middle of the run, and the later test files break.
#
# The run passes only if Pester reports Passed and ran at least one test.
# Counting failed tests is not enough: a test file that does not parse, or
# whose setup throws, fails without any test failing.
$env:PSModulePath = "$PSScriptRoot\pester;$PSHOME\Modules"
$r = Invoke-Pester -Path "$PSScriptRoot\agents\windows\unit_tests_ps1" -PassThru
if (-not $r) { exit 1 }
Write-Output ('TOTAL=' + $r.TotalCount + ' PASSED=' + $r.PassedCount + ' FAILED=' + $r.FailedCount +
    ' SKIPPED=' + $r.SkippedCount + ' FAILED_CONTAINERS=' + $r.FailedContainersCount)
if ($r.Result -ne 'Passed' -or $r.TotalCount -eq 0) { exit 1 }
exit 0
