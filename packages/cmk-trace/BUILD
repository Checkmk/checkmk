load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@omd_packages//omd/packages/rules:package_wheel.bzl", "package_wheel")
load("@rules_python//python:packaging.bzl", "py_wheel")

exports_files([
    "pyproject.toml",
    "requirements.txt",
])

py_library(
    name = "cmk-trace",
    srcs = [
        "cmk/trace/__init__.py",
        "cmk/trace/_config.py",
        "cmk/trace/_propagate.py",
        "cmk/trace/export.py",
        "cmk/trace/logs.py",
        "cmk/trace/py.typed",
    ],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        requirement("opentelemetry-api"),
        requirement("opentelemetry-sdk"),
        requirement("opentelemetry-exporter-otlp"),
        requirement("opentelemetry-semantic-conventions"),
    ],
)

py_wheel(
    name = "wheel",
    distribution = "cmk-trace",
    strip_path_prefixes = ["packages/cmk-trace"],
    # TODO: Duplicated from pyproject.toml
    version = "1.0.0",
    deps = [
        ":cmk-trace",
    ],
)

package_wheel(
    name = "pkg_tar",
    visibility = ["//visibility:public"],
    whl = "wheel",
)
