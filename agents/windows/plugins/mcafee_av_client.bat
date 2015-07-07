@echo off
rem #  -----------------------------------------------------------------------------
rem #  Check_MK windows agent plugin to gather information about signature date
rem #  of Mcafee Anti-Virus software.
rem #  -----------------------------------------------------------------------------


setlocal enableDelayedExpansion
set dateval=

for /f "tokens=3" %%a in ('reg query "HKLM\SOFTWARE\McAfee\AvEngine" ^|find "AVDatDate" ^|find "REG_SZ"') do @set dateval=%%a
if not "%dateval%"=="" (
  echo ^<^<^<mcafee_av_client^>^>^>
  echo %dateval%
)
