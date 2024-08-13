load("@rules_python//python:pip.bzl", "compile_pip_requirements")
load("@aspect_rules_py//py:defs.bzl", "py_library", "py_pytest_main", "py_test")
load("@cmk_agent_based//:requirements.bzl", "requirement")

compile_pip_requirements(
    name = "requirements",
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
        ":cmk-agent-based",
        requirement("pytest"),
        requirement("pydantic"),
    ],
)
