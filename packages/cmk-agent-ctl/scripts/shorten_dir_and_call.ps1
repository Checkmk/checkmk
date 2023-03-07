#
# Simple wrapper to change dir for short one and call some script
# Required for CI with lobg paths
#

[string]$inp = Get-Location
[string]$new = $inp.tolower().replace($args[0], $args[1])
Write-Host "shorten dir: " $new
Set-Location $new
&$args[2]
