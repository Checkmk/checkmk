@echo off
set CMK_VERSION="2.0.0p24"
echo ^<^<^<windows_broadcom_bonding^>^>^>

rem Tested with BroadCom BASP v1.6.3
wmic /namespace:\\root\BrcmBnxNS path brcm_redundancyset get caption,redundancystatus
