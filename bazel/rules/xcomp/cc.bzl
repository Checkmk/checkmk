"""Wrapper that lets users specify an alternative target platform."""

load(":private/xcomp/cc/cc_binary.bzl", _cc_binary = "cc_binary")
load(":private/xcomp/cc/cc_library.bzl", _cc_library = "cc_library")
load(":private/xcomp/cc/cc_test.bzl", _cc_test = "cc_test")

cc_binary = _cc_binary
cc_library = _cc_library
cc_test = _cc_test
