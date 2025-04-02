# Signer wrapper for Bazel

param (
    $source,
    $target
)

Write-Host "Copy $source to $target"
Copy-Item -Path $source -Destination $target -Force
Write-Host "Sign $target"
if (Test-Path "c:\common\scsigntool.exe" -PathType Leaf) {
    $pin = 469673
    $cert = "7b97b15df65358623576584b7aafbe04d6668a0e"
    &c:\common\scsigntool.exe -pin $pin sign /sha1 $cert /tr http://timestamp.sectigo.com /td sha256 /fd sha256 $target
}
else {
    Write-Host "skip signing"
}