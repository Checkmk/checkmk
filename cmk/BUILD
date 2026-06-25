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
        "GitPython",
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
        "pyprof2calltree",
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

_KNOWN_UNDECLARED = [
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
]

_KNOWN_UNUSED = [
    "setuptools",  # pinned transitive dependency
    "setuptools-scm",
    "pysmi",  # used outside of cmk/ in omd/packages/net-snmp/compile_mibs.py
    "apispec-oneofschema",  # only imported by build-time spec generator
    "openapi-spec-validator",  # only imported by tests
]

py_requirements_test(
    name = "requirements-test-community",
    known_undeclared = _KNOWN_UNDECLARED,
    known_unused = _KNOWN_UNUSED + [
        # only imported in non-free editions
        "numpy",
        "protobuf",
        "pyjwt",
        "pypdf",
        "pysaml2",
        "roman",
    ],
    libs = ["//cmk/editions:community"],
    requirements_in = "requirements.in",
    target_compatible_with = select({
        "@cmk//edition:community": [],
        "//conditions:default": ["@platforms//:incompatible"],
    }),
)

py_requirements_test(
    name = "requirements-test-pro",
    known_undeclared = _KNOWN_UNDECLARED,
    known_unused = _KNOWN_UNUSED + [
        # only imported in cloud edition
        "pyjwt",
    ],
    libs = ["//cmk/editions/nonfree:pro"],
    requirements_in = "requirements.in",
    target_compatible_with = select({
        "@cmk//edition:pro": [],
        "//conditions:default": ["@platforms//:incompatible"],
    }),
)

py_requirements_test(
    name = "requirements-test-ultimate",
    known_undeclared = _KNOWN_UNDECLARED,
    known_unused = _KNOWN_UNUSED + [
        # only imported in cloud edition
        "pyjwt",
    ],
    libs = ["//cmk/editions/nonfree:ultimate"],
    requirements_in = "requirements.in",
    target_compatible_with = select({
        "@cmk//edition:ultimate": [],
        "//conditions:default": ["@platforms//:incompatible"],
    }),
)

py_requirements_test(
    name = "requirements-test-cloud",
    known_undeclared = _KNOWN_UNDECLARED,
    known_unused = _KNOWN_UNUSED,
    libs = ["//cmk/editions/nonfree:cloud"],
    requirements_in = "requirements.in",
    target_compatible_with = select({
        "@cmk//edition:cloud": [],
        "//conditions:default": ["@platforms//:incompatible"],
    }),
)

py_requirements_test(
    name = "requirements-test-ultimatemt",
    known_undeclared = _KNOWN_UNDECLARED,
    known_unused = _KNOWN_UNUSED + [
        # only imported in cloud edition
        "pyjwt",
    ],
    libs = ["//cmk/editions/nonfree:ultimatemt"],
    requirements_in = "requirements.in",
    target_compatible_with = select({
        "@cmk//edition:ultimatemt": [],
        "//conditions:default": ["@platforms//:incompatible"],
    }),
)
