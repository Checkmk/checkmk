load("@aspect_rules_py//py:defs.bzl", "py_library", "py_test")
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

py_library(
    name = "init_py",
    testonly = True,
    srcs = ["__init__.py"],
    visibility = ["//tests/unit/cmk/gui:__subpackages__"],
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
    name = "background_job",
    srcs = ["test_background_job.py"],
    args = ["tests/unit/cmk/gui/test_background_job.py"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        ":conftest",
        "//cmk/gui:log",
        "//cmk/gui/background_job/job",
        "//cmk/utils",
        "//packages/cmk-trace",
        "//tests/unit:conftest",
        requirement("opentelemetry-sdk"),
        requirement("pytest"),
    ],
)

py_test(
    name = "backup_unit",
    srcs = ["test_backup_unit.py"],
    args = ["tests/unit/cmk/gui/test_backup_unit.py"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        ":conftest",
        "//cmk/gui:logged_in",
        "//cmk/gui/backup",
        "//cmk/utils",
        "//packages/cmk-ccc:user",
        "//packages/cmk-ccc:version",
        "//packages/cmk-crypto",
        "//tests/unit:conftest",
        requirement("pytest"),
    ],
)

py_test(
    name = "cmkcert",
    srcs = ["test_cmkcert.py"],
    args = ["tests/unit/cmk/gui/test_cmkcert.py"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        ":conftest",
        "//cmk/gui:cmkcert",
        "//cmk/gui:config",
        "//cmk/utils",
        "//packages/cmk-ccc:site",
        "//tests/unit:conftest",
        requirement("pytest"),
        requirement("pytest-mock"),
    ],
)

py_test(
    name = "crash_handler",
    srcs = ["test_crash_handler.py"],
    args = ["tests/unit/cmk/gui/test_crash_handler.py"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        ":conftest",
        "//cmk/gui:crash_handler",
        "//packages/cmk-ccc:crash-reporting",
        "//tests/unit:conftest",
        requirement("pytest"),
    ],
)

py_test(
    name = "dashboard_tests",
    srcs = ["test_dashboard.py"],
    args = ["tests/unit/cmk/gui/test_dashboard.py"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        ":conftest",
        "//cmk/gui/dashboard",
        "//packages/cmk-ccc:plugin-registry",
        "//tests/unit:conftest",
        requirement("pytest"),
    ],
)

py_test(
    name = "forms",
    srcs = ["test_forms.py"],
    args = ["tests/unit/cmk/gui/test_forms.py"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        ":conftest",
        "//cmk/gui:forms",
        "//cmk/gui:http",
        "//cmk/gui/wato",
        "//tests/unit:conftest",
        requirement("pytest"),
    ],
)

py_test(
    name = "graphing_main",
    srcs = ["test_graphing_main.py"],
    args = ["tests/unit/cmk/gui/test_graphing_main.py"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        ":conftest",
        "//cmk/gui:graphing_main",
        "//cmk/gui:unit_formatter",
        "//cmk/gui/graphing",
        "//packages/cmk-plugin-apis:graphing",
        "//tests/unit:conftest",
        requirement("pytest"),
    ],
)

py_test(
    name = "gui_config",
    srcs = ["test_gui_config.py"],
    args = ["tests/unit/cmk/gui/test_gui_config.py"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        ":conftest",
        "//cmk/gui:config",
        "//cmk/utils",
        "//tests/unit:conftest",
        requirement("pytest"),
    ],
)

py_test(
    name = "gui_hooks",
    srcs = ["test_gui_hooks.py"],
    args = ["tests/unit/cmk/gui/test_gui_hooks.py"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        ":conftest",
        "//cmk/gui:hooks",
        "//cmk/gui:pages",
        "//packages/cmk-ccc:exceptions",
        "//tests/unit:conftest",
        requirement("pytest"),
        requirement("pytest-mock"),
    ],
)

py_test(
    name = "http",
    srcs = ["test_http.py"],
    args = ["tests/unit/cmk/gui/test_http.py"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        ":conftest",
        "//cmk/gui:exceptions",
        "//cmk/gui:http",
        "//cmk/gui:script_helpers",
        "//tests/unit:conftest",
        requirement("pytest"),
        requirement("werkzeug"),
    ],
)

py_test(
    name = "i18n",
    srcs = ["test_i18n.py"],
    args = ["tests/unit/cmk/gui/test_i18n.py"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        ":conftest",
        "//cmk/gui:i18n",
        "//cmk/gui:script_helpers",
        "//cmk/utils",
        "//tests/unit:conftest",
        requirement("flask"),
        requirement("pytest"),
    ],
)

py_test(
    name = "index",
    srcs = ["test_index.py"],
    args = ["tests/unit/cmk/gui/test_index.py"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        ":conftest",
        "//cmk/gui:config",
        "//cmk/gui:http",
        "//cmk/gui:logged_in",
        "//cmk/gui:main",
        "//cmk/gui:session",
        "//tests/unit:conftest",
        requirement("pytest"),
        requirement("werkzeug"),
    ],
)

py_test(
    name = "key_mgmt",
    srcs = ["test_key_mgmt.py"],
    args = ["tests/unit/cmk/gui/test_key_mgmt.py"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        ":conftest",
        "//cmk/gui:key_mgmt",
        "//cmk/utils",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:user",
        "//packages/cmk-crypto",
        "//tests/unit:conftest",
        requirement("pytest"),
    ],
)

py_test(
    name = "logged_in",
    srcs = ["test_logged_in.py"],
    args = ["tests/unit/cmk/gui/test_logged_in.py"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        ":conftest",
        "//cmk/gui:config",
        "//cmk/gui:exceptions",
        "//cmk/gui:hooks",
        "//cmk/gui:logged_in",
        "//cmk/gui:permissions",
        "//cmk/gui:role_types",
        "//cmk/gui:session",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:user",
        "//tests/unit:conftest",
        requirement("pytest"),
        requirement("pytest-mock"),
    ],
)

py_test(
    name = "login_unit",
    srcs = ["test_login_unit.py"],
    args = ["tests/unit/cmk/gui/test_login_unit.py"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        ":conftest",
        "//cmk/gui:auth",
        "//cmk/gui:config",
        "//cmk/gui:http",
        "//cmk/gui:logged_in",
        "//cmk/gui:login",
        "//cmk/gui:script_helpers",
        "//cmk/gui:session",
        "//cmk/gui:type_defs",
        "//cmk/gui/userdb",
        "//packages/cmk-ccc:user",
        "//tests/unit:conftest",
        requirement("flask"),
        requirement("pytest"),
        requirement("werkzeug"),
    ],
)

py_test(
    name = "monitored_service_description_autocompleter",
    srcs = ["test_monitored_service_description_autocompleter.py"],
    args = ["tests/unit/cmk/gui/test_monitored_service_description_autocompleter.py"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        ":conftest",
        "//cmk/gui:config",
        "//cmk/gui/visuals",
        "//packages/cmk-livestatus-client:livestatus-api",
        "//tests/unit:conftest",
        requirement("pytest"),
    ],
)

py_test(
    name = "page_menu",
    srcs = ["test_page_menu.py"],
    args = ["tests/unit/cmk/gui/test_page_menu.py"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        ":conftest",
        "//cmk/gui:page_menu",
        "//cmk/gui:type_defs",
        "//tests/unit:conftest",
        requirement("pytest"),
    ],
)

py_test(
    name = "pages",
    srcs = ["test_pages.py"],
    args = ["tests/unit/cmk/gui/test_pages.py"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        ":conftest",
        "//cmk/gui:config",
        "//cmk/gui:http",
        "//cmk/gui:pages",
        "//tests/unit:conftest",
        requirement("pytest"),
        requirement("werkzeug"),
    ],
)

py_test(
    name = "pagetypes",
    srcs = ["test_pagetypes.py"],
    args = ["tests/unit/cmk/gui/test_pagetypes.py"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        ":conftest",
        "//cmk/gui:script_helpers",
        "//cmk/gui/pagetypes",
        "//tests/unit:conftest",
        requirement("pytest"),
    ],
)

py_test(
    name = "permissions",
    srcs = ["test_permissions.py"],
    args = ["tests/unit/cmk/gui/test_permissions.py"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        ":conftest",
        "//cmk/gui:permissions",
        "//packages/cmk-ccc:plugin-registry",
        "//tests/unit:conftest",
        requirement("pytest"),
    ],
)

py_test(
    name = "session",
    srcs = ["test_session.py"],
    args = ["tests/unit/cmk/gui/test_session.py"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        ":conftest",
        "//cmk/gui:logged_in",
        "//cmk/gui:session",
        "//tests/unit:conftest",
        requirement("flask"),
        requirement("pytest"),
        requirement("pytest-mock"),
    ],
)

py_test(
    name = "sites",
    srcs = ["test_sites.py"],
    args = ["tests/unit/cmk/gui/test_sites.py"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        ":conftest",
        "//cmk/gui:sites",
        "//cmk/gui:user_sites",
        "//cmk/utils",
        "//packages/cmk-ccc:site",
        "//packages/cmk-livestatus-client",
        "//tests/unit:conftest",
        requirement("pytest"),
    ],
)

py_test(
    name = "table",
    srcs = ["test_table.py"],
    args = ["tests/unit/cmk/gui/test_table.py"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        ":compare_html",
        ":conftest",
        "//cmk/gui:http",
        "//cmk/gui:logged_in",
        "//cmk/gui:table",
        "//cmk/gui/htmllib:html",
        "//cmk/gui/utils:html",
        "//cmk/gui/utils:output_funnel",
        "//tests/unit:conftest",
        requirement("beautifulsoup4"),
        requirement("pytest"),
    ],
)

py_test(
    name = "threading",
    srcs = ["test_threading.py"],
    args = ["tests/unit/cmk/gui/test_threading.py"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        ":conftest",
        "//cmk/gui:config",
        "//cmk/gui/utils:request_context",
        "//tests/unit:conftest",
        requirement("flask"),
        requirement("pytest"),
    ],
)

py_test(
    name = "valuespec",
    srcs = ["test_valuespec.py"],
    args = ["tests/unit/cmk/gui/test_valuespec.py"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        ":conftest",
        "//cmk/gui:config",
        "//cmk/gui:exceptions",
        "//cmk/gui:http",
        "//cmk/gui/valuespec",
        "//tests/unit:conftest",
        requirement("pytest"),
        requirement("time-machine"),
    ],
)

py_test(
    name = "view_utils",
    srcs = ["test_view_utils.py"],
    args = ["tests/unit/cmk/gui/test_view_utils.py"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        ":conftest",
        "//cmk/gui:http",
        "//cmk/gui:view_utils",
        "//cmk/gui/utils:html",
        "//tests/unit:conftest",
        requirement("pytest"),
    ],
)

py_test(
    name = "visuals_tests",
    srcs = ["test_visuals.py"],
    args = ["tests/unit/cmk/gui/test_visuals.py"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        ":conftest",
        "//cmk/gui:http",
        "//cmk/gui:type_defs",
        "//cmk/gui/visuals",
        "//tests/unit:conftest",
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
