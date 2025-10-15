load("@aspect_rules_lint//format:defs.bzl", "format_multirun")
load("@npm//bazel/tools:prettier/package_json.bzl", prettier_bin = "bin")
load("@rules_python//python/entry_points:py_console_script_binary.bzl", "py_console_script_binary")
load("//bazel/rules:sh_expand_template.bzl", "sh_expand_template")

prettier_bin.prettier_binary(
    name = "prettier",
    data = ["//bazel/tools:prettierrc"],
    env = {"BAZEL_BINDIR": "."},
    fixed_args = [
        "--config=\"$$JS_BINARY__RUNFILES\"/$(rlocationpath //bazel/tools:prettierrc)",
        "--ignore-path=\"$$BUILD_WORKSPACE_DIRECTORY/.prettierignore\"",
        "--log-level=warn",
    ],
)

py_console_script_binary(
    name = "djlint",
    data = ["//:pyproject.toml"],
    pkg = "@cmk_requirements//djlint:pkg",
)

sh_expand_template(
    name = "shfmt",
    src = "@multitool//tools/shfmt",
    substitutions = {"{shfmt_bin}": "$(execpath @multitool//tools/shfmt)"},
    template = [
        "#!/bin/sh",
        'cd "${BUILD_WORKSPACE_DIRECTORY:=.}" || exit 1',
        'exec "$BUILD_WORKSPACE_DIRECTORY/{shfmt_bin}" --indent 4 -ci "$@"',
        "",
    ],
    visibility = ["//visibility:public"],
)

genrule(
    name = "taplo",
    srcs = ["@taplo.gz//file"],
    outs = ["taplo_bin"],
    cmd = "gunzip -c $< > $@",
    executable = True,
)

sh_expand_template(
    name = "taplo_quiet",
    src = ":taplo_bin",
    substitutions = {"{taplo_bin}": "$(execpath :taplo_bin)"},
    template = [
        "#!/bin/sh",
        'exec env RUST_LOG=warn "$BUILD_WORKSPACE_DIRECTORY/{taplo_bin}" "$@"',
        "",
    ],
    visibility = ["//visibility:public"],
)

format_multirun(
    name = "format",
    c = "@clang-linux-x86_64//:bin/clang-format",
    cc = "@clang-linux-x86_64//:bin/clang-format",
    css = ":prettier",
    html = ":prettier",
    html_jinja = ":djlint",
    javascript = ":prettier",
    markdown = ":prettier",
    python = "@multitool_hub//tools/ruff",
    rust = "@rules_rust//tools/upstream_wrapper:rustfmt",
    shell = ":shfmt",
    starlark = "@buildifier_prebuilt//:buildifier",
    toml = ":taplo_quiet",
    visibility = ["//visibility:public"],
)

alias(
    name = "check",
    actual = ":format.check",
    visibility = ["//visibility:public"],
)
