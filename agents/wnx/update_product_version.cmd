rem this is working example of version upating in the MSI
rem reference only
cscript.exe //nologo WiRunSQL.vbs file.msi "UPDATE `Property` SET `Property`.`Value`='1.2.3.4' WHERE `Property`.`Property`='ProductVersion'"