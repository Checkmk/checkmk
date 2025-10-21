load("@aspect_rules_py//py:defs.bzl", "py_library", "py_pytest_main", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//bazel/rules:doctest.bzl", "py_doc_test")
load("//bazel/rules:package_wheel.bzl", "package_wheel")

exports_files([
    "dev-requirements.in",
    "pyproject.toml",
    "requirements.in",
])

py_library(
    name = "agent_based",
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
    ],
    data = ["cmk/agent_based/py.typed"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        requirement("pydantic"),
    ],
)

py_library(
    name = "bakery",
    srcs = [
        "cmk/bakery/v1/__init__.py",
        "cmk/bakery/v1/_artifact_types.py",
        "cmk/bakery/v1/_constants.py",
        "cmk/bakery/v1/_function_types.py",
        "cmk/bakery/v2_alpha/__init__.py",
        "cmk/bakery/v2_alpha/_artifact_types.py",
        "cmk/bakery/v2_alpha/_config.py",
        "cmk/bakery/v2_alpha/_plugins.py",
    ],
    data = ["cmk/bakery/py.typed"],
    imports = ["."],
    visibility = ["//visibility:public"],
)

py_library(
    name = "graphing",
    srcs = [
        "cmk/graphing/__init__.py",
        "cmk/graphing/v1/__init__.py",
        "cmk/graphing/v1/_localize.py",
        "cmk/graphing/v1/_type_defs.py",
        "cmk/graphing/v1/graphs.py",
        "cmk/graphing/v1/metrics.py",
        "cmk/graphing/v1/perfometers.py",
        "cmk/graphing/v1/translations.py",
    ],
    data = [
        "cmk/graphing/py.typed",
    ],
    imports = ["."],
    visibility = ["//visibility:public"],
)

py_library(
    name = "rulesets",
    srcs = [
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
    ],
    data = ["cmk/rulesets/py.typed"],
    imports = ["."],
    visibility = ["//visibility:public"],
)

py_library(
    name = "password_store",
    srcs = [
        "cmk/password_store/v1_alpha/__init__.py",
        "cmk/password_store/v1_alpha/_impl.py",
    ],
    data = ["cmk/password_store/py.typed"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        requirement("cryptography"),
    ],
)

py_library(
    name = "server_side_calls",
    srcs = [
        "cmk/server_side_calls/__init__.py",
        "cmk/server_side_calls/alpha/__init__.py",
        "cmk/server_side_calls/alpha/_active_checks.py",
        "cmk/server_side_calls/alpha/_special_agents.py",
        "cmk/server_side_calls/v1/__init__.py",
        "cmk/server_side_calls/v1/_active_checks.py",
        "cmk/server_side_calls/v1/_special_agents.py",
        "cmk/server_side_calls/v1/_utils.py",
    ],
    data = ["cmk/server_side_calls/py.typed"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        requirement("pydantic"),
    ],
)

py_library(
    name = "inventory_ui",
    srcs = [
        "cmk/inventory_ui/__init__.py",
        "cmk/inventory_ui/v1_alpha/__init__.py",
        "cmk/inventory_ui/v1_alpha/_localize.py",
        "cmk/inventory_ui/v1_alpha/_node.py",
        "cmk/inventory_ui/v1_alpha/_style.py",
        "cmk/inventory_ui/v1_alpha/_unit.py",
    ],
    data = ["cmk/inventory_ui/py.typed"],
    imports = ["."],
    visibility = ["//visibility:public"],
)

py_doc_test(
    name = "doctest",
    size = "small",
    srcs = [
        ":agent_based",
        ":bakery",
        ":graphing",
        ":inventory_ui",
        ":rulesets",
        ":server_side_calls",
    ],
    tags = ["no-mypy"],
)

py_pytest_main(
    name = "__test__",
    deps = [
        requirement("pytest"),
    ],
)

py_test(
    name = "agent_based-test",
    size = "small",
    srcs = glob(["tests/cmk/agent_based/**/*.py"]) + [":__test__.py"],
    main = ":__test__.py",
    deps = [
        ":__test__",
        ":agent_based",
        requirement("pytest"),
    ],
)

py_test(
    name = "bakery-test",
    size = "small",
    srcs = glob(["tests/cmk/bakery/**/*.py"]) + [":__test__.py"],
    main = ":__test__.py",
    deps = [
        ":__test__",
        ":bakery",
        requirement("pytest"),
    ],
)

py_test(
    name = "graphing-test",
    size = "small",
    srcs = glob(["tests/cmk/graphing/**/*.py"]) + [":__test__.py"],
    main = ":__test__.py",
    deps = [
        ":__test__",
        ":graphing",
        requirement("pytest"),
    ],
)

py_test(
    name = "rulesets-test",
    size = "small",
    srcs = glob(["tests/cmk/rulesets/**/*.py"]) + [":__test__.py"],
    main = "__test__.py",
    deps = [
        ":__test__",
        ":rulesets",
        requirement("pytest"),
    ],
)

py_test(
    name = "password_store-test",
    size = "small",
    srcs = glob(["tests/cmk/password_store/**/*.py"]) + [":__test__.py"],
    main = ":__test__.py",
    deps = [
        ":__test__",
        ":password_store",
        requirement("cryptography"),
        requirement("pytest"),
    ],
)

py_test(
    name = "server_side_calls-test",
    size = "small",
    srcs = glob(["tests/cmk/server_side_calls/**/*.py"]) + [":__test__.py"],
    main = ":__test__.py",
    deps = [
        ":__test__",
        ":server_side_calls",
        requirement("pytest"),
    ],
)

py_test(
    name = "inventory_ui-test",
    size = "small",
    srcs = glob(["tests/cmk/inventory_ui/**/*.py"]) + [":__test__.py"],
    main = ":__test__.py",
    deps = [
        ":__test__",
        ":inventory_ui",
        requirement("pytest"),
    ],
)

py_wheel(
    name = "wheel",
    distribution = "cmk-plugin-apis",
    strip_path_prefixes = ["packages/cmk-plugin-apis"],
    # TODO: Duplicated from pyproject.toml
    version = "1.0.0",
    deps = [
        ":agent_based",
        ":bakery",
        ":graphing",
        ":inventory_ui",
        ":password_store",
        ":py_typed",
        ":rulesets",
        ":server_side_calls",
    ],
)

filegroup(
    name = "py_typed",
    srcs = [
        "cmk/agent_based/py.typed",
        "cmk/bakery/py.typed",
        "cmk/graphing/py.typed",
        "cmk/inventory_ui/py.typed",
        "cmk/password_store/py.typed",
        "cmk/rulesets/py.typed",
        "cmk/server_side_calls/py.typed",
    ],
)

package_wheel(
    name = "pkg_tar",
    visibility = ["//visibility:public"],
    whl = "wheel",
)
