"""shared_typing: Python and TypeScript types generated from a package's own JSON schemas."""

load("@aspect_bazel_lib//lib:copy_to_bin.bzl", "COPY_FILE_TO_BIN_TOOLCHAINS", "copy_files_to_bin_actions")
load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@bazel_skylib//lib:paths.bzl", "paths")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//bazel/rules:shared_typing_generators.bzl", "JSON2PYTHON_LITERAL_ENUM_ARGS")
load("//omd/packages/Python:version.bzl", "PYTHON_MAJOR_DOT_MINOR")

_TS_HEADER = """/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/* eslint-disable */
/**
 * This file is auto-generated from a JSON schema via //bazel/rules:shared_typing.bzl.
 * Do not edit manually.
 */
"""

def _schemas(ctx):
    # One directory, so that `$ref`s between schemas resolve alike for both generators.
    if len({src.dirname: None for src in ctx.files.srcs}) != 1:
        fail("shared_typing srcs must all be in one directory: {}".format(ctx.files.srcs))
    return ctx.files.srcs

def _declare_module(ctx, schema, extension):
    return ctx.actions.declare_file(
        paths.join(ctx.attr.out_dir, paths.replace_extension(schema.basename, extension)),
    )

def _python_types_impl(ctx):
    schemas = _schemas(ctx)
    modules = []
    for schema in schemas:
        module = _declare_module(ctx, schema, ".py")
        ctx.actions.run(
            executable = ctx.attr._datamodel_codegen[DefaultInfo].files_to_run,
            arguments = [
                "--input=" + schema.path,
                "--input-file-type=jsonschema",
                "--output=" + module.path,
                "--target-python-version=" + PYTHON_MAJOR_DOT_MINOR,
            ] + JSON2PYTHON_LITERAL_ENUM_ARGS + [
                "--custom-file-header-path=" + ctx.file._header.path,
            ],
            inputs = schemas + [ctx.file._header],
            outputs = [module],
            mnemonic = "Json2Python",
        )
        modules.append(module)

    init = ctx.actions.declare_file(paths.join(ctx.attr.out_dir, "__init__.py"))
    ctx.actions.symlink(output = init, target_file = ctx.file._header)
    py_typed = ctx.actions.declare_file(paths.join(ctx.attr.out_dir, "py.typed"))
    ctx.actions.write(py_typed, "")
    return [
        DefaultInfo(files = depset(modules + [init])),
        OutputGroupInfo(py_typed = depset([py_typed])),
    ]

_python_types = rule(
    implementation = _python_types_impl,
    attrs = {
        "out_dir": attr.string(mandatory = True),
        "srcs": attr.label_list(allow_files = [".json"], mandatory = True),
        "_datamodel_codegen": attr.label(
            default = Label("//bazel/tools/shared_typing:datamodel_codegen"),
            executable = True,
            cfg = "exec",
        ),
        "_header": attr.label(
            default = Label("//bazel/rules:shared_typing_header_py.txt"),
            allow_single_file = True,
        ),
    },
)

def _typescript_types_impl(ctx):
    # json2ts runs in the bin directory and resolves `$ref`s from --cwd.
    schemas = copy_files_to_bin_actions(ctx, _schemas(ctx))
    modules = []
    for schema in schemas:
        module = _declare_module(ctx, schema, ".ts")
        ctx.actions.run(
            executable = ctx.attr._json2ts[DefaultInfo].files_to_run,
            arguments = [
                "--additionalProperties=false",
                "--declareExternallyReferenced",
                "--bannerComment=" + _TS_HEADER,
                "--cwd=" + paths.dirname(schema.short_path),
                "--input=" + schema.short_path,
                "--output=" + module.short_path,
            ],
            inputs = schemas,
            outputs = [module],
            env = {"BAZEL_BINDIR": ctx.bin_dir.path},
            mnemonic = "Json2Typescript",
        )
        modules.append(module)
    return [DefaultInfo(files = depset(modules))]

_typescript_types = rule(
    implementation = _typescript_types_impl,
    attrs = {
        "out_dir": attr.string(mandatory = True),
        "srcs": attr.label_list(allow_files = [".json"], mandatory = True),
        "_json2ts": attr.label(
            default = Label("//bazel/tools/shared_typing:json2ts"),
            executable = True,
            cfg = "exec",
        ),
    },
    toolchains = COPY_FILE_TO_BIN_TOOLCHAINS,
)

def _shared_typing_impl(name, visibility, srcs, python_package, typescript_dir):
    _python_types(
        name = name + "_py_files",
        srcs = srcs,
        out_dir = python_package,
    )
    py_library(
        name = name + "_py",
        srcs = [":" + name + "_py_files"],
        imports = ["."],
        visibility = visibility,
    )
    native.filegroup(
        name = name + "_py_typed",
        srcs = [":" + name + "_py_files"],
        output_group = "py_typed",
        visibility = visibility,
    )
    py_wheel(
        name = name + "_wheel",
        distribution = python_package.replace("/", "-").replace("_", "-"),
        strip_path_prefixes = [native.package_name()],
        version = "1.0.0",
        visibility = ["//:__pkg__"],
        deps = [":" + name + "_py", ":" + name + "_py_typed"],
    )
    _typescript_types(
        name = name + "_ts",
        srcs = srcs,
        out_dir = typescript_dir,
        visibility = visibility,
    )

shared_typing = macro(
    doc = """Generates Python and TypeScript types from JSON schemas, one module per schema.

    Creates `<name>_py`, a py_library of frozen keyword-only dataclasses, its
    `<name>_py_typed` marker for the package's py_wheel, `<name>_wheel`, the
    Python modules alone for the `.venv`, and `<name>_ts`, the TypeScript modules
    for the package's vue_library `srcs`.

    Beyond BUILD, the package's tsconfig.json must resolve the generated modules
    from `bazel-bin`, module_layers.toml must allow `python_package` (dotted)
    for the components importing it, and `//:create_venv` must install
    `<name>_wheel`. The parent of `python_package` must be a namespace package.
    """,
    implementation = _shared_typing_impl,
    attrs = {
        "python_package": attr.string(
            doc = "Directory below the package the Python modules go to, e.g. `cmk/foo/shared_typing`.",
            configurable = False,
            mandatory = True,
        ),
        "srcs": attr.label_list(
            doc = "The JSON schemas, all in one directory. They may `$ref` each other.",
            allow_files = [".json"],
            mandatory = True,
        ),
        "typescript_dir": attr.string(
            doc = "Directory below the package the TypeScript modules go to.",
            configurable = False,
            mandatory = True,
        ),
    },
)
