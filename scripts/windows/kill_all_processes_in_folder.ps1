# Kill all processes starting in the current folder.
# --------------------------------------------------
# Mitigates the annoying Windows "feature": if process is running you can't touch executable
# Use it with care, btw. This kills everything in the current folder
Get-Process | ?{$_.path -and (test-path (split-path $_.path -leaf ))} | Stop-Process -Force