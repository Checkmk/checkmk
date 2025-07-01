load("@aspect_rules_py//py:defs.bzl", "py_library", "py_pytest_main")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//:bazel_variables.bzl", "edition_python_deps")
load("//bazel/rules:doctest.bzl", "py_doc_test")

exports_files(["requirements.in"])

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
    "kubernetes",
    "lxml",
    "markdown",
    "marshmallow",
    "marshmallow-oneofschema",
    "meraki",
    "msal",
    "mypy-boto3-logs",
    "netapp-ontap",  # provided elsewhere
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
    "pysmi-lextudio",
    "pysnmp-lextudio",
    "python-active-directory",  # missing wheel
    "python-dateutil",
    "python-ldap",  # missing wheel
    "python-multipart",
    "python-snap7",
    "pyyaml",
    "recurring_ical_events",
    "redfish",
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
    "snmpsim-lextudio",
    "tenacity",
    "urllib3",
    "uvicorn",
    "vcrpy",
    "watchdog",
    "werkzeug",
]

CRE_PY = glob(
    [
        "**/cre/**/*.py",
        "**/cre.py",
        "**/raw/**/*.py",
        "**/raw.py",
    ],
    allow_empty = True,
)

CCE_PY = glob(
    [
        "**/cce/**/*.py",
        "**/cce.py",
    ],
    allow_empty = True,
)

CEE_PY = glob(
    [
        "**/cee/**/*.py",
        "**/cee.py",
    ],
    allow_empty = True,
)

CME_PY = glob(
    [
        "**/cme/**/*.py",
        "**/cme.py",
    ],
    allow_empty = True,
)

CSE_PY = glob(
    [
        "**/cse/**/*.py",
        "**/cse.py",
    ],
    allow_empty = True,
)

CMK_PACKAGES = [
    "//packages/cmk-shared-typing:cmk_shared_typing_py",
    "//packages/cmk-agent-receiver",
    "//packages/cmk-ccc:cleanup",
    "//packages/cmk-ccc:cpu-tracking",
    "//packages/cmk-ccc:crash-reporting",
    "//packages/cmk-ccc:daemon",
    "//packages/cmk-ccc:debug",
    "//packages/cmk-ccc:exceptions",
    "//packages/cmk-ccc:hostaddress",
    "//packages/cmk-ccc:i18n",
    "//packages/cmk-ccc:plugin-registry",
    "//packages/cmk-ccc:profile",
    "//packages/cmk-ccc:resulttype",
    "//packages/cmk-ccc:site",
    "//packages/cmk-ccc:store",
    "//packages/cmk-ccc:tty",
    "//packages/cmk-ccc:user",
    "//packages/cmk-ccc:validatedstr",
    "//packages/cmk-ccc:version",
    "//packages/cmk-crypto",
    "//packages/cmk-events",
    "//packages/cmk-livestatus-client",
    "//packages/cmk-livestatus-client:py_livestatus",
    "//packages/cmk-messaging",
    "//packages/cmk-mkp-tool",
    "//packages/cmk-plugin-apis:agent_based",
    "//packages/cmk-plugin-apis:graphing",
    "//packages/cmk-plugin-apis:rulesets",
    "//packages/cmk-plugin-apis:server_side_calls",
    "//packages/cmk-trace",
    "//packages/cmk-werks",
] + select({
    "@//:gpl_repo": [],
    "@//:gpl+enterprise_repo": [
        "//non-free/packages/cmk-mknotifyd",
        "//non-free/packages/cmk-otel-collector",
    ],
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
        exclude = CRE_PY + CCE_PY + CEE_PY + CME_PY + CSE_PY,
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
    name = "lib_cmk_cre",
    srcs = CRE_PY,
    imports = [".."],
    visibility = ["//tests:__subpackages__"],
    deps = [
        "lib_cmk",
    ],
)

[py_library(
    name = "lib_cmk_" + edition,
    srcs = srcs,
    imports = [".."],
    visibility = ["//tests:__subpackages__"],
    deps = CMC_PROTO_DEPS + [
        "lib_cmk",
    ] + edition_python_deps[edition],
) for edition, srcs in [
    ("cce", CCE_PY),
    ("cee", CEE_PY),
    ("cme", CME_PY),
    ("cse", CSE_PY),
]]

py_library(
    # HACK to avoid Source file found twice under different module names: "meraki" and "meraki.__init__"
    name = "lib_cmk_repo_no_meraki",
    srcs = glob(
        include = ["**/*.py"],
        exclude = ["plugins/cisco_meraki/special_agent/agent_cisco_meraki.py"],
    ),
    data = ["gui/wsgi/applications/index.wsgi"],
    imports = [".."],
    visibility = ["//tests/unit:__pkg__"],
    deps = [
        "//agents/plugins:mk_jolokia",
    ] + select({
        "@//:gpl_repo": [],
        "@//:gpl+enterprise_repo": CMC_PROTO_DEPS,
    }) + CMK_PACKAGES + [requirement(dep) for dep in REQUIRED_EXTERNAL_DEPS if dep != "meraki"],
)

py_library(
    # The repo edition is only used for testing.
    name = "lib_cmk_repo",
    srcs = glob(["**/*.py"]),
    data = ["gui/wsgi/applications/index.wsgi"],
    imports = [".."],
    visibility = ["//tests/unit:__pkg__"],
    deps = [
        "//agents/plugins:mk_jolokia",
    ] + select({
        "@//:gpl_repo": [],
        "@//:gpl+enterprise_repo": CMC_PROTO_DEPS,
    }) + CMK_PACKAGES + [requirement(dep) for dep in REQUIRED_EXTERNAL_DEPS],
)

py_wheel(
    name = "cmk_cre",
    distribution = "checkmk",
    requires = REQUIRED_EXTERNAL_DEPS,
    # TODO(ml): cmk_version vs. PEP 440?
    version = "1+cre",
    visibility = ["//visibility:public"],
    deps = [
        "lib_cmk",
        "lib_cmk_cre",
    ],
)

[py_wheel(
    name = "cmk_" + edition,
    distribution = "checkmk",
    requires = REQUIRED_EXTERNAL_DEPS,
    # TODO(ml): cmk_version vs. PEP 440?
    version = "1+" + edition,
    visibility = ["//visibility:public"],
    deps = CMC_PROTO_DEPS + [
        "lib_cmk",
        "lib_cmk_" + edition,
    ],
) for edition in [
    "cce",
    "cee",
    "cme",
    "cse",
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
)
