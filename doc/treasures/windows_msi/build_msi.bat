"C:\Program Files (x86)\wix\candle.exe" -ext WixUtilExtension C:\mkmsi\cmk_WixUI_InstallDir.wxs
"C:\Program Files (x86)\wix\candle.exe" -ext WixUtilExtension C:\mkmsi\cmk_InstallDirDlg.wxs
"C:\Program Files (x86)\wix\candle.exe" -ext WixUtilExtension C:\mkmsi\check_mk_agent.wxs
"C:\Program Files (x86)\wix\light.exe" -ext WixUIExtension -ext WixUtilExtension -sval -o check_mk_agent.msi C:\mkmsi\check_mk_agent.wixobj C:\mkmsi\cmk_WixUI_InstallDir.wixobj C:\mkmsi\cmk_InstallDirDlg.wixobj
@pause
