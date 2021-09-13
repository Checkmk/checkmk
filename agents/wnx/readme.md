# Info

## Here we can place only:
1. *.sln
2. readme.txt
3. build scripts and tools
4. CMakeLists.txt 
5. .gitignore
6. Makefile
7. rulesets for clang/tidy


## Installation

**You need have choco already installed** to build release

Run *windows_setup.cmd*. This is **Simplest** method to install some required Windows software

Alternatively you can **choco install make** and use Makefile

## Build Scripts
1. build_release.cmd - to build MSI in artefacts
2. build_watest.cmd- to build 32-bit watest to be used later


## Test Scripts
1. Unit Testss Full: call_unit_tests.cmd
2. Unit Tests Part: call_unit_tests.cmd EventLog*
3. Integration Tests: call_integration_tests.cmd

## Assorted
To build and measure time use ptime
To run arbitrary powershell script use x

## Build of frozen binaries
*make frozen_binaries* to build exe and put it into  the artefacts directory
or
*make clean* to clean directories from the trash
