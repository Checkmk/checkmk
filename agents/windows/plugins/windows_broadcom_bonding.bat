set VERSION="2.0.0i2"
@echo off
echo ^<^<^<windows_broadcom_bonding^>^>^>

rem Tested with BroadCom BASP v1.6.3
wmic /namespace:\\root\BrcmBnxNS path brcm_redundancyset get caption,redundancystatus
