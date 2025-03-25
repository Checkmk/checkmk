load("@bazel_skylib//rules:copy_file.bzl", _copy_file = "copy_file")
load("@rules_proto//proto:defs.bzl", _proto_library = "proto_library")
load(
    "@rules_proto_grpc//:defs.bzl",
    "ProtoPluginInfo",
    "proto_compile_attrs",
    "proto_compile_impl",
    "proto_compile_toolchains",
)
load("@rules_python//python:defs.bzl", _py_library = "py_library")
load("@rules_python//python:proto.bzl", _py_proto_library = "py_proto_library")

def proto_library_as(name, proto, as_proto, **kwargs):
    """Macro to create a proto_library after moving the proto to a different path.

    This avoids errors such as
    "Error in fail: Cannot generate Python code for a .proto whose path contains '-'"

    Args:
        name: the name of the target.
        proto: the proto file.
        as_proto: new path to the proto file under the current directory.
        **kwargs: arguments forwarded to the proto_library.

    """
    name_cp = name + "_cp"
    _copy_file(name = name_cp, src = proto, out = as_proto)
    _proto_library(name = name, srcs = [as_proto], **kwargs)

py_proto_compile = rule(
    implementation = proto_compile_impl,
    attrs = dict(
        proto_compile_attrs,
        _plugins = attr.label_list(
            providers = [ProtoPluginInfo],
            default = [Label("//bazel/rules/private/proto:pyi_plugin")],
            cfg = "exec",
            doc = "List of protoc plugins to apply",
        ),
    ),
    toolchains = proto_compile_toolchains,
)

def py_proto_library(name, protos, output_mode = None, **kwargs):
    """py_proto_library generates Python code from proto and creates a py_library for them.

    Args:
        name: the name of the target.
        protos: the proto files.
        output_mode: "PREFIX" or "NO_PREFIX".
        **kwargs: arguments forwarded to the py_library.
    """
    name_pb = name + "_pb"
    _py_proto_library(
        name = name_pb,
        deps = protos,
    )

    name_pyi = name + "_pyi"
    py_proto_compile(
        name = name_pyi,
        output_mode = output_mode,
        protos = protos,
    )

    _py_library(
        name = name,
        srcs = [name_pb],
        pyi_srcs = [name_pyi],
        imports = ["."],
        **kwargs
    )
