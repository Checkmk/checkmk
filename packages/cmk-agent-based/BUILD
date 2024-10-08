load("@aspect_rules_lint//format:defs.bzl", "format_multirun")
load("@aspect_rules_py//py:defs.bzl", "py_library", "py_pytest_main", "py_test")
load("@cmk_agent_based//:requirements.bzl", "requirement")
load("@omd_packages//omd/packages/rules:package_wheel.bzl", "package_wheel")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("@rules_python//python:pip.bzl", "compile_pip_requirements")
load(":linters.bzl", "ruff_test")

exports_files(["pyproject.toml"])

compile_pip_requirements(
    name = "requirements",
    extra_args = ["--quiet"],
    requirements_in = "pyproject.toml",
    requirements_txt = "requirements_lock.txt",  # shall exist, emtpy is okay
)

py_library(
    name = "cmk-agent-based",
    srcs = [
        "cmk/agent_based/prediction_backend.py",
        "cmk/agent_based/v1/__init__.py",
        "cmk/agent_based/v1/_check_levels.py",
        "cmk/agent_based/v1/_checking_classes.py",
        "cmk/agent_based/v1/_detection.py",
        "cmk/agent_based/v1/_inventory_classes.py",
        "cmk/agent_based/v1/_regex.py",
        "cmk/agent_based/v1/_snmp.py",
        "cmk/agent_based/v1/_value_store_utils.py",
        "cmk/agent_based/v1/clusterize.py",
        "cmk/agent_based/v1/register.py",
        "cmk/agent_based/v1/render.py",
        "cmk/agent_based/v1/type_defs.py",
        "cmk/agent_based/v1/value_store.py",
        "cmk/agent_based/v2/__init__.py",
        "cmk/agent_based/v2/_check_levels.py",
        "cmk/agent_based/v2/_get_average.py",
        "cmk/agent_based/v2/_plugins.py",
        "cmk/agent_based/v2/clusterize.py",
        "cmk/agent_based/v2/render.py",
    ],
    imports = ["."],
    visibility = ["//cmk:__pkg__"],
    deps = [
        requirement("pydantic"),
    ],
)

ruff_test(
    name = "ruff_lint",
    size = "small",
    srcs = [
        ":cmk-agent-based",
        ":unit",
    ],
)

py_pytest_main(
    name = "__test__",
)

py_test(
    name = "unit",
    size = "small",
    srcs = glob(["tests/**/*.py"]) + [":__test__.py"],
    args = ["--config-file=$(location pyproject.toml)"],
    data = ["pyproject.toml"],
    imports = ["."],
    main = ":__test__.py",
    deps = [
        ":__test__",
        ":cmk-agent-based",
        requirement("pytest"),
    ],
)

format_multirun(
    name = "format",
    python = "@aspect_rules_lint//format:ruff",
)

py_wheel(
    name = "wheel",
    distribution = "cmk-agent-based",
    strip_path_prefixes = ["packages/cmk-agent-based"],
    # TODO: Duplicated from pyproject.toml
    version = "1.0.0",
    deps = [":cmk-agent-based"],
)

package_wheel(
    name = "pkg_tar",
    visibility = ["//visibility:public"],
    whl = "wheel",
)
