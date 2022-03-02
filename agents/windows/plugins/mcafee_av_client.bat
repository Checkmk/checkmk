@echo off
set CMK_VERSION="2.2.0i1"
rem #  -----------------------------------------------------------------------------
rem #  Check_MK windows agent plugin to gather information about signature date
rem #  of Mcafee Virusscan and ENS Anti-Virus software.
rem #  -----------------------------------------------------------------------------


setlocal enableDelayedExpansion
set dateval=

rem # check for ENS DAT date (returned as yyyy-mm-dd)
for /f "skip=2 tokens=3" %%a in ('reg query "HKLM\SOFTWARE\McAfee\AvSolution\DS\DS" /v szContentCreationDate 2^>nul') do @set dateval=%%a
if "%dateval%"=="" (
  rem # ENS not installed, check for Virusscan DAT date (returned as yyyy/mm/dd)
  rem # on 64 bit systems
  if "%PROCESSOR_ARCHITECTURE%" == "AMD64" (
    for /f "skip=2 tokens=3" %%a in ('reg query "HKLM\SOFTWARE\Wow6432Node\McAfee\AvEngine" /v AVDatDate 2^>nul') do @set dateval=%%a
  )
  rem # on 32 bit systems
  if "%PROCESSOR_ARCHITECTURE%" == "x86" (
    for /f "skip=2 tokens=3" %%a in ('reg query "HKLM\SOFTWARE\McAfee\AvEngine" /v AVDatDate 2^>nul') do @set dateval=%%a
  )
)

rem # if dateval was found, return it in the form yyyy/mm/dd

if not "%dateval%"=="" (
  echo ^<^<^<mcafee_av_client^>^>^>
  echo %dateval:-=/%
)
