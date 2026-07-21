load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@bazel_skylib//rules:build_test.bzl", "build_test")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//bazel/rules:package_wheel.bzl", "package_wheel")
load("//bazel/rules:py_cmk_package.bzl", "py_cmk_package")
load("//bazel/rules:py_requirements_test.bzl", "py_requirements_test")

exports_files(["requirements.in"])

py_library(
    name = "cmkpasswd",
    srcs = glob(["cmkpasswd/**/*.py"]),
    imports = [".."],
    visibility = ["//:__subpackages__"],
    deps = [
        "//cmk/gui/utils:htpasswd",
        "//cmk/utils:paths",
        "//packages/cmk-ccc:user",
        "//packages/cmk-ccc:version",
        "//packages/cmk-crypto",
    ],
)

py_library(
    name = "message_broker_certs",
    srcs = ["message_broker_certs.py"],
    imports = [".."],
    visibility = ["//:__subpackages__"],
    deps = [
        "//cmk/utils",
        "//packages/cmk-messaging",
    ],
)

py_library(
    name = "validate_config",
    srcs = ["validate_config.py"],
    imports = [".."],
    tags = [
        "deballast-keep=//cmk/gui:app",  # GUI plugin tree loaded at runtime to populate the config/ruleset registries
        "deballast-keep=//cmk/gui/form_specs:form_specs",  # form specs registered at runtime with the GUI plugin tree
        "deballast-keep=//cmk/gui/watolib:registries",  # registries populated at runtime with the GUI plugin tree
    ],
    visibility = ["//:__subpackages__"],
    deps = [
        "//cmk/gui:app",
        "//cmk/gui:core_toolkit",
        "//cmk/gui/form_specs",
        "//cmk/gui/watolib",
        "//cmk/gui/watolib:config_infra",
        "//cmk/gui/watolib:registries",
        "//cmk/gui/watolib:timeperiods",
        "//cmk/utils",
        "//packages/cmk-ccc:tty",
        requirement("pydantic"),
    ],
)

py_library(
    name = "validate_plugins",
    srcs = ["validate_plugins.py"],
    imports = [".."],
    visibility = ["//:__subpackages__"],
    deps = [
        "//cmk/base:config",
        "//cmk/gui:app",
        "//cmk/gui/rule_specs:types",
        "//cmk/gui/watolib",
        "//cmk/gui/watolib:registries",
        "//cmk/server_side_calls_backend",
        "//cmk/utils",
        "//packages/cmk-ccc:debug",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-check-engine:specs",
        "//packages/cmk-check-engine/cmk/checkengine/plugin_backend",
        "//packages/cmk-check-engine/cmk/checkengine/plugins",
        "//packages/cmk-plugin-apis:agent_based",
        "//packages/cmk-plugin-apis:discover_plugins",
        "//packages/cmk-plugin-apis:rulesets",
        "//packages/cmk-wsgi",
    ],
)

py_cmk_package(
    name = "whl_contents",
    # The monolithic cmk wheel bundles only files from the //cmk/ tree. Everything under
    # //packages/cmk-* and //non-free/packages/cmk-* ships in its own wheel that is deployed
    # separately via //omd:edition_deps, so it must be filtered out here to avoid shipping
    # it twice.
    include_roots = ["cmk"],
    deps = select({
        "@cmk//edition:cloud": ["//cmk/editions/nonfree:cloud"],
        "@cmk//edition:community": ["//cmk/editions:community"],
        "@cmk//edition:pro": ["//cmk/editions/nonfree:pro"],
        "@cmk//edition:ultimate": ["//cmk/editions/nonfree:ultimate"],
        "@cmk//edition:ultimatemt": ["//cmk/editions/nonfree:ultimatemt"],
    }),
)

py_wheel(
    name = "whl",
    distribution = "checkmk",
    entry_points = {"console_scripts": [
        "cmk-automation-client = cmk.automations.client:main",
        "cmk-automation-helper = cmk.base.automation_helper:main",
        "cmk-cert = cmk.gui.cmkcert.main:main",
        "cmk-config-anonymizer = cmk.config_anonymizer.main:main",
        "cmk-convert-rrds = cmk.rrd.convert_rrds.__main__:main",
        "cmk-passwd = cmk.cmkpasswd.main:main",
        "cmk-product-usage = cmk.product_usage.cli:main",
        "cmk-pwstore = cmk.utils.password_store.cli:main",
        "cmk-ui-job-scheduler = cmk.gui.job_scheduler.main:main",
        "cmk-validate-plugins = cmk.validate_plugins:main",
        "init-redis = cmk.gui.search.index:main",
        "message-broker-certs = cmk.message_broker_certs:main",
    ]},
    requires = [
        # alphabetical order
        "apispec",
        "apispec-oneofschema",
        "bcrypt",
        "cryptography",
        "docstring-parser",
        "fastapi",
        "feedparser",
        "fido2",
        "flask",
        "google-api-python-client",
        "google-auth",
        "google-cloud-asset",
        "google-cloud-monitoring",
        "icalendar",
        "jinja2",
        "jira",
        "lxml",
        "markdown",
        "marshmallow",
        "marshmallow-oneofschema",
        "meraki",
        "msal",
        "numpy",
        "oauthlib",
        "openapi-spec-validator",
        "opentelemetry-api",
        "opentelemetry-exporter-otlp",
        "opentelemetry-instrumentation-fastapi",
        "opentelemetry-instrumentation-redis",
        "opentelemetry-instrumentation-requests",
        "opentelemetry-instrumentation-wsgi",
        "opentelemetry-sdk",
        "opentelemetry-semantic-conventions",
        "paho-mqtt",
        "paramiko",
        "pillow",
        "pika",
        "protobuf",
        "psutil",
        "psycopg2-binary",  # missing wheel
        "pyasn1",
        "pydantic",
        "pydantic_core",
        "pyjwt",
        "pymongo",
        "pymssql",
        "pymysql",
        "pyopenssl",
        "pyparsing",
        "pypdf",
        "pysaml2",
        "pysmb",
        "pysmi",
        "python-active-directory",  # missing wheel
        "python-dateutil",
        "python-ldap",  # missing wheel
        "python-multipart",
        "python-snap7",
        "pyyaml",
        "recurring_ical_events",
        "redis",
        "reportlab",
        "requests",
        "requests-oauthlib",
        "robotframework",
        "roman",
        # "rrdtool",
        "setproctitle",
        "setuptools",
        "setuptools-scm",
        "urllib3",
        "uvicorn",
        "watchdog",
        "werkzeug",
    ],
    # TODO(ml): cmk_version vs. PEP 440?
    version = "1+" + select({
        "@cmk//edition:cloud": "cloud",
        "@cmk//edition:community": "community",
        "@cmk//edition:pro": "pro",
        "@cmk//edition:ultimate": "ultimate",
        "@cmk//edition:ultimatemt": "ultimatemt",
    }),
    visibility = ["//visibility:public"],
    deps = [":whl_contents"],
)

build_test(
    name = "build_test",
    targets = ["whl"],
)

package_wheel(
    name = "cmk_tar",
    visibility = ["//visibility:public"],
    whl = "whl",
)

sh_library(
    name = "f12",
    srcs = [
        ".f12",
    ],
)

py_requirements_test(
    name = "requirements-test",
    known_undeclared = [
        "tinkerforge",  # cmk/plugins/tinkerforge/special_agent/agent_tinkerforge.py
        "ibm-db",  # cmk/plugins/sql/active_check/check_sql.py
        "ibm-db-dbi",  # cmk/plugins/sql/active_check/check_sql.py
        "sqlanydb",  # cmk/plugins/sql/active_check/check_sql.py
        "rados",  # cmk/plugins/ceph/agents/mk_ceph.py
        "mysqldb",  # cmk/plugins/plesk/agents/plesk_backups.py
        "pymongo",  # cmk/plugins/mongodb/agents/mk_mongodb.py
        "bson",  # cmk/plugins/mongodb/agents/mk_mongodb.py
        "pyrfc",  # cmk/plugins/sap/agents/mk_sap.py
        "rrdtool",  # is built as part of the project
        "git",  # cmk/utils/werks/mail/__init__.py, dev-only werks tooling
    ],
    known_unused = [
        "setuptools",  # pinned transitive dependency
        "setuptools-scm",
        "pysmi",  # used outside of cmk/ in omd/packages/net-snmp/compile_mibs.py
        "openapi-spec-validator",  # only imported by tests
    ],
    libs = [
        # cloud and ultimatemt each transitively pull in ultimate -> pro -> community,
        # so together they cover every edition's library code.
        "//cmk/editions/nonfree:cloud",
        "//cmk/editions/nonfree:ultimatemt",
        "//cmk/gui/openapi/spec/editions/community:generate_api_spec",
        "//cmk/gui/openapi/spec/editions/nonfree/pro:generate_api_spec",
        "//cmk/gui/openapi/spec/editions/nonfree/ultimate:generate_api_spec",
        "//cmk/gui/openapi/spec/editions/nonfree/cloud:generate_api_spec",
        "//cmk/gui/openapi/spec/editions/nonfree/ultimatemt:generate_api_spec",
        "//cmk/gui/openapi/spec/spec_generator:merge_api_specs",
        "//cmk/post_rename_site:post-rename-site",
        "//cmk/update_config:cmk-update-config",
        "//cmk/utils:werks_bin",
    ],
    requirements_in = "requirements.in",
    target_compatible_with = select({
        "@cmk//edition:community": ["@platforms//:incompatible"],
        "//conditions:default": [],
    }),
)
