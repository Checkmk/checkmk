# Info

## Here we can place only:
1. *.sln
2. readme.txt
3. build scripts
4. CMakeLists.txt 
5. .gitignore
6. Makefile

## Test Scripts
call_unit_tests.cmd
or
To check only few tests
call_unit_tests.cmd EventLog*
or
To check only few tests also in 64-bit version
call_unit_tests.cmd EventLog* both

## Assorted
To build and measure time:
x time_build_release.ps1

To unit-test and measure time:
x time_unit_tests.ps1

## Installation
run windows.setup.cmd
This is *MANDATORY* step to build code

## Build of frozen binaries
make frozen_binaries
or
make clean
