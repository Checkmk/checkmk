load("@npm//bazel/tools:npm-groovy-lint/package_json.bzl", groovy_bin = "bin")
load("@npm//bazel/tools:prettier/package_json.bzl", prettier_bin = "bin")
load("@rules_python//python/entry_points:py_console_script_binary.bzl", "py_console_script_binary")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")
load("//bazel/rules:sh_expand_template.bzl", "sh_expand_template")
load(":format_dispatch.bzl", "format_dispatch")

# Opts the formatter's own PowerShell wrapper into PSScriptAnalyzer so we eat
# our own dog food. Also satisfies scripts/in_bazel.sh's "every .ps1 in a
# filegroup" requirement.
filegroup(
    name = "powershell_scripts",
    srcs = ["pwsh_format.ps1"],
    tags = ["lint-with-psscriptanalyzer"],
)

# --cache skips the files that are unchanged since prettier last found them
# formatted. format_dispatch provides a cache directory per target and language:
# - prettier keys its entries by the resolved options, which include the path of
#   the import-sorting plugin that prettier.config.cjs require.resolve()s. That
#   path lies in the runfiles tree of the calling target, so e.g. //:format and
#   //:format.check would invalidate each other's entries.
# - prettier loads its cache file at start and rewrites it on exit, so languages
#   running in parallel would drop each other's entries.
# The "content" strategy compares only the file size before prettier 3.9.0
# (https://github.com/prettier/prettier/issues/18913); "metadata" compares size
# and mtime.
prettier_bin.prettier_binary(
    name = "prettier",
    data = ["//bazel/tools:prettierrc"],
    env = {"BAZEL_BINDIR": "."},
    fixed_args = [
        "--config=\"$$JS_BINARY__RUNFILES\"/$(rlocationpath //bazel/tools:prettierrc)",
        "--ignore-path=\"$$BUILD_WORKSPACE_DIRECTORY/.prettierignore\"",
        "--log-level=warn",
        "--cache",
        "--cache-location=\"$${FORMAT_CACHE_DIR:-$$BUILD_WORKSPACE_DIRECTORY/.format_cache}/prettier\"",
        "--cache-strategy=metadata",
    ],
)

# npm-groovy-lint runs CodeNarc on the JVM and accepts only Java 17 to 24 (its
# lib/codenarc-caller.js passes minimumJavaVersion = 17 and maximumJavaVersion =
# 24 to java-caller). Without a match on PATH java-caller downloads a Temurin JRE
# from github.com into ~/.java-caller while the formatter runs. That download
# bypasses Bazel's downloader, so neither the mirror rewrites in
# bazel_downloader.cfg nor the repository cache apply, and one dropped connection
# fails the whole format check.
#
# Passing --javaexecutable removes the fallback rather than making it cheaper:
# java-caller returns from manageJavaInstall() before any version probe or
# install as soon as the executable is not the literal "java".
#
# --noserver runs CodeNarc in the formatter's own JVM. Otherwise npm-groovy-lint
# starts a CodeNarc server that outlives the run, listens on localhost:7484 and
# serves any npm-groovy-lint version that connects, e.g. from another worktree.
# It also gives every request just 120 s and does not retry a timeout.
groovy_bin.npm_groovy_lint_binary(
    name = "groovy-format",
    data = [
        "//bazel/tools/format:.groovyformatrc.json",
        "@remotejdk17_linux//:bin/java",
        "@remotejdk17_linux//:jdk",
    ],
    env = {"BAZEL_BINDIR": "."},
    fixed_args = [
        "--config=\"$$JS_BINARY__RUNFILES\"/$(rlocationpath //bazel/tools/format:.groovyformatrc.json)",
        "--javaexecutable=\"$$JS_BINARY__RUNFILES\"/$(rlocationpath @remotejdk17_linux//:bin/java)",
        "--noserver",
    ],
    # A JDK cannot be copied into the output tree by rules_js — it lives in an
    # external repository and must keep its internal layout intact.
    no_copy_to_bin = [
        "@remotejdk17_linux//:bin/java",
        "@remotejdk17_linux//:jdk",
    ],
)

py_cmk_test(
    name = "component",
    size = "small",
    srcs = ["tests/component/test_groovy_format.py"],
    data = [":groovy-format"] + glob(["tests/component/groovy/*.groovy"]),
    env = {"GROOVY_FORMAT": "$(rootpath :groovy-format)"},
)

py_console_script_binary(
    name = "djlint",
    data = ["//:pyproject.toml"],
    pkg = "@cmk_requirements//djlint:pkg",
    tags = ["no-mypy"],
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

FORMATTERS = {
    "c": "@multitool_hub//tools/clang-format",
    "cc": "@multitool_hub//tools/clang-format",
    "css": ":prettier",
    "groovy": ":groovy-format",
    "html": ":prettier",
    "html_jinja": ":djlint",
    "javascript": ":prettier",
    "markdown": ":prettier",
    "powershell": ":pwsh-format",
    "python": "@multitool_hub//tools/ruff",
    "rust": "@rules_rust//tools/upstream_wrapper:rustfmt",
    "shell": ":shfmt",
    "starlark": "@buildifier_prebuilt//:buildifier",
    "toml": ":taplo_quiet",
}

format_dispatch(
    name = "format",
    fix_target = "//:format",
    languages = FORMATTERS,
    visibility = ["//visibility:public"],
)

alias(
    name = "check",
    actual = ":format.check",
    visibility = ["//visibility:public"],
)

# One target per language, e.g. `bazel run //bazel/tools/format:python -- <paths>`.
[
    format_dispatch(
        name = language,
        fix_target = "//bazel/tools/format:" + language,
        languages = {language: tool},
        visibility = ["//visibility:public"],
    )
    for language, tool in FORMATTERS.items()
]
