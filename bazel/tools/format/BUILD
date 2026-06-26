load("@aspect_rules_lint//format:defs.bzl", "format_multirun")
load("@npm//bazel/tools:npm-groovy-lint/package_json.bzl", groovy_bin = "bin")
load("@npm//bazel/tools:prettier/package_json.bzl", prettier_bin = "bin")
load("@rules_python//python/entry_points:py_console_script_binary.bzl", "py_console_script_binary")
load("//bazel/rules:sh_expand_template.bzl", "sh_expand_template")

# Opts the formatter's own PowerShell wrapper into PSScriptAnalyzer so we eat
# our own dog food. Also satisfies scripts/in_bazel.sh's "every .ps1 in a
# filegroup" requirement.
filegroup(
    name = "powershell_scripts",
    srcs = ["pwsh_format.ps1"],
    tags = ["lint-with-psscriptanalyzer"],
)

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

groovy_bin.npm_groovy_lint_binary(
    name = "groovy-format",
    data = ["//bazel/tools/format:.groovyformatrc.json"],
    env = {"BAZEL_BINDIR": "."},
    fixed_args = [
        "--config=\"$$JS_BINARY__RUNFILES\"/$(rlocationpath //bazel/tools/format:.groovyformatrc.json)",
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

sh_binary(
    name = "pwsh-format",
    srcs = ["pwsh_format_runner.sh"],
    data = [
        "pwsh_format.ps1",
        "@psscriptanalyzer//:files",
        "@pwsh",
    ],
    visibility = ["//visibility:public"],
    deps = ["@bazel_tools//tools/bash/runfiles"],
)

format_multirun(
    name = "format",
    c = "@clang-linux-x86_64//:bin/clang-format",
    cc = "@clang-linux-x86_64//:bin/clang-format",
    css = ":prettier",
    groovy = ":groovy-format",
    html = ":prettier",
    html_jinja = ":djlint",
    javascript = ":prettier",
    # Must be 0 (not e.g. 4) — any non-zero value means sequential execution.
    # See https://github.com/keith/rules_multirun/issues/82
    jobs = 0,
    markdown = ":prettier",
    powershell = ":pwsh-format",
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

_PER_LANGUAGE_FORMATTERS = {
    "c": "format_C_with_clang-format",
    "cc": "format_C++_with_clang-format",
    "css": "format_CSS_with_prettier",
    "groovy": "format_Groovy_with_groovy-format",
    "html": "format_HTML_with_prettier",
    "html_jinja": "format_HTML_Jinja_with_djlint",
    "javascript": "format_JavaScript_with_prettier",
    "markdown": "format_Markdown_with_prettier",
    "powershell": "format_PowerShell_with_ps-format",
    "python": "format_Python_with_ruff",
    "rust": "format_Rust_with_rustfmt",
    "shell": "format_Shell_with_shfmt",
    "starlark": "format_Starlark_with_buildifier",
    "toml": "format_TOML_with_taplo",
}

[
    alias(
        name = name,
        actual = ":" + target,
        visibility = ["//visibility:public"],
    )
    for name, target in _PER_LANGUAGE_FORMATTERS.items()
]
