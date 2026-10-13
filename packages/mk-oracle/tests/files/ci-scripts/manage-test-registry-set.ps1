$command = $args[0]
$name = $args[1]
$package = "mk-oracle"

function Install-Me {
    param (
        [string]$Name
    )
    Write-Output "Installing $Name..."
    $folderPath = $PSScriptRoot + "\..\windows-registry\$Name"
    $regFiles = Get-ChildItem -Path $folderPath -Filter *.reg
    if (-not $regFiles) {
        Write-Output "No .reg files found in $folderPath."
        exit 1
    }
    foreach ($file in $regFiles) {
        Write-Host "loading $($file.FullName)"
        reg.exe import $file.FullName
        if ($LASTEXITCODE -ne 0) {
            Write-Output "Importing $($file.FullName) failed."
            exit 1
        }
    }

}

function Remove-Me {
    param (
        [string]$Name
    )
    Write-Output "Removing $Name..."
    reg delete "HKLM\SOFTWARE\checkmk\tests\$Name\$package" /f
}

if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)) {
    Write-Output "This script needs administrator privileges."
    exit 1
}


switch ($command) {
    '--install' { Install-Me -Name $name }
    '--remove' { Remove-Me -Name $name }
    '--reinstall' { 
        Remove-Me -Name $name
        Install-Me -Name $name 
    }
    default {
        Write-Output "Invalid command $Command. Use --install <name> or --remove <name>."
        exit 1
    }
}


exit 0
