rem @set file=install\resources\check_mk.user.yml
rem powershell -Command "@(Get-Content %file% | Where-Object { $_.Contains('``n') } ).Count"
@py -2 check_crlf.py 
@if errorlevel 1 powershell Write-Host "Line Encoding Error" && exit /b 1
@exit /b 0 