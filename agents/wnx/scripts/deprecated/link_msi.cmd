:: Script to link msi from compiled data
@"C:\Program Files (x86)\WiX Toolset v3.11\bin\Light.exe" ^
-out C:\z\m\check_mk\agents\wnx\build\install\Release\check_mk_service.msi ^
-pdbout C:\z\m\check_mk\agents\wnx\build\install\Release\check_mk_service.wixpdb ^
-sw1076 ^
-cultures:null ^
-dRelease=1 ^
-ext "C:\Program Files (x86)\WiX Toolset v3.11\bin\\WixUIExtension.dll" ^
-spdb ^
-contentsfile obj\Release\install.wixproj.BindContentsFileListnull.txt ^
-outputsfile obj\Release\install.wixproj.BindOutputsFileListnull.txt ^
-builtoutputsfile obj\Release\install.wixproj.BindBuiltOutputsFileListnull.txt ^
obj\Release\InstallFolderDialog.wixobj obj\Release\InstallMainDialog.wixobj obj\Release\Product.wixobj                             