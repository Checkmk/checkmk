#
# Areca Raid state
#
# Script must executed with local administrator credentials!
#
# This script gathers information from the Areca CLI about the Raid state from a Areca Raid Controller.
# The Areca CLI have to be installed on the System! You can download it from here: ftp.areca.com.tw/RaidCards/AP_Drivers/Windows/CLI/
#
# Version: 1.0
#
# Date: 2020.11.02
#
# Authors: Norman Kuehnberger, ITSWF; Tobias Artinger, ITSWF

#Installation Path
Set-Location -Path "C:\Program Files (x86)\MRAID\CLI\"

# DO NOT CHANGE ANYTHING BELOW THIS LINE!
#-------------------------------------------------------------------------------
#Raid-Status abfragen und in Textfile speichern
./cli rsf info > raid-output.txt
#AUSGABE

echo "<<<arc_raid_status>>>"
#Get-Content raid-output.txt | Select-String -Pattern "#" -NotMatch | Select-String -Pattern "=" -NotMatch | Select-String -Pattern "GuiErrMsg" -NotMatch | Out-File raid.txt
#Filtern auf Zeichen (küzere Version als oben)
Get-Content .\raid-output.txt| Select-String -Pattern "#`|=`|GuiErrMsg" -NotMatch | Out-File .\raid.txt

#Leerzeilen löschen
(Get-Content .\raid.txt).Trim() | ? {$_.Length -gt 0} | Out-File .\raid.txt

Get-Content .\raid.txt
#Ausgabe ohne unnötige Zeilen