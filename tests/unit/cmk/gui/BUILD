load("@aspect_rules_py//py:defs.bzl", "py_library", "py_pytest_main", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "conftest",
    testonly = True,
    srcs = ["conftest.py"],
    visibility = ["//tests/unit/cmk/gui:__subpackages__"],
    deps = [
        "//cmk/gui:config",
        "//cmk/gui:http",
        "//cmk/gui:login",
        "//cmk/gui:permissions",
        "//cmk/gui/livestatus_utils",
        "//cmk/gui/utils:roles",
        "//cmk/gui/watolib",
        "//cmk/gui/watolib:password_store",
        "//cmk/utils",
        "//tests/testlib/unit",
        requirement("flask"),
        requirement("pytest"),
        requirement("pytest-mock"),
    ],
)

py_pytest_main(
    name = "__test__",
    deps = [
        requirement("pytest"),
        # pytest-xdist for `--numprocesses=NPROC`
        requirement("pytest-xdist"),
    ],
)

py_library(
    name = "compare_html",
    testonly = True,
    srcs = ["compare_html.py"],
    visibility = ["//tests/unit/cmk/gui:__subpackages__"],
    deps = [
        "//cmk/gui/utils:html",
        requirement("beautifulsoup4"),
    ],
)

py_test(
    name = "availability_tests",
    srcs = glob(["test_availability_*.py"]),
    args = ["tests/unit/cmk/gui"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        ":conftest",
        "//cmk/gui/availability",
        "//cmk/utils",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:site",
        "//tests/unit:conftest",
        requirement("fido2"),
        requirement("marshmallow"),
        requirement("opentelemetry-sdk"),
        requirement("pytest"),
        requirement("python-ldap"),
        requirement("time-machine"),
    ],
)

py_test(
    name = "auth",
    srcs = ["test_auth.py"],
    args = ["tests/unit/cmk/gui/test_auth.py"],
    pytest_main = True,
    deps = [
        "//cmk/gui:auth",
        "//cmk/gui:config",
        "//cmk/gui:pseudo_users",
        "//cmk/utils",
        requirement("pytest"),
    ],
)

py_test(
    name = "autocompleters",
    srcs = ["test_autocompleters.py"],
    args = ["tests/unit/cmk/gui/test_autocompleters.py"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        ":conftest",
        "//cmk/gui:autocompleters",
        "//tests/unit:conftest",
        requirement("pytest"),
    ],
)

py_test(
    name = "breadcrumb",
    srcs = ["test_breadcrumb.py"],
    args = ["tests/unit/cmk/gui/test_breadcrumb.py"],
    pytest_main = True,
    deps = [
        "//cmk/gui:breadcrumb",
        requirement("pytest"),
    ],
)

py_test(
    name = "cron",
    srcs = ["test_cron.py"],
    args = ["tests/unit/cmk/gui/test_cron.py"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        ":conftest",
        "//cmk/gui:cron",
        "//tests/unit:conftest",
        requirement("pytest"),
    ],
)

py_test(
    name = "deprecations",
    srcs = ["test_deprecations.py"],
    args = ["tests/unit/cmk/gui/test_deprecations.py"],
    pytest_main = True,
    deps = [
        "//cmk/gui:deprecations",
        "//cmk/gui/watolib",
        "//cmk/gui/watolib:config_infra",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:user",
        "//packages/cmk-mkp-tool",
        requirement("pytest"),
    ],
)

py_test(
    name = "edition_compatibility",
    srcs = ["test_edition_compatibility.py"],
    args = ["tests/unit/cmk/gui/test_edition_compatibility.py"],
    pytest_main = True,
    deps = [
        "//cmk/gui:sites",
        "//cmk/gui/watolib",
        "//packages/cmk-ccc:version",
        requirement("pytest"),
    ],
)

py_test(
    name = "figures",
    srcs = ["test_figures.py"],
    args = ["tests/unit/cmk/gui/test_figures.py"],
    pytest_main = True,
    deps = [
        "//cmk/gui:figures",
        requirement("pytest"),
    ],
)

py_test(
    name = "main_modules",
    srcs = ["test_main_modules.py"],
    args = ["tests/unit/cmk/gui/test_main_modules.py"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        ":conftest",
        "//cmk/gui:main_modules",
        "//cmk/utils",
        "//tests/unit:conftest",
        requirement("pytest"),
    ],
)

py_test(
    name = "query_filters",
    srcs = ["test_query_filters.py"],
    args = ["tests/unit/cmk/gui/test_query_filters.py"],
    pytest_main = True,
    deps = [
        "//cmk/gui:exceptions",
        "//cmk/gui:query_filters",
        "//cmk/gui:type_defs",
        "//cmk/utils",
        requirement("pytest"),
    ],
)

py_test(
    name = "site_config",
    srcs = ["test_site_config.py"],
    args = ["tests/unit/cmk/gui/test_site_config.py"],
    pytest_main = True,
    deps = [
        "//cmk/gui:site_config",
        "//packages/cmk-ccc:site",
        requirement("pytest"),
    ],
)

py_test(
    name = "userdb_htpasswd_connector",
    srcs = ["test_userdb_htpasswd_connector.py"],
    args = ["tests/unit/cmk/gui/test_userdb_htpasswd_connector.py"],
    pytest_main = True,
    deps = [
        "//cmk/gui:exceptions",
        "//cmk/gui:user_connection_config_types",
        "//cmk/gui/userdb",
        "//packages/cmk-ccc:user",
        "//packages/cmk-crypto",
        requirement("pytest"),
    ],
)

py_test(
    name = "color",
    srcs = ["test_color.py"],
    args = ["tests/unit/cmk/gui/test_color.py"],
    pytest_main = True,
    deps = [
        "//cmk/gui:color",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-plugin-apis:graphing",
        "//packages/cmk-plugin-apis:inventory_ui",
        requirement("pytest"),
    ],
)

py_test(
    name = "escaping",
    srcs = ["test_escaping.py"],
    args = ["tests/unit/cmk/gui/test_escaping.py"],
    pytest_main = True,
    deps = [
        "//cmk/gui/utils:escaping",
        "//cmk/gui/utils:html",
        "//cmk/gui/utils:speaklater",
        requirement("pytest"),
    ],
)

py_test(
    name = "sort",
    srcs = ["test_sort.py"],
    args = ["tests/unit/cmk/gui/test_sort.py"],
    pytest_main = True,
    deps = [
        "//cmk/gui/utils:sort",
        requirement("pytest"),
    ],
)

py_test(
    name = "type_defs",
    srcs = ["test_type_defs.py"],
    args = ["tests/unit/cmk/gui/test_type_defs.py"],
    pytest_main = True,
    deps = [
        "//cmk/gui:type_defs",
        requirement("pytest"),
    ],
)

py_test(
    name = "unit_formatter",
    srcs = ["test_unit_formatter.py"],
    args = ["tests/unit/cmk/gui/test_unit_formatter.py"],
    pytest_main = True,
    deps = [
        "//cmk/gui:unit_formatter",
        requirement("pytest"),
    ],
)

py_test(
    name = "gui",
    srcs = ["__test__.py"] + glob(
        include = ["**/*.py"],
        exclude = [
            "compare_html.py",
            "conftest.py",
            "test_auth.py",
            "test_autocompleters.py",
            "test_availability_*.py",
            "test_breadcrumb.py",
            "test_color.py",
            "test_cron.py",
            "test_deprecations.py",
            "test_edition_compatibility.py",
            "test_escaping.py",
            "test_figures.py",
            "test_main_modules.py",
            "test_query_filters.py",
            "test_site_config.py",
            "test_sort.py",
            "test_type_defs.py",
            "test_unit_formatter.py",
            "test_userdb_htpasswd_connector.py",
        ],
    ),
    args = [
        "--config-file=$(location @//:pyproject.toml)",
        "--import-mode=importlib",
        "--random-order-bucket=global",
        "--dist=loadfile",
        "--numprocesses=4",
    ],
    data = ["@//:pyproject.toml"],
    env = {"EDITION": "community"},
    main = ":__test__.py",
    visibility = ["//visibility:private"],
    deps = [
        ":__test__",
        ":compare_html",
        ":conftest",
        "//tests/unit:conftest",
        requirement("apispec-oneofschema"),
        requirement("beautifulsoup4"),
        requirement("fakeredis"),
        requirement("fastapi"),
        requirement("flask"),
        requirement("httpx"),
        requirement("marshmallow"),
        requirement("marshmallow-oneofschema"),
        requirement("openapi-spec-validator"),
        requirement("opentelemetry-sdk"),
        requirement("polyfactory"),
        requirement("pytest-mock"),
        requirement("pytest-asyncio"),
        requirement("pytest-random-order"),
        requirement("python-dateutil"),
        requirement("python-ldap"),
        requirement("pyyaml"),
        requirement("responses"),
        requirement("time-machine"),
        requirement("werkzeug"),
        "//cmk:validate_config",
        "//cmk/bi",
        "//cmk/gui",
        "//cmk/gui/job_scheduler",
        "//cmk/gui/openapi/spec/spec_generator",
        "//cmk/gui/openapi/spec/spec_generator:_core",
        "//omd/packages/omd:omdlib",
        "//tests/testlib/common:empty_config",
        "//tests/testlib/common:utils",
        "//tests/testlib/unit",
    ],
)
