"""Wrapper that lets users specify an alternative target platform."""

load(":private/xcomp/rust/rust_binary.bzl", _rust_binary = "rust_binary")
load(":private/xcomp/rust/rust_library.bzl", _rust_library = "rust_library")
load(":private/xcomp/rust/rust_test.bzl", _rust_test = "rust_test")

rust_binary = _rust_binary
rust_library = _rust_library
rust_test = _rust_test
