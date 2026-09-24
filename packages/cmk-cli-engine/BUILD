load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@bazel_skylib//rules:build_test.bzl", "build_test")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//bazel/rules:package_wheel.bzl", "package_wheel")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")
load("//bazel/rules:py_requirements_test.bzl", "py_requirements_test")

exports_files([
    "dev-requirements.in",
    "requirements.in",
])

# NOTE: `cmk.cli` is a PEP 420 namespace package -- never add a cmk/cli/__init__.py.
# The `internal` portion (the plug-in API) is contributed by cmk-plugin-apis.
py_library(
    name = "engine",
    srcs = [
        "cmk/cli/engine/arguments.py",
        "cmk/cli/engine/call.py",
        "cmk/cli/engine/commands.py",
    ],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:tty",
        "//packages/cmk-plugin-apis:cli",
        "//packages/cmk-plugin-apis:discover_plugins",
        "//packages/cmk-trace",
    ],
)

# The application: everything the entry point does once it knows the site root.
# Separate from :main so it can be imported -- and tested -- without OMD_ROOT.
py_library(
    name = "run",
    srcs = ["cmk/cli/engine/run.py"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        ":engine",
        "//packages/cmk-ccc:debug",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:log",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:version-info",
        "//packages/cmk-crash:crash",
        "//packages/cmk-profiling:backend",
        "//packages/cmk-trace",
    ],
)

# The entry point. Separate from :engine because it assembles the application,
# which depends on the commands, which depend on :engine.
py_library(
    name = "main",
    srcs = ["cmk/cli/engine/main.py"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [":run"],
)

py_wheel(
    name = "wheel",
    distribution = "cmk-cli-engine",
    strip_path_prefixes = ["packages/cmk-cli-engine"],
    version = "1.0.0",
    visibility = ["//visibility:public"],
    deps = [
        ":engine",
        ":main",
        ":run",
    ],
)

build_test(
    name = "build_test",
    targets = ["wheel"],
)

package_wheel(
    name = "pkg_tar",
    visibility = ["//visibility:public"],
    whl = "wheel",
)

py_cmk_test(
    name = "unit",
    size = "small",
    srcs = glob(["tests/**/*.py"]),
    args = ["--random-order-bucket=global"],
    use_project_pytest_config = True,
    deps = [
        ":engine",
        ":run",
        "//packages/cmk-plugin-apis:cli",
        requirement("pytest-random-order"),
    ],
)

py_requirements_test(
    name = "requirements-test",
    libs = [
        ":engine",
        ":main",
        ":run",
    ],
    requirements_in = "requirements.in",
)
