load("@aspect_rules_js//js:defs.bzl", "js_library")
load("@aspect_rules_lint//format:defs.bzl", "format_multirun")
load("@bazel_skylib//rules:copy_file.bzl", "copy_file")
load("@bazel_skylib//rules:native_binary.bzl", "native_binary")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@npm//:defs.bzl", "npm_link_all_packages")
load("@npm//bazel/tools:prettier/package_json.bzl", prettier_bin = "bin")
load("@rules_mypy//mypy:mypy.bzl", "mypy_cli")
load("@rules_python//python:defs.bzl", "py_binary")
load("@rules_python//python/entry_points:py_console_script_binary.bzl", "py_console_script_binary")
load("//bazel/rules:sh_expand_template.bzl", "sh_expand_template")

npm_link_all_packages(name = "node_modules")

js_library(
    name = "prettierrc",
    srcs = ["prettier.config.cjs"],
    visibility = ["//:__subpackages__"],
    deps = [
        ":node_modules/@trivago/prettier-plugin-sort-imports",
    ],
)

py_console_script_binary(
    name = "djlint",
    data = ["//:pyproject.toml"],
    pkg = "@cmk_requirements//djlint:pkg",
)

mypy_cli(
    name = "mypy_cli_original",
    mypy_requirement = requirement("mypy"),
    deps = [
        # for `plugins = ["pydantic.mypy"]`
        requirement("pydantic"),
    ],
)

# Custom mypy wrapper that filters problematic MYPYPATH entries
py_binary(
    name = "mypy_cli",
    srcs = ["mypy_wrapper.py"],
    data = [":mypy_cli_original"],
    main = "mypy_wrapper.py",
    deps = [
        requirement("mypy"),
        requirement("pydantic"),
    ],
)

# TODO: Collect here all formatters we're currently using
format_multirun(
    name = "format",
    c = "@clang-linux-x86_64//:bin/clang-format",
    cc = "@clang-linux-x86_64//:bin/clang-format",
    css = ":prettier",
    html = ":prettier",
    html_jinja = ":djlint",
    javascript = ":prettier",
    python = "@multitool_hub//tools/ruff",
    rust = "@rules_rust//tools/upstream_wrapper:rustfmt",
    shell = ":shfmt",
    starlark = ":buildifier",
    toml = ":taplo_quiet",
    visibility = ["//visibility:public"],
)

native_binary(
    name = "clang_tidy",
    src = "@clang-linux-x86_64//:bin/clang-tidy",
)

filegroup(
    name = "clang_tidy_config",
    srcs = [".clang-tidy"],
    visibility = ["//visibility:public"],
)

sh_binary(
    name = "iwyu_bin",
    srcs = ["run-iwyu"],
)

filegroup(
    name = "iwyu_mappings",
    srcs = glob(["mappings/*.imp"]),
)

copy_file(
    name = "shellcheck_binary",
    src = "@shellcheck",
    out = "shellcheck",
)

# Shell wrapper to execute shellcheck in the callers working directory
sh_binary(
    name = "shellcheck_bin",
    srcs = ["run-shellcheck"],
    data = [":shellcheck_binary"],
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

# TODO: Should we use buildifier more in the way aspect does?
# Currenlty, we try to find all "bazel" files with run-buildifier or run buildifier on a package level.
# rules_lint however does the discovery by itself, see:
# https://docs.aspect.build/workflows/features/buildifier
alias(
    name = "buildifier",
    actual = "@buildifier_prebuilt//:buildifier",
)

alias(
    name = "uv",
    actual = "@multitool//tools/uv",
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

prettier_bin.prettier_binary(
    name = "prettier",
    data = [":prettierrc"],
    env = {"BAZEL_BINDIR": "."},
    fixed_args = [
        "--config=\"$$JS_BINARY__RUNFILES\"/$(rlocationpath :prettierrc)",
        "--ignore-path=\"$$BUILD_WORKSPACE_DIRECTORY/.prettierignore\"",
        "--log-level=warn",
    ],
)
