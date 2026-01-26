load("@aspect_rules_py//py:defs.bzl", "py_binary", "py_library", "py_pytest_main")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_pkg//pkg:mappings.bzl", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//:bazel_variables.bzl", "edition_python_deps")
load("//bazel/rules:doctest.bzl", "py_doc_test")
load("//bazel/rules:package_wheel.bzl", "package_wheel")
load("do_not_deploy.bzl", "DO_NOT_DEPLOY")

# To update the list run the following command:
# echo "LEGACY_CHECKS = [" > legacy_checks_list.bzl;for F in $(ls *.py); do echo $F | sed 's/\(.*\)\.py/    "\1",/' >> legacy_checks_list.bzl; done; echo "]" >> legacy_checks_list.bzl
load("legacy_checks_list.bzl", "LEGACY_CHECKS")

LEGACY_CHECKS_DICT = {"base/legacy_checks/" + name + ".py": name for name in LEGACY_CHECKS}

exports_files([
    "requirements.in",
    "utils/password_store/cli.py",
    "gui/openapi/spec/spec_generator/generate_api_spec.py",
    "product_telemetry/cmk_telemetry_cli.py",
] + LEGACY_CHECKS_DICT.keys())

REQUIRED_EXTERNAL_DEPS = [
    # alphabetical order
    "apispec",
    "apispec-oneofschema",
    "azure-identity",
    "azure-storage-blob",
    "bcrypt",
    "boto3",
    "botocore",
    "cryptography",
    "docstring-parser",
    "exchangelib",  # missing wheel
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
    "mypy-boto3-logs",
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
    "opsgenie-sdk",
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
    "pyghmi",
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
    "pysnmp",
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
    "simplejson",
    "snmpsim",
    "tenacity",
    "urllib3",
    "uvicorn",
    "vcrpy",
    "watchdog",
    "werkzeug",
]

COMMUNITY_PY = glob(
    include = [
        "**/community/**/*.py",
    ],
    allow_empty = True,
    exclude = DO_NOT_DEPLOY + ["**/nonfree/**"],
)

ULTIMATE_PY = glob(
    include = [
        "**/ultimate/**/*.py",
        "**/nonfree/**/*.py",
    ],
    allow_empty = True,
    exclude = DO_NOT_DEPLOY + [
        # ultimate includes pro, but not cloud or ultimatemt
        "**/nonfree/**/cloud/**",
        "**/nonfree/**/ultimatemt/**",
    ],
)

PRO_PY = glob(
    [
        "**/pro/**/*.py",
        "**/nonfree/**/*.py",
    ],
    allow_empty = True,
    exclude = DO_NOT_DEPLOY + [
        # pro doesn't include any other enterprise edition
        "**/nonfree/**/cloud/**",
        "**/nonfree/**/ultimate/**",
        "**/nonfree/**/ultimatemt/**",
    ],
)

ULTIMATEMT_PY = glob(
    [
        "**/ultimatemt/**/*.py",
        "**/nonfree/**/*.py",
    ],
    allow_empty = True,
    exclude = DO_NOT_DEPLOY + [
        # ultimate includes pro and ultimate but not cloud
        "**/nonfree/**/cloud/**",
    ],
)

CLOUD_PY = glob(
    [
        "**/cloud/**/*.py",
        "**/nonfree/**/*.py",
    ],
    allow_empty = True,
    exclude = DO_NOT_DEPLOY + [
        # cloud includes pro and ultimate but not ultimatemt
        "**/nonfree/**/ultimatemt/**",
    ],
)

filegroup(
    name = "checkman",
    srcs = glob(
        [
            "**/checkman/**",
        ],
        exclude = ["**/OWNERS"],
    ),
)

filegroup(
    name = "libexec",
    srcs = glob(
        [
            "**/libexec/*",
        ],
    ),
    visibility = ["//omd:__subpackages__"],
)

filegroup(
    name = "miscellaneous",
    srcs = [
        "gui/wsgi/applications/index.wsgi",
        "utils/werks/announce/templates/announce.md.jinja2",
        "utils/werks/announce/templates/announce.txt.jinja2",
    ],
)

filegroup(
    name = "agents",
    srcs = glob(
        [
            "plugins/**/agents/*",
        ],
    ),
)

CMK_PACKAGES = [
    "//packages/cmk-shared-typing:cmk_shared_typing_py",
    "//packages/cmk-agent-receiver",
    "//packages/cmk-ccc:cleanup",
    "//packages/cmk-ccc:config-path",
    "//packages/cmk-ccc:cpu-tracking",
    "//packages/cmk-ccc:crash-reporting",
    "//packages/cmk-ccc:daemon",
    "//packages/cmk-ccc:debug",
    "//packages/cmk-ccc:exceptions",
    "//packages/cmk-ccc:hostaddress",
    "//packages/cmk-ccc:i18n",
    "//packages/cmk-ccc:observer",
    "//packages/cmk-ccc:plugin-registry",
    "//packages/cmk-ccc:profile",
    "//packages/cmk-ccc:regex",
    "//packages/cmk-ccc:resulttype",
    "//packages/cmk-ccc:site",
    "//packages/cmk-ccc:store",
    "//packages/cmk-ccc:timeout",
    "//packages/cmk-ccc:translations",
    "//packages/cmk-ccc:tty",
    "//packages/cmk-ccc:user",
    "//packages/cmk-ccc:archive",
    "//packages/cmk-ccc:version",
    "//packages/cmk-check-engine:fetchers",
    "//packages/cmk-check-engine:helper-interface",
    "//packages/cmk-check-engine:snmplib",
    "//packages/cmk-crypto",
    "//packages/cmk-ec",
    "//packages/cmk-events",
    "//packages/cmk-livestatus-client",
    "//packages/cmk-livestatus-client:py_livestatus",
    "//packages/cmk-messaging",
    "//packages/cmk-mkp-tool",
    "//packages/cmk-plugins:lib",
    "//packages/cmk-plugin-apis:agent_based",
    "//packages/cmk-plugin-apis:bakery",
    "//packages/cmk-plugin-apis:graphing",
    "//packages/cmk-plugin-apis:inventory_ui",
    "//packages/cmk-plugin-apis:rulesets",
    "//packages/cmk-plugin-apis:password_store",
    "//packages/cmk-plugin-apis:server_side_calls",
    "//packages/cmk-plugin-apis:server_side_programs",
    "//packages/cmk-trace",
    "//packages/cmk-werks",
] + select({
    "@//:gpl+nonfree_repo": [
        "//non-free/packages/cmk-core-helpers:check-helper-protocol",
        "//non-free/packages/cmk-core-helpers:fetcher-helper",
        "//non-free/packages/cmk-core-helpers:inline-snmp",
        "//non-free/packages/cmk-metric-backend",
        "//non-free/packages/cmk-mknotifyd",
        "//non-free/packages/cmk-otel-collector",
    ],
    "@//:gpl_repo": [],
})

CMC_PROTO_DEPS = [
    "//non-free/packages/cmc-protocols:py_config_proto",
    "//non-free/packages/cmc-protocols:py_cycletime_proto",
    "//non-free/packages/cmc-protocols:py_state_proto",
]

py_library(
    name = "lib_cmk",
    srcs = glob(
        # Keep in sync with `REPO_PATCH_RULES` from `versioning.groovy`.
        include = ["**/*.py"],
        exclude = (
            ["plugins/**/agents/*"] +
            COMMUNITY_PY +
            ULTIMATE_PY +
            PRO_PY +
            ULTIMATEMT_PY +
            CLOUD_PY +
            DO_NOT_DEPLOY + [
                "base/legacy_checks/*",
                "**/nonfree/**",
            ]
        ),
    ),
    data = ["gui/wsgi/applications/index.wsgi"],
    imports = [".."],
    visibility = [
        # for conftest
        "//tests:__subpackages__",
    ],
    deps = [
        "@rrdtool_native//:rrdtool_python_lib",
        # `cmk.special_agent.agent_jolokia` imports `mk_jolokia`
        "//agents/plugins:mk_jolokia",
    ] + CMK_PACKAGES + [requirement(dep) for dep in REQUIRED_EXTERNAL_DEPS],
)

py_library(
    name = "lib_cmk_community",
    srcs = COMMUNITY_PY,
    imports = [".."],
    visibility = [
        "//tests:__subpackages__",
        # for api spec
        "//omd:__subpackages__",
    ],
    deps = [
        "lib_cmk",
    ],
)

[py_library(
    name = "lib_cmk_" + edition,
    srcs = srcs,
    imports = [".."],
    visibility = ["//tests:__subpackages__"],
    deps = select({
        "@//:gpl+nonfree_repo": CMC_PROTO_DEPS,
        "@//:gpl_repo": [],
    }) + [
        "lib_cmk",
    ] + edition_python_deps[edition] + [requirement(dep) for dep in REQUIRED_EXTERNAL_DEPS],
) for edition, srcs in [
    ("ultimate", ULTIMATE_PY),
    ("pro", PRO_PY),
    ("ultimatemt", ULTIMATEMT_PY),
    ("cloud", CLOUD_PY),
]]

py_library(
    # The repo edition is only used for testing and generating the plugin-api doc with sphinx.
    name = "lib_cmk_repo",
    srcs = glob(["**/*.py"]),
    data = ["gui/wsgi/applications/index.wsgi"],
    imports = [".."],
    tags = ["lint-with-astrein"],
    visibility = [
        "//doc/plugin-api:__pkg__",
        "//tests/unit:__pkg__",
    ],
    deps = [
        "//agents/plugins:mk_jolokia",
    ] + select({
        "@//:gpl+nonfree_repo": CMC_PROTO_DEPS,
        "@//:gpl_repo": [],
    }) + CMK_PACKAGES + [requirement(dep) for dep in REQUIRED_EXTERNAL_DEPS],
)

py_wheel(
    name = "cmk_community",
    distribution = "checkmk",
    requires = REQUIRED_EXTERNAL_DEPS,
    # TODO(ml): cmk_version vs. PEP 440?
    version = "1+community",
    visibility = ["//visibility:public"],
    deps = [
        "lib_cmk",
        "lib_cmk_community",
        ":agents",
        ":checkman",
        ":miscellaneous",
    ],
)

[py_wheel(
    name = "cmk_" + edition,
    distribution = "checkmk",
    requires = REQUIRED_EXTERNAL_DEPS,
    # TODO(ml): cmk_version vs. PEP 440?
    version = "1+" + edition,
    visibility = ["//visibility:public"],
    deps = select({
        "@//:gpl+nonfree_repo": CMC_PROTO_DEPS,
        "@//:gpl_repo": [],
    }) + [
        "lib_cmk",
        ":agents",
        ":checkman",
        ":libexec",
        ":miscellaneous",
        "lib_cmk_" + edition,
    ],
) for edition in [
    "ultimate",
    "pro",
    "ultimatemt",
    "cloud",
]]

[package_wheel(
    name = "cmk_tar_" + edition,
    prefix = "lib/python3",
    visibility = ["//visibility:public"],
    whl = "cmk_" + edition,
) for edition in [
    "community",
    "ultimate",
    "pro",
    "ultimatemt",
    "cloud",
]]

py_pytest_main(
    name = "__test__",
    deps = [
        requirement("pytest"),
        # pytest-xdist for `--numprocesses=NPROC`
        requirement("pytest-xdist"),
    ],
)

py_doc_test(
    name = "doctest",
    srcs = [
        "//cmk:lib_cmk_repo",
    ],
    env = {
        "PYTHONWARNINGS": "ignore",
    },
    tags = ["no-mypy"],
)

py_binary(
    name = "generate_api_spec",
    srcs = ["gui/openapi/spec/spec_generator/generate_api_spec.py"],
    main = "gui/openapi/spec/spec_generator/generate_api_spec.py",
    visibility = [
        "//omd:__subpackages__",
        "//packages/cmk-shared-typing:__subpackages__",
    ],
    deps = [
        "lib_cmk_repo",
        requirement("pyyaml"),
    ],
)

pkg_files(
    name = "legacy_checks_pkg",
    srcs = LEGACY_CHECKS_DICT.keys(),
    prefix = "share/check_mk/checks",
    renames = LEGACY_CHECKS_DICT,
)

pkg_tar(
    name = "legacy_checks",
    srcs = ["legacy_checks_pkg"],
    stamp = 1,
    visibility = ["//omd:__pkg__"],
)
