load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//bazel/rules:package_wheel.bzl", "package_wheel")

exports_files([
    "pyproject.toml",
    "requirements.txt",
])

py_library(
    name = "cmk-shared-typing",
    srcs = [
        "python/cmk/shared_typing/__init__.py",
        "python/cmk/shared_typing/configuration_entity.py",
        "python/cmk/shared_typing/graph_designer.py",
        "python/cmk/shared_typing/notifications.py",
        "python/cmk/shared_typing/vue_formspec_components.py",
    ],
    imports = ["."],
    visibility = ["//cmk:__pkg__"],
    deps = [
        requirement("black"),
        requirement("datamodel-code-generator"),
        requirement("libcst"),
    ],
)

py_wheel(
    name = "wheel",
    distribution = "cmk-shared-typing",
    strip_path_prefixes = ["packages/cmk-shared-typing/python"],
    # TODO: Duplicated from pyproject.toml
    version = "1.0.0",
    deps = [
        ":cmk-shared-typing",
    ],
)

package_wheel(
    name = "pkg_tar",
    visibility = ["//visibility:public"],
    whl = "wheel",
)
