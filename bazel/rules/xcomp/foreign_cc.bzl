"""Wrapper that lets users specify an alternative target platform for rules_foreign_cc targets."""

load(":private/xcomp/foreign_cc/cmake.bzl", _cmake = "cmake")
load(":private/xcomp/foreign_cc/configure_make.bzl", _configure_make = "configure_make")
load(":private/xcomp/foreign_cc/make.bzl", _make = "make")

cmake = _cmake
configure_make = _configure_make
make = _make
