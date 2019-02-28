@echo off
powershell write-host -fore Cyan "********************************************************************"
powershell write-host -fore Cyan "           Command line builder for the Windows Agent MSI           "
powershell write-host -fore Cyan "Used manually. Output MSI wil be placed in ../build/install/Release."
powershell write-host -fore Cyan "********************************************************************"
if "%1" == "" powershell write-host -fore Red Error: Folder for the sources is required, for example, "." && exit
if "%WIX%"== "" powershell write-host -fore Red  Error: Wix is not installed. Either install Wix from the web or set environment variable WIX && exit
set folder=%WIX%\bin
mkdir ..\build\install\Release
mkdir ..\build\install\obj\Release
set msi_name=check_mk_service
set obj_folder=..\build\install\obj\Release
set bin_folder=..\build\install\Release
set src_folder=%1
set can=candle.exe
set lig=light.exe
set candle="%folder%\%can%"
set light="%folder%\%lig%"
rem common files:
set work_file=InstallMainDialog
set out_file_1=%obj_folder%\%work_file%.wixobj
%candle% -ext WixUtilExtension -out %out_file_1% %src_folder%/%work_file%.wxs 
set work_file=InstallFolderDialog
set out_file_2=%obj_folder%\%work_file%.wixobj
%candle% -ext WixUtilExtension -out %out_file_2% %src_folder%/%work_file%.wxs 
rem install files:
set work_file=Product
set out_file_msi=%obj_folder%\%work_file%.wixobj
%candle% -ext WixUtilExtension -out %out_file_msi% %src_folder%/%work_file%.wxs 

set pack=%out_file_1% %out_file_2%
set param=-ext WixUIExtension -ext WixUtilExtension -sval -spdb
%light% %param% -o %bin_folder%\%msi_name%.msi   %obj_folder%/Product.wixobj %pack%
