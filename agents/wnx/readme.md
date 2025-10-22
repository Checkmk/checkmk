# Info

## Here we can place only:

1. \*.sln
2. readme.txt
3. build scripts and tools
4. CMakeLists.txt
5. .gitignore
6. Makefile
7. rulesets for clang/tidy

## Installation

**You need have choco already installed** to build release

Run _windows_setup.cmd_. This is **Simplest** method to install some required Windows software

Alternatively you can **choco install make** and use Makefile

## Build Scripts

1. run.ps1 - to build/unit test agent

## Test Scripts

1. run_tests.cmd

## Assorted

To build and measure time use ptime
To run arbitrary powershell script use x.cmd

## Build of frozen binaries

_make frozen_binaries_ to build exe and put it into the artefacts directory
or
_make clean_ to clean directories from the trash
