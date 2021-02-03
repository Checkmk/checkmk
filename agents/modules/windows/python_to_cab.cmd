@rem Wrapper to cab python, also reference
@cd %1
@powershell -ExecutionPolicy ByPass -File ..\make_cab.ps1 -the_file %2 -the_dir %3 
