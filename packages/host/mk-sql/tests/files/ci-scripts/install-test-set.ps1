$folderPath = "..\windows-registry"
$regFiles = Get-ChildItem -Path $folderPath -Filter *.reg
foreach ($file in $regFiles) {
    Write-Host "loading $($file.FullName)"
    regedit.exe /s $file.FullName
}

Write-Host "Setting test cases are ready"