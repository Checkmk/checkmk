load("@aspect_rules_py//py:defs.bzl", "py_library", "py_pytest_main", "py_test")
load("@cmk_werks//:requirements.bzl", "requirement")
load("@rules_python//python:pip.bzl", "compile_pip_requirements")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("@omd_packages//omd/packages/rules:package_wheel.bzl", "package_wheel")

filegroup(
    name = "files",
    srcs = [
        "Pipfile",
        "Pipfile.lock",
        "cmk/werks/__init__.py",
        "cmk/werks/cli.py",
        "cmk/werks/config.py",
        "cmk/werks/convert.py",
        "cmk/werks/error.py",
        "cmk/werks/format.py",
        "cmk/werks/load.py",
        "cmk/werks/markup.py",
        "cmk/werks/models.py",
        "cmk/werks/parse.py",
        "cmk/werks/validate.py",
        "pyproject.toml",
        "setup.cfg",
    ],
    visibility = ["//visibility:public"],
)

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
    visibility = ["//visibility:public"],
)

py_pytest_main(
    name = "__test__",
)

py_test(
    name = "unit",
    srcs = glob(["tests/**/*.py"]) + [":__test__.py"],
    # TODO: Duplicated from pyproject.toml
    args = [
        "--import-mode=importlib",
        "--doctest-modules",
    ],
    imports = ["."],
    main = ":__test__.py",
    deps = [
        ":__test__",
        ":cmk-werks",
        requirement("pytest"),
        requirement("markdown"),
        requirement("lxml"),
        requirement("pydantic"),
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

package_wheel(wheel_target = "wheel")
