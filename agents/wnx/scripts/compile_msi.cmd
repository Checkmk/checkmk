:: Script to compile msi obj
@"C:\Program Files (x86)\WiX Toolset v3.11\bin\candle.exe" ^
-sw1076 ^
-dRelease=1 ^
-dConfiguration=Release ^
-dPlatform=x86 ^
-out obj\Release\ ^
-arch x86 ^
-ext "C:\Program Files (x86)\WiX Toolset v3.11\bin\WixUIExtension.dll" ^
-sw1091 ^
InstallFolderDialog.wxs InstallMainDialog.wxs Product.wxs

