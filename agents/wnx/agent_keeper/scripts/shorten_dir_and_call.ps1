#
# Simple wrapper to change dir for short one and call some script
# Required for CI with lobg paths
#
#
# Script to Call Build Rust executable using junction(if available)
#
# shorten_dit_and_call.ps1 p1 p2 p3
#  
# Where:
# Arg  What            Example from CI
# p1 = from\path       workdir\workspace
# p2 = to\path         x
# p3 = the script     .\scripts\cargo_build_core.cmd
#
# We assume that CI is building in the workdir\workspavce and there is a junction x
# This situation is applicable only for Checkmk CI infrastructure

[string]$inp = Get-Location
[string]$new = $inp.tolower().replace($args[0], $args[1])
Write-Host "shorten dir: " $new
Set-Location $new
&$args[2]
[Environment]::Exit($LASTEXITCODE)