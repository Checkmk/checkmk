@echo off
::
:: Script to Call Build Rust executable using junction(if available)
::  
:: p1 = from\path	workdir\workspace
:: p2 = to\path         x
:: p3 = core script     .\scripts\cargo_build_core.cmd
:: we assume that CI is building in the workdir\workspavce and there is a junction x
:: This situation is applicable only for tribe29 CI infrastructure
::

@echo off
set ci_root_dir=workdir\workspace
set ci_junction_to_root_dir=x
set script_to_run=.\scripts\cargo_build_core.cmd
powershell -ExecutionPolicy ByPass -File scripts/shorten_dir_and_call.ps1 %ci_root_dir% %ci_junction_to_root_dir% %script_to_run%
