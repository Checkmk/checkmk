@echo off
set CMK_VERSION="2.1.0p20"
echo ^<^<^<windows_broadcom_bonding^>^>^>

rem Tested with BroadCom BASP v1.6.3
wmic /namespace:\\root\BrcmBnxNS path brcm_redundancyset get caption,redundancystatus
