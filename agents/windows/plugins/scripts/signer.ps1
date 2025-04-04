# Signer wrapper for Bazel

param (
    $source,
    $target
)

if (Test-Path "c:\common\scsigntool.exe" -PathType Leaf) {
    Write-Host "Copy $source to $target"
    Copy-Item -Path $source -Destination $target -Force
    Write-Host "Sign $target"
    $pin = 469673
    $cert = "7b97b15df65358623576584b7aafbe04d6668a0e"
    &c:\common\scsigntool.exe -pin $pin sign /sha1 $cert /tr http://timestamp.sectigo.com /td sha256 /fd sha256 $target *>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Sign $target failed with exit code <$LASTEXITCODE>" -foreground Red
        Remove-Item -Path $target -Force -ErrorAction SilentlyContinue
    }
    else {
        Write-Host "Sign $target succeeded" -foreground Green
    }
}
else {
    Write-Host "Skip signing $source to $target, scsigntool.exe not found" -foreground Red
}