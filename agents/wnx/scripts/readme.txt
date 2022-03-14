
Binaries and libraries to be used during build/test of Windows agents(new and old). 
Because Windows doesn't support unpack of archive files from the scratch, 
we have to have additional binaries, like 7zip.

Some libraries may be located in <omd> branch, this is normal. Example - gtest. All other libraries located here, in 
<agents/windows/dependencies>. 
Script will try to find libraries in next order 
  1. First Param
  2. Second Param

Contents:
Root:
  - readme.txt         - this file
  - unpack_package.cmd - unpack one tgz to correct folder
  - unpack_all.cmd     - example how unpack few packages, every project can write own unpacker
  - /7zip              - binaries to unpack
  - /*                 - libraries for windows agent(new)
  - wirunsql.vbs       - script is used to patch versions by build script
  - clean_artifacts.cmd- used by Makefile to clean artifacts
  -*_msi.cmd           - MSI tools

Packages List:
  Global Packages[OMD]
    1. Gtest
    2. Simpleini
    3. Fmt. Formatting package for C++. Python and "C" style full and safe support. License is Special but looks as safe.
    4. Asio. *Standalone* ASIO library for C++. Industry Standard Low-level Transport. License is Boost.
    5. yaml-cpp
  Local:
    1. 7-zip: to unpack tar.gz and zip files. Windows doesn't support from the box decompression of zip/tgz/etc/. License is LGPL.

Guidelines:
  HOW-TO unpack all by default(example) :
  unpack_all.cmd ..\..\..\omd\packages
  param 1 - location for first directory with packages

For build/development process, please 
  - add command to unpack all in prebuild step
  - add folder with unpacked packages to .gitignore.
  This is usually more than enough. We are not going to change 3-rd party libraries often.
  TODO: real check of dependencies.

