load("@bazel_skylib//rules:copy_file.bzl", _copy_file = "copy_file")
load("@protobuf//bazel:cc_proto_library.bzl", _cc_proto_library = "cc_proto_library")
load("@protobuf//bazel:py_proto_library.bzl", _py_proto_library = "py_proto_library")
load("@rules_cc//cc:cc_library.bzl", _cc_library = "cc_library")
load("@rules_proto//proto:defs.bzl", _proto_library = "proto_library")
load(
    "@rules_proto_grpc//:defs.bzl",
    "ProtoPluginInfo",
    "proto_compile_attrs",
    "proto_compile_impl",
    "proto_compile_toolchains",
)
load("@rules_python//python:defs.bzl", _py_library = "py_library")

def _cc_proto_library_with_runtime_impl(name, visibility, proto_lib_target):
    """Implementation function for cc_proto_library_with_runtime symbolic macro."""
    _cc_library(
        name = name,
        visibility = visibility,
        deps = [
            proto_lib_target,
            "@protobuf//:protobuf",
        ],
    )

_cc_proto_library_with_runtime = macro(
    attrs = {
        "proto_lib_target": attr.label(mandatory = True, configurable = False, doc = "The generated proto library target"),
    },
    implementation = _cc_proto_library_with_runtime_impl,
)

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
    _copy_file(name = name_cp, src = proto, out = as_proto, allow_symlink = True)
    _proto_library(name = name, srcs = [as_proto], **kwargs)

def cc_proto_library(name, deps, visibility = None, **kwargs):
    """Wrapper for cc_proto_library that ensures the protobuf runtime is included.

    This wrapper works around an issue where cc_proto_library doesn't properly
    link the protobuf runtime when:
    1. --incompatible_enable_proto_toolchain_resolution is enabled, AND
    2. The cc_binary uses dynamic_deps (even with an unrelated shared library)

    When toolchain resolution is enabled, cc_proto_library obtains the protobuf
    runtime via toolchain resolution rather than as a direct dependency. This
    toolchain-provided runtime is not properly propagated when the binary uses
    dynamic_deps.

    Symptoms without this wrapper:
    - Linker errors like: undefined reference to
      `google::protobuf::Message::kDescriptorMethods`
    - Linker errors like: undefined reference to
      `absl::lts_YYYYMMDD::log_internal::...`

    This wrapper explicitly adds @protobuf//:protobuf as a dependency.

    See: https://github.com/protocolbuffers/protobuf/issues/25577

    Args:
        name: the name of the target.
        deps: proto_library targets to generate C++ code for.
        visibility: visibility of the target.
        **kwargs: additional arguments forwarded to cc_proto_library.
    """
    proto_lib_name = name + "_gen"
    _cc_proto_library(
        name = proto_lib_name,
        deps = deps,
        **kwargs
    )

    _cc_proto_library_with_runtime(
        name = name,
        proto_lib_target = ":" + proto_lib_name,
        visibility = visibility,
    )

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
