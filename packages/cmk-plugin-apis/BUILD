load("@aspect_rules_py//py:defs.bzl", "py_library", "py_pytest_main", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//bazel/rules:doctest.bzl", "py_doc_test")
load("//bazel/rules:package_wheel.bzl", "package_wheel")

exports_files([
    "pyproject.toml",
    "requirements.in",
])

py_library(
    name = "cmk-plugin-apis",
    srcs = [
        "cmk/agent_based/legacy/__init__.py",
        "cmk/agent_based/legacy/_loading.py",
        "cmk/agent_based/legacy/v0_unstable.py",
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
        "cmk/graphing/__init__.py",
        "cmk/graphing/v1/__init__.py",
        "cmk/graphing/v1/_localize.py",
        "cmk/graphing/v1/_type_defs.py",
        "cmk/graphing/v1/graphs.py",
        "cmk/graphing/v1/metrics.py",
        "cmk/graphing/v1/perfometers.py",
        "cmk/graphing/v1/translations.py",
        "cmk/rulesets/__init__.py",
        "cmk/rulesets/v1/__init__.py",
        "cmk/rulesets/v1/_localize.py",
        "cmk/rulesets/v1/form_specs/__init__.py",
        "cmk/rulesets/v1/form_specs/_base.py",
        "cmk/rulesets/v1/form_specs/_basic.py",
        "cmk/rulesets/v1/form_specs/_composed.py",
        "cmk/rulesets/v1/form_specs/_levels.py",
        "cmk/rulesets/v1/form_specs/_migrations.py",
        "cmk/rulesets/v1/form_specs/_preconfigured.py",
        "cmk/rulesets/v1/form_specs/validators.py",
        "cmk/rulesets/v1/rule_specs.py",
        "cmk/server_side_calls/__init__.py",
        "cmk/server_side_calls/v1/__init__.py",
        "cmk/server_side_calls/v1/_active_checks.py",
        "cmk/server_side_calls/v1/_special_agents.py",
        "cmk/server_side_calls/v1/_utils.py",
    ],
    imports = ["."],
    visibility = ["//cmk:__pkg__"],
    deps = [
        requirement("pydantic"),
    ],
)

py_doc_test(
    name = "doctest",
    size = "small",
    srcs = ["cmk-plugin-apis"],
    tags = ["no-mypy"],
)

py_pytest_main(
    name = "__test__",
    deps = [
        requirement("pytest"),
    ],
)

py_test(
    name = "unit",
    size = "small",
    srcs = glob(["tests/**/*.py"]) + [":__test__.py"],
    main = "__test__.py",
    deps = [
        ":__test__",
        ":cmk-plugin-apis",
        requirement("pytest"),
    ],
)

py_wheel(
    name = "wheel",
    distribution = "cmk-plugin-apis",
    strip_path_prefixes = ["packages/cmk-plugin-apis"],
    # TODO: Duplicated from pyproject.toml
    version = "1.0.0",
    deps = [":cmk-plugin-apis"],
)

package_wheel(
    name = "pkg_tar",
    visibility = ["//visibility:public"],
    whl = "wheel",
)
