load("@aspect_rules_py//py:defs.bzl", "py_library", "py_pytest_main", "py_test")
load("@cmk_werks//:requirements.bzl", "requirement")
load("@omd_packages//omd/packages/rules:package_wheel.bzl", "package_wheel")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("@rules_python//python:pip.bzl", "compile_pip_requirements")

exports_files(["pyproject.toml"])

compile_pip_requirements(
    name = "requirements",
    requirements_in = "pyproject.toml",
    requirements_txt = "requirements_lock.txt",  # shall exist, emtpy is okay
)

py_library(
    name = "cmk-werks",
    srcs = [
        "cmk/werks/__init__.py",
        "cmk/werks/cli.py",
        "cmk/werks/collect.py",
        "cmk/werks/config.py",
        "cmk/werks/convert.py",
        "cmk/werks/error.py",
        "cmk/werks/format.py",
        "cmk/werks/load.py",
        "cmk/werks/markup.py",
        "cmk/werks/models.py",
        "cmk/werks/parse.py",
        "cmk/werks/validate.py",
    ],
    imports = ["."],
    visibility = ["//cmk:__pkg__"],
    deps = [
        requirement("markdown"),
        requirement("lxml"),
        requirement("pydantic"),
        requirement("GitPython"),
    ],
)

py_pytest_main(
    name = "__test__",
)

py_test(
    name = "unit",
    srcs = glob(["tests/**/*.py"]) + [":__test__.py"],
    args = ["--config-file=$(location pyproject.toml)"],
    data = ["pyproject.toml"],
    imports = ["."],
    main = ":__test__.py",
    deps = [
        ":__test__",
        ":cmk-werks",
        requirement("pytest"),
    ],
)

py_wheel(
    name = "wheel",
    distribution = "cmk-werks",
    strip_path_prefixes = ["packages/cmk-werks"],
    # TODO: Duplicated from pyproject.toml
    version = "1.0.0",
    deps = [
        ":cmk-werks",
    ],
)

package_wheel(
    name = "pkg_tar",
    visibility = ["//visibility:public"],
    whl = "wheel",
)
