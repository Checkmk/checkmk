# Kill all processes starting in the current folder.
# --------------------------------------------------
# Mitigates the annoying Windows "feature": if process is running you can't touch executable
# Use it with care, btw. This kills everything in the current folder

$cwd=Get-Location
if ( $cwd -like "*cmk-agent-ctl\target*") { 
   Get-Process | Where-Object { $_.path  -and ($_.path -like "$cwd\*") } | Stop-Process -Force
}
