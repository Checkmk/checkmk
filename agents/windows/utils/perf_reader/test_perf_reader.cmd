@echo off
@rem Simple Testing File for Some utils
if "%1" == "" (
    echo "usage: test_per_reader <exe module to test>"
    exit /b 9999
)
"%1" test
if %errorlevel% equ 0 (
   echo Success
   del test_output_file.tmp
   exit /b 0
) 
echo Failed with code %errorlevel%
exit /b %errorlevel%
