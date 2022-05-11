@echo off
set CMK_VERSION="2.0.0p25"
rem #  -----------------------------------------------------------------------------
rem #  Checkmk windows agent plugin to gather information about signature date
rem #  of Mcafee Anti-Virus software.
rem #  -----------------------------------------------------------------------------


setlocal enableDelayedExpansion
set dateval=

rem # on 64 bit systems
if "%PROCESSOR_ARCHITECTURE%" == "AMD64" (
  for /f "skip=2 tokens=3" %%a in ('reg query "HKLM\SOFTWARE\Wow6432Node\McAfee\AvEngine" /v AVDatDate 2^>nul') do @set dateval=%%a
)

rem # on 32 bit systems
if "%PROCESSOR_ARCHITECTURE%" == "x86" (
  for /f "skip=2 tokens=3" %%a in ('reg query "HKLM\SOFTWARE\McAfee\AvEngine" /v AVDatDate 2^>nul') do @set dateval=%%a
)

if not "%dateval%"=="" (
  echo ^<^<^<mcafee_av_client^>^>^>
  echo %dateval%
)
