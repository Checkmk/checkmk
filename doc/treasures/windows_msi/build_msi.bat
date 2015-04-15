"C:\Program Files (x86)\wix\candle.exe" -ext WixUtilExtension C:\mkmsi\cmk_WixUI_InstallDir.wxs
"C:\Program Files (x86)\wix\candle.exe" -ext WixUtilExtension C:\mkmsi\cmk_InstallDirDlg.wxs
"C:\Program Files (x86)\wix\candle.exe" -ext WixUtilExtension C:\mkmsi\check_mk_agent_baked.wxs
"C:\Program Files (x86)\wix\candle.exe" -ext WixUtilExtension C:\mkmsi\check_mk_agent_vanilla.wxs
"C:\Program Files (x86)\wix\light.exe" -ext WixUIExtension -ext WixUtilExtension -sval -o check_mk_agent_baked.msi C:\mkmsi\check_mk_agent_baked.wixobj C:\mkmsi\cmk_WixUI_InstallDir.wixobj C:\mkmsi\cmk_InstallDirDlg.wixobj
"C:\Program Files (x86)\wix\light.exe" -ext WixUIExtension -ext WixUtilExtension -sval -o check_mk_agent_vanilla.msi C:\mkmsi\check_mk_agent_vanilla.wixobj C:\mkmsi\cmk_WixUI_InstallDir.wixobj C:\mkmsi\cmk_InstallDirDlg.wixobj
@pause
