Checkmk protobuf integration
============================

The protobuf integration is a little tricky because we need protobuf in
different situations. We need protobuf for the following parts of Checkmk:

a) protoc is needed during built time (also packaging) to compile the proto files
b) The Microcore needs libprotobuf for reading the Microcore configuration
c) python-protobuf is needed for creating the Microcore configuration.

It would be possible to compile protoc and libprotobuf, but since our toolchain
is very new, our g++ in the CI containers link against too new libstd++ which
are natively not available on the target systems.

The python protobuf module is also able to work in pure python mode, but this
would come with a performance drawback. Sice we want full performance, this is
no option for us.

The way to solve this is to statically link the protobuf parts.

1. The microcore will statically link with libprotobuf. This is handled by the
   build mechanic of the Microcore (See enterprise/core/src/Makefile.am).
2. We build the python protobuf package on our own in CPP mode with statically
   linked libraries. This is done here in this OMD package.
