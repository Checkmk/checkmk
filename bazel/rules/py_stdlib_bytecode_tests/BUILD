load("@rules_python//python:defs.bzl", "py_binary")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")
load("//bazel/rules:py_stdlib_bytecode.bzl", "py_stdlib_bytecode")

py_stdlib_bytecode(name = "stdlib_bytecode")

# Prints where Python looks for the bytecode of email.feedparser. A py_binary of rules_python, like
# tools that use py_stdlib_bytecode(), unlike py_cmk_test: the runfiles hold the standard library
# the same way.
py_binary(
    name = "probe",
    srcs = ["probe.py"],
    data = [":stdlib_bytecode"],
)

py_cmk_test(
    name = "test",
    size = "small",
    srcs = ["test_py_stdlib_bytecode.py"],
    data = [":probe"],
    env = {"PROBE": "$(rootpath :probe)"},
)
