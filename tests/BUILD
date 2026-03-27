load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

package(default_visibility = [":__subpackages__"])

exports_files(["dev-requirements.in"])

py_library(
    name = "testlib",
    srcs = ["__init__.py"] + glob(
        include = ["testlib/**/*.py"],
    ),
    data = glob(
        include = ["testlib/**"],
        allow_empty = True,
        exclude = ["testlib/**/*.py"],
    ),
    imports = [".."],
    visibility = ["//:__subpackages__"],
    deps = [
        "//cmk/base",
        "//cmk/checkengine",
        "//cmk/gui",
        "//cmk/utils",
        "//packages/cmk-relay-protocols",
        "//tests/testlib/common:repo",
        "//tests/testlib/common:utils",
        requirement("beautifulsoup4"),
        requirement("clickhouse-connect"),
        requirement("cryptography"),
        requirement("docker"),
        requirement("dockerpty"),
        requirement("fastapi"),
        requirement("flask"),
        requirement("pexpect"),
        requirement("playwright"),
        requirement("psutil"),
        requirement("pyjwt"),
        requirement("pyyaml"),
        requirement("pytest"),
        requirement("pytest-check"),
        requirement("pytest-mock"),
        requirement("requests"),
    ] + select({
        "//:gpl+nonfree_repo": [
            "//cmk/editions/nonfree:cloud",
            "//non-free/packages/cmk-licensing-nonfree",
            "//non-free/packages/cmk-metric-backend",
        ],
        "//:gpl_repo": [],
    }),
)

py_library(
    name = "conftest",
    testonly = True,
    srcs = ["conftest.py"],
    deps = [
        "//tests/testlib/common:repo",
        "//tests/testlib/common:utils",
        requirement("playwright"),
        requirement("pytest"),
        requirement("pytest-check"),
        requirement("pytest-metadata"),
        ":testlib",
    ],
)

py_library(
    name = "testlib_system_level",
    testonly = True,
    srcs = ["__init__.py"] + glob(
        include = ["testlib/**/*.py"],
        exclude = ["testlib/unit/**"],
    ),
    data = glob(
        include = ["testlib/**"],
        allow_empty = True,
        exclude = ["testlib/**/*.py"],
    ),
    imports = [".."],
    deps = [
        "//cmk/base",
        "//cmk/checkengine",
        "//cmk/gui",
        "//cmk/utils",
        "//packages/cmk-relay-protocols",
        "//tests/testlib/common:repo",
        "//tests/testlib/common:utils",
        requirement("beautifulsoup4"),
        requirement("clickhouse-connect"),
        requirement("cryptography"),
        requirement("docker"),
        requirement("dockerpty"),
        requirement("fastapi"),
        requirement("pexpect"),
        requirement("playwright"),
        requirement("psutil"),
        requirement("pyjwt"),
        requirement("pytest"),
        requirement("pytest-check"),
        requirement("pyyaml"),
        requirement("requests"),
    ] + select({
        "//:gpl+nonfree_repo": ["//cmk/editions/nonfree:cloud"],
        "//:gpl_repo": [],
    }),
)

py_library(
    name = "agent-integration",
    testonly = True,
    srcs = glob(
        include = [
            "agent-integration/**/*.py",
        ],
    ),
    imports = [".."],
    deps = [
        "//tests/testlib/common:repo",
        requirement("docker"),
        requirement("pytest"),
    ],
)

py_library(
    name = "agent_plugin_integration",
    testonly = True,
    srcs = glob(
        include = ["agent_plugin_integration/**/*.py"],
    ),
    imports = [".."],
    deps = [
        ":testlib",
        "//tests/testlib/common:repo",
        "//tests/testlib/common:utils",
        requirement("docker"),
        requirement("pytest"),
    ],
)

py_library(
    name = "bandit-nosec-markers",
    testonly = True,
    srcs = glob(
        include = ["bandit-nosec-markers/**/*.py"],
    ),
    imports = [".."],
    deps = [":testlib"],
)

py_library(
    name = "composition",
    testonly = True,
    srcs = glob(
        include = ["composition/**/*.py"],
        exclude = ["composition/**/nonfree/**"],
    ) + select({
        "//:gpl+nonfree_repo": glob(
            include = ["composition/**/nonfree/**/*.py"],
            allow_empty = True,
        ),
        "//:gpl_repo": [],
    }),
    imports = [".."],
    deps = [
        ":scripts",
        ":testlib",
        "//tests/testlib/common:utils",
        requirement("clickhouse_connect"),
        requirement("pytest"),
        requirement("cryptography"),
        requirement("requests"),
        requirement("opentelemetry-instrumentation-requests"),
    ],
)

py_library(
    name = "docker",
    testonly = True,
    srcs = glob(
        include = ["docker/**/*.py"],
    ),
    imports = [".."],
    deps = [
        requirement("docker"),
        requirement("pytest"),
        requirement("requests"),
        ":testlib",
    ],
)

py_library(
    name = "etc",
    testonly = True,
    srcs = glob(
        include = ["etc/**/*.py"],
        allow_empty = True,
        exclude = ["etc/**/nonfree/**"],
    ) + select({
        "//:gpl+nonfree_repo": glob(
            include = ["etc/**/nonfree/**/*.py"],
            allow_empty = True,
        ),
        "//:gpl_repo": [],
    }),
    imports = [".."],
)

py_library(
    name = "extension_compatibility",
    testonly = True,
    srcs = glob(
        include = ["extension_compatibility/**/*.py"],
    ),
    imports = [".."],
    deps = [
        "//tests/testlib/common:repo",
        requirement("pytest"),
        ":testlib",
    ],
)

py_library(
    name = "gui_crawl",
    testonly = True,
    srcs = glob(
        include = ["gui_crawl/**/*.py"],
    ),
    imports = [".."],
    deps = [
        requirement("playwright"),
        requirement("requests"),
        requirement("lxml"),
        requirement("pytest"),
        requirement("beautifulsoup4"),
        ":testlib",
    ],
)

py_library(
    name = "gui_e2e",
    testonly = True,
    srcs = glob(
        include = ["gui_e2e/**/*.py"],
        exclude = ["gui_e2e/**/nonfree/**"],
    ) + select({
        "//:gpl+nonfree_repo": glob(
            include = ["gui_e2e/**/nonfree/**/*.py"],
            allow_empty = True,
        ),
        "//:gpl_repo": [],
    }),
    imports = [".."],
    deps = [
        "//tests/testlib/common:repo",
        "//tests/testlib/common:utils",
        requirement("playwright"),
        requirement("pytest"),
        requirement("requests"),
        requirement("faker"),
        requirement("pyyaml"),
        requirement("pytest_playwright"),
        requirement("clickhouse_connect"),
        ":testlib",
    ],
)

py_library(
    name = "integration",
    testonly = True,
    srcs = glob(
        include = ["integration/**/*.py"],
        exclude = ["integration/**/nonfree/**"],
    ) + select({
        "//:gpl+nonfree_repo": glob(
            include = ["integration/**/nonfree/**/*.py"],
            allow_empty = True,
        ),
        "//:gpl_repo": [],
    }),
    imports = [".."],
    deps = [
        requirement("pytest"),
        requirement("pytest-mock"),
        requirement("pysaml2"),
        requirement("matplotlib"),
        requirement("requests"),
        requirement("pyyaml"),
        requirement("clickhouse_connect"),
        requirement("cryptography"),
        requirement("pysnmp"),
        requirement("psutil"),
        requirement("semver"),
        requirement("polyfactory"),
        requirement("psycopg"),
        requirement("protobuf"),
        requirement("pyopenssl"),
        ":extension_compatibility",
        ":scripts",
        ":testlib",
        "//cmk/post_rename_site",
        "//packages/cmk-agent-receiver",
        "//tests/testlib/common:utils",
    ] + select({
        "//:gpl+nonfree_repo": [
            "//non-free/packages/cmk-licensing-nonfree",
        ],
        "//:gpl_repo": [],
    }),
)

py_library(
    name = "integration_redfish",
    testonly = True,
    srcs = glob(
        include = ["integration_redfish/**/*.py"],
    ),
    imports = [".."],
    deps = [
        requirement("pytest"),
        requirement("grequests"),
        requirement("multipart"),
        requirement("opentelemetry-instrumentation-requests"),
        ":testlib",
    ],
)

py_library(
    name = "packaging",
    testonly = True,
    srcs = glob(
        include = ["packaging/**/*.py"],
    ),
    imports = [".."],
    deps = [
        ":testlib",
        "//tests/testlib/common:utils",
        requirement("pytest"),
    ],
)

py_library(
    name = "performance",
    testonly = True,
    srcs = glob(
        include = ["performance/**/*.py"],
    ),
    imports = [".."],
    deps = [
        "//cmk:validate_plugins",
        requirement("pytest"),
        requirement("psycopg"),
        requirement("jira"),
        requirement("matplotlib"),
        requirement("psutil"),
        requirement("requests"),
        requirement("playwright"),
        requirement("pytest_benchmark"),
        ":testlib",
        "//tests/testlib/common:repo",
        "//tests/testlib/common:utils",
    ],
)

py_library(
    name = "plugins_integration",
    testonly = True,
    srcs = glob(
        include = ["plugins_integration/**/*.py"],
        exclude = ["plugins_integration/**/nonfree/**"],
    ) + select({
        "//:gpl+nonfree_repo": glob(
            include = ["plugins_integration/**/nonfree/**/*.py"],
            allow_empty = True,
        ),
        "//:gpl_repo": [],
    }),
    imports = [".."],
    deps = [
        requirement("pytest"),
        ":testlib",
    ],
)

py_library(
    name = "plugins_siteless",
    testonly = True,
    # TODO: The tests include non-free plugins (cmk.plugins.custom_query_metric_backend.special_agents.nonfree.ultimate)
    # Introduce a folder structure to separate free and non-free tests.
    srcs = select({
        "//:gpl+nonfree_repo": glob(
            include = ["plugins_siteless/**/*.py"],
        ),
        "//:gpl_repo": [],
    }),
    imports = [".."],
    deps = [
        ":testlib",
        "//packages/cmk-plugins:cisco_prime",
        "//packages/cmk-plugins:elasticsearch",
        "//packages/cmk-plugins:gerrit",
        "//packages/cmk-plugins:ipmi",
        "//packages/cmk-plugins:kube",
        "//packages/cmk-plugins:netapp",
        "//packages/cmk-plugins:proxmox_ve",
        "//packages/cmk-plugins:pure_storage_fa",
        "//packages/cmk-plugins:rabbitmq",
        "//packages/cmk-plugins:redfish",
        "//packages/cmk-plugins:splunk",
        "//tests/testlib/unit",
        requirement("pytest"),
    ],
)

py_library(
    name = "scripts",
    testonly = True,
    srcs = glob(
        include = ["scripts/**/*.py"],
        exclude = ["scripts/**/nonfree/**"],
    ) + select({
        "//:gpl+nonfree_repo": glob(
            include = ["scripts/**/nonfree/**/*.py"],
            allow_empty = True,
        ),
        "//:gpl_repo": [],
    }),
    imports = [".."],
    deps = [
        "//tests/testlib/common:repo",
        requirement("cryptography"),
        requirement("requests"),
        requirement("psycopg"),
        requirement("jinja2"),
        requirement("prometheus-client"),
        requirement("opentelemetry-sdk"),
        requirement("opentelemetry-exporter-otlp"),
        ":testlib",
    ],
)

py_library(
    name = "typeshed",
    testonly = True,
    srcs = glob(
        include = ["typeshed/**/*.py"],
        allow_empty = True,
    ),
    imports = [".."],
)

py_library(
    name = "update",
    testonly = True,
    srcs = glob(
        include = ["update/**/*.py"],
        exclude = ["update/**/nonfree/**"],
    ) + select({
        "//:gpl+nonfree_repo": glob(
            include = ["update/**/nonfree/**/*.py"],
            allow_empty = True,
        ),
        "//:gpl_repo": [],
    }),
    imports = [".."],
    deps = [
        ":scripts",
        ":testlib",
        "//tests/testlib/common:utils",
        requirement("pytest"),
    ],
)

sh_library(
    name = "tests_sh",
    srcs = [
        "performance/database/mk_client_cert.sh",
        "performance/database/mk_server_cert.sh",
        "performance/perftest.sh",
        "scripts/find_modified_lock_files",
        "scripts/run_code_coverage.sh",
        "scripts/setup_openldap.sh",
        "scripts/setup_postfix.sh",
        "scripts/teardown_openldap.sh",
        "scripts/teardown_postfix.sh",
        "scripts/verify_test_python_files.sh",
    ],
)
