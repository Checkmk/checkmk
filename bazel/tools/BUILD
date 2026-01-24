load("@aspect_rules_js//js:defs.bzl", "js_library")
load("@bazel_env.bzl", "bazel_env")
load("@bazel_skylib//rules:copy_file.bzl", "copy_file")
load("@bazel_skylib//rules:native_binary.bzl", "native_binary")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@npm//:defs.bzl", "npm_link_all_packages")
load("@npm//bazel/tools:npm-groovy-lint/package_json.bzl", groovy_bin = "bin")
load("@rules_mypy//mypy:mypy.bzl", "mypy_cli")
load("@rules_python//python:defs.bzl", "py_binary")
load("@rules_python//python/entry_points:py_console_script_binary.bzl", "py_console_script_binary")
load("@rules_uv//uv:pip.bzl", "pip_compile")
load("@tools_requirements//:requirements.bzl", tooling_pip = "requirement")

pip_compile(
    name = "requirements",
    requirements_in = "requirements.in",
    requirements_txt = "requirements.txt",
    tags = ["manual"],
)

npm_link_all_packages(name = "node_modules")

js_library(
    name = "prettierrc",
    srcs = ["prettier.config.cjs"],
    visibility = ["//:__subpackages__"],
    deps = [
        ":node_modules/@trivago/prettier-plugin-sort-imports",
    ],
)

groovy_bin.npm_groovy_lint_binary(
    name = "groovy-lint",
    data = ["//bazel/tools:.groovylintrc.json"],
    env = {"BAZEL_BINDIR": "."},
    fixed_args = [
        "--config=\"$$JS_BINARY__RUNFILES\"/$(rlocationpath //bazel/tools:.groovylintrc.json)",
    ],
)

mypy_cli(
    name = "mypy_cli_original",
    mypy_requirement = requirement("mypy"),
    python_version = "3.13",
    deps = [
        # for `plugins = ["pydantic.mypy"]`
        requirement("pydantic"),
    ],
)

py_console_script_binary(
    name = "bandit",
    pkg = requirement("bandit"),
    tags = [
        "manual",
        "no-mypy",
    ],
)

py_console_script_binary(
    name = "semgrep",
    pkg = tooling_pip("semgrep"),
    script = "pysemgrep",
    tags = [
        "manual",
        "no-mypy",
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

native_binary(
    name = "clang_tidy",
    src = "@clang-linux-x86_64//:bin/clang-tidy",
)

filegroup(
    name = "clang_tidy_config",
    srcs = ["//:.clang-tidy"],
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

alias(
    name = "uv",
    actual = "@multitool//tools/uv",
)

bazel_env(
    name = "bazel_env",
    toolchains = {},
    tools = {
        "bandit": ":bandit",
        "mypy": ":mypy_cli_original",
        "osslsigncode": "@osslsigncode",
        "pnpm": "@pnpm",
        "semgrep": ":semgrep",
        "uv": "@multitool//tools/uv",
        "genhtml": "@lcov//:genhtml",
    },
)

py_binary(
    name = "extract_os_packages",
    srcs = ["extract_os_packages.py"],
    main = "extract_os_packages.py",
    visibility = ["//visibility:public"],
)
