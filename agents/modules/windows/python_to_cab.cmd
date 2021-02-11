:: Wrapper to cab python
:: Parameters <dir-to-work> <resulting-file> <dir-to-compress>

@echo off
cd %1
powershell -ExecutionPolicy ByPass -File ..\..\make_cab.ps1 -the_file %2 -the_dir %3 
