:: Wrapper to run original bash command, requires WSL installed

@where bash.exe > nul 2>&1 || ( powershell Write-Host "Install WSL to run this command" -Foreground Red & exit /b 1 )
@bash ./create-archive