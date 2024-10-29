load("@aspect_rules_py//py:defs.bzl", "py_library", "py_pytest_main", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@com_google_protobuf//:protobuf_version.bzl", "PROTOBUF_PYTHON_VERSION")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("@rules_python//python:proto.bzl", "py_proto_library")

genrule(
    name = "_generate_requirements_in",
    srcs = [
        "@//:Pipfile",
        "@//:Pipfile.lock",
    ],
    outs = ["requirements_in.orig"],
    # We need to filter out editable reqs are the relative paths are not
    # accessible in the sandbox.  Failing to do so raises an `InstallationError`.
    cmd = "pipenv requirements --dev | grep -Ev '^\\-e[[:space:]]' > $@",
)

FILTER_OUT = [
    # Provided elsewhere
    "rrdtool",
]

genrule(
    name = "_prune_requirements_in",
    srcs = ["requirements_in.orig"],
    outs = ["requirements_pruned.txt"],
    cmd = "cat $< | grep -v " + " ".join([("-e ^%s==" % pkg) for pkg in FILTER_OUT]) + " > $@",
)

genrule(
    name = "_pin_protobuf_requirement",
    srcs = ["requirements_pruned.txt"],
    outs = ["requirements.txt"],
    # We go for "compatible release" with `~=`.
    cmd = "cat $< <(echo protobuf~=%s) > $@" % PROTOBUF_PYTHON_VERSION,
    visibility = ["//:__pkg__"],
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
    "dicttoxml",
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
    "requests-kerberos",  # krb5: missing wheel
    "requests-oauthlib",
    "robotframework",
    "roman",
    "setproctitle",
    "setuptools-scm",
    "six",
    "snmpsim-lextudio",
    "typing-extensions",
    "urllib3",
    "vcrpy",
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
    "//packages/cmk-crypto",
    "//packages/cmk-graphing",
    "//packages/cmk-livestatus-client",
    "//packages/cmk-livestatus-client:py_livestatus",
    "//packages/cmk-messaging",
    "//packages/cmk-mkp-tool",
    "//packages/cmk-rulesets",
    "//packages/cmk-server-side-calls",
    "//packages/cmk-trace",
    "//packages/cmk-werks",
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

py_proto_library(
    name = "config_proto_pb2",
    deps = ["//:config_proto"],
)

[py_library(
    name = "lib_cmk_" + edition,
    srcs = srcs,
    imports = [".."],
    visibility = ["//tests:__subpackages__"],
    deps = [
        "config_proto_pb2",
        "lib_cmk",
    ],
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
        "@rrdtool_native//:rrdtool_python_lib",
    ] + select({
        "@//:gpl_repo": [],
        "@//:gpl+enterprise_repo": [
            "config_proto_pb2",
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
        "config_proto_pb2",
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

py_test(
    name = "doctest",
    srcs = ["__test__.py"],
    args = [
        "--config-file=$(location @//:pyproject.toml)",
        "--doctest-modules",
        "--override-ini=consider_namespace_packages=true",
    ],
    data = ["@//:pyproject.toml"],
    imports = [".."],
    main = ":__test__.py",
    visibility = ["//tests:__subpackages__"],
    deps = [
        ":__test__",
        "//agents/plugins:mk_jolokia",
        "//cmk:lib_cmk",
        "//cmk:lib_cmk_cre",
        requirement("pytest"),
        requirement("polyfactory"),
        requirement("marshmallow"),
    ] + CMK_PACKAGES,
)
