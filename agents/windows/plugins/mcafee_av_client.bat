@echo off
rem #  -----------------------------------------------------------------------------
rem #  Check_MK windows agent plugin to gather information about signature date
rem #  of McAfee Virusscan Anti-Virus software.
rem #
rem #  Superseded by the mcafee_av_client.ps1 plugin which checks signature dates 
rem #  of both Virusscan and Endpoint Security
rem #  -----------------------------------------------------------------------------


setlocal enableDelayedExpansion
set dateval=

for /f "tokens=3" %%a in ('reg query "HKLM\SOFTWARE\McAfee\AvEngine" ^|find /I "AVDatDate" ^|find "REG_SZ"') do @set dateval=%%a
if "%dateval%"=="" (
    rem # on 64 bit systems the registry key is in the wow64/32 branch
    for /f "tokens=3" %%a in ('reg query "HKLM\SOFTWARE\Wow6432Node\McAfee\AvEngine" ^|find /I "AVDatDate" ^|find "REG_SZ"') do @set dateval=%%a
)

if not "%dateval%"=="" (
  echo ^<^<^<mcafee_av_client^>^>^>
  echo %dateval%
)
