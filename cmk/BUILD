load("@aspect_rules_py//py:defs.bzl", "py_library", "py_pytest_main")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@com_google_protobuf//:protobuf_version.bzl", "PROTOBUF_PYTHON_VERSION")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//:bazel_variables.bzl", "edition_deps")
load("//bazel/rules:doctest.bzl", "py_doc_test")

genrule(
    name = "_prune_requirements_in",
    srcs = ["//cmk:requirements.txt"],
    outs = ["requirements_pruned.txt"],
    cmd = "cat $< | grep -v -e ^rrdtool > $@",
)

genrule(
    name = "_pin_protobuf_requirement",
    srcs = [":requirements_pruned.txt"],
    outs = ["requirements_protobuf_pinned.txt"],
    # We go for "compatible release" with `~=`.
    cmd = "cat $< <(echo protobuf~=%s) > $@" % PROTOBUF_PYTHON_VERSION,
    visibility = ["//:__subpackages__"],
)

REQUIRED_EXTERNAL_DEPS = [
    # alphabetical order
    "annotated-types",
    "apispec",
    "apispec-oneofschema",
    "azure-identity",
    "azure-storage-blob",
    "boto3",
    "botocore",
    "cryptography",
    "cython",
    "docstring-parser",
    "exchangelib",  # missing wheel
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
    "marshmallow",
    "marshmallow-oneofschema",
    "meraki",
    "msal",
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
    "ply",
    # "protobuf",  # provided elsewhere
    "psutil",
    "psycopg2-binary",  # missing wheel
    "pyasn1",
    "pydantic",
    "pydantic_core",
    "pyghmi",
    "pyjwt",
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
    "setproctitle",
    "setuptools-scm",
    "snmpsim-lextudio",
    "urllib3",
    "vcrpy",
    "watchdog",
]

CRE_PY = glob([
    "**/cre/**/*.py",
    "**/cre.py",
    "**/raw/**/*.py",
    "**/raw.py",
])

CCE_PY = glob([
    "**/cce/**/*.py",
    "**/cce.py",
])

CEE_PY = glob([
    "**/cee/**/*.py",
    "**/cee.py",
])

CME_PY = glob([
    "**/cme/**/*.py",
    "**/cme.py",
])

CSE_PY = glob([
    "**/cse/**/*.py",
    "**/cse.py",
])

CMK_PACKAGES = [
    "//packages/cmk-agent-based",
    "//packages/cmk-agent-receiver",
    "//packages/cmk-ccc",
    "//packages/cmk-crypto",
    "//packages/cmk-events",
    "//packages/cmk-graphing",
    "//packages/cmk-livestatus-client",
    "//packages/cmk-livestatus-client:py_livestatus",
    "//packages/cmk-messaging",
    "//packages/cmk-mkp-tool",
    "//packages/cmk-rulesets",
    "//packages/cmk-server-side-calls",
    "//packages/cmk-trace",
    "//packages/cmk-werks",
] + select({
    "@//:gpl_repo": [],
    "@//:gpl+enterprise_repo": [
        "//non-free/packages/cmk-mknotifyd",
        "//non-free/packages/cmk-otel-collector",
    ],
})

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
    deps = [
        # TODO: Shouldn't we add "cycletime_" and "state_" here?
        "//non-free/packages/cmc-protocols:config_proto_pb2",
        "lib_cmk",
    ] + edition_deps[edition],
) for edition, srcs in [
    ("cce", CCE_PY),
    ("cee", CEE_PY),
    ("cme", CME_PY),
    ("cse", CSE_PY),
]]

py_library(
    # The repo edition is only used for testing.
    name = "lib_cmk_repo",
    srcs = glob(["**/*.py"]),
    data = ["gui/wsgi/applications/index.wsgi"],
    imports = [".."],
    visibility = ["//tests/unit:__pkg__"],
    deps = [
        "//agents/plugins:mk_jolokia",
        "@rrdtool_native//:rrdtool_python_lib",
    ] + select({
        "@//:gpl_repo": [],
        "@//:gpl+enterprise_repo": [
            "//non-free/packages/cmc-protocols:config_proto_pb2",
            "//non-free/packages/cmc-protocols:cycletime_proto_pb2",
            "//non-free/packages/cmc-protocols:state_proto_pb2",
        ],
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
    deps = [
        "lib_cmk",
        "lib_cmk_" + edition,
        "//non-free/packages/cmc-protocols:config_proto_pb2",
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
