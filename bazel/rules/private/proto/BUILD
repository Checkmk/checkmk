load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_proto_grpc//:defs.bzl", "proto_plugin")
load("@rules_python//python/entry_points:py_console_script_binary.bzl", "py_console_script_binary")

py_console_script_binary(
    name = "protoc-gen-mypy",
    data = ["//bazel/tools:python_stdlib_bytecode"],
    pkg = requirement("mypy-protobuf"),
    pyc_collection = "include_pyc",
    script = "protoc-gen-mypy",
    tags = [
        "manual",
        "no-mypy",
    ],
)

proto_plugin(
    name = "pyi_plugin",
    exclusions = ["google/protobuf"],
    options = ["quiet"],
    outputs = ["{protopath|python}_pb2.pyi"],
    # protoc_plugin_name = "pyi",
    tool = ":protoc-gen-mypy",
    visibility = ["//visibility:public"],
)
