load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

package(default_visibility = [
    "//cmk:__subpackages__",
    "//tests/unit:__subpackages__",
])

py_library(
    name = "plugins",
    srcs = glob(
        include = ["**/*.py"],
        exclude = [
            "**/community/**",
            "**/nonfree/**",
        ],
    ) + [
        "//cmk/plugins/mtr/agents",
        "//cmk/plugins/plesk/agents",
        "//cmk/plugins/postgres/agents",
    ],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/bi",
        "//cmk/utils",
        "//packages/cmk-ccc:debug",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:i18n",
        "//packages/cmk-ccc:plugin-registry",
        "//packages/cmk-ccc:regex",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:store",
        "//packages/cmk-ccc:version",
        "//packages/cmk-crypto",
        "//packages/cmk-ec:event",
        "//packages/cmk-ec:syslog",
        "//packages/cmk-events",
        "//packages/cmk-livestatus-client:py_livestatus",
        "//packages/cmk-plugin-apis:agent_based",
        "//packages/cmk-plugin-apis:bakery",
        "//packages/cmk-plugin-apis:discover_plugins",
        "//packages/cmk-plugin-apis:graphing",
        "//packages/cmk-plugin-apis:inventory_ui",
        "//packages/cmk-plugin-apis:password_store",
        "//packages/cmk-plugin-apis:rulesets",
        "//packages/cmk-plugin-apis:server_side_calls",
        "//packages/cmk-plugin-apis:server_side_programs",
        "//packages/cmk-plugins:lib",
        "//packages/cmk-werks",
        requirement("boto3"),
        requirement("botocore"),
        requirement("cryptography"),
        requirement("exchangelib"),  # missing wheel
        requirement("feedparser"),
        requirement("google-api-python-client"),
        requirement("google-auth"),
        requirement("google-cloud-asset"),
        requirement("google-cloud-monitoring"),
        requirement("jira"),
        requirement("lxml"),
        requirement("meraki"),
        requirement("msal"),
        requirement("mypy-boto3-logs"),
        requirement("oauthlib"),
        requirement("paho-mqtt"),
        requirement("paramiko"),
        requirement("protobuf"),
        requirement("psycopg2-binary"),  # missing wheel
        requirement("pyasn1"),
        requirement("pydantic"),
        requirement("pymongo"),
        requirement("pymssql"),
        requirement("pymysql"),
        requirement("pyopenssl"),
        requirement("pysmb"),
        requirement("python-dateutil"),
        requirement("python-snap7"),
        requirement("pyyaml"),
        requirement("requests"),
        requirement("requests-oauthlib"),
    ],
)

py_library(
    name = "plugins_community",
    srcs = glob(
        include = ["**/community/**/*.py"],
        allow_empty = True,
        exclude = ["**/nonfree/**"],
    ),
    imports = ["../.."],
    deps = [":plugins"],
)

py_library(
    name = "plugins_pro",
    srcs = glob(
        include = [
            "**/nonfree/**/pro/**/*.py",
            "**/nonfree/**/*.py",
        ],
        allow_empty = True,
        exclude = [
            "**/nonfree/**/cloud/**",
            "**/nonfree/**/ultimate/**",
            "**/nonfree/**/ultimatemt/**",
        ],
    ),
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":plugins",
        ":plugins_community",
        requirement("robotframework"),
    ],
)

py_library(
    name = "plugins_ultimate",
    srcs = glob(
        include = [
            "**/nonfree/**/ultimate/**/*.py",
            "**/nonfree/__init__.py",
        ],
        allow_empty = True,
    ),
    imports = ["../.."],
    deps = [
        ":plugins",
        ":plugins_community",
        ":plugins_pro",
    ],
)

py_library(
    name = "plugins_cloud",
    srcs = glob(
        include = [
            "**/nonfree/**/cloud/**/*.py",
            "**/nonfree/__init__.py",
        ],
        allow_empty = True,
    ),
    imports = ["../.."],
    deps = [
        ":plugins",
        ":plugins_community",
        ":plugins_pro",
        ":plugins_ultimate",
    ],
)

py_library(
    name = "plugins_ultimatemt",
    srcs = glob(
        include = [
            "**/nonfree/**/ultimatemt/**/*.py",
            "**/nonfree/__init__.py",
        ],
        allow_empty = True,
    ),
    imports = ["../.."],
    visibility = [
        "//cmk:__pkg__",
        "//cmk/editions/nonfree:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":plugins",
        ":plugins_community",
        ":plugins_pro",
        ":plugins_ultimate",
    ],
)

filegroup(
    name = "checkman_community",
    srcs = glob(
        ["**/checkman/**"],
        exclude = [
            "**/OWNERS",
            "**/checkman/nonfree/**",
        ],
    ),
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
)

filegroup(
    name = "checkman_pro",
    srcs = glob(
        ["**/checkman/nonfree/pro/**"],
        allow_empty = True,
        exclude = ["**/OWNERS"],
    ) + [
        ":checkman_community",
    ],
)

filegroup(
    name = "checkman_ultimate",
    srcs = glob(
        ["**/checkman/nonfree/ultimate/**"],
        allow_empty = True,
        exclude = ["**/OWNERS"],
    ) + [
        ":checkman_community",
        ":checkman_pro",
        "//cmk/plugins/custom_query_metric_backend:checkman",
    ],
)

filegroup(
    name = "checkman_cloud",
    srcs = glob(
        ["**/checkman/nonfree/cloud/**"],
        allow_empty = True,
        exclude = ["**/OWNERS"],
    ) + [
        ":checkman_community",
        ":checkman_pro",
        ":checkman_ultimate",
    ],
)

filegroup(
    name = "checkman_ultimatemt",
    srcs = glob(
        ["**/checkman/nonfree/ultimatemt/**"],
        allow_empty = True,
        exclude = ["**/OWNERS"],
    ) + [
        ":checkman_community",
        ":checkman_pro",
        ":checkman_ultimate",
    ],
)

filegroup(
    name = "agents",
    srcs = glob(
        include = ["**/agents/**/*"],
        exclude = ["**/agents/**/*.py"],
    ),
)

filegroup(
    name = "libexec",
    srcs = glob(
        [
            "**/libexec/*",
        ],
    ) + [
        "//cmk/plugins/custom_query_metric_backend:libexec",
    ],
    visibility = [
        "//cmk:__subpackages__",
        "//omd:__subpackages__",
        "//tests:__subpackages__",
    ],
)

filegroup(
    name = "shell_scripts",
    srcs = [
        "activemq/libexec/agent_activemq",
        "alertmanager/libexec/agent_alertmanager",
        "allnet_ip_sensoric/libexec/agent_allnet_ip_sensoric",
        "appdynamics/libexec/agent_appdynamics",
        "azure_deprecated/libexec/agent_azure",
        "azure_status/libexec/agent_azure_status",
        "checkmk/libexec/agent_bi",
        "checkmk/libexec/check_cmk_inv",
        "cisco_meraki/libexec/agent_cisco_meraki",
        "couchbase/libexec/agent_couchbase",
        "datadog/libexec/agent_datadog",
        "ddn_s2a/libexec/agent_ddn_s2a",
        "emailchecks/libexec/check_mail",
        "emailchecks/libexec/check_mail_loop",
        "emailchecks/libexec/check_mailboxes",
        "form_submit/libexec/check_form_submit",
        "fritzbox/libexec/agent_fritzbox",
        "gcp/libexec/agent_gcp",
        "gcp/libexec/agent_gcp_status",
        "hivemanager/libexec/agent_hivemanager",
        "hivemanager_ng/libexec/agent_hivemanager_ng",
        "hp_msa/libexec/agent_hp_msa",
        "hpe_3par/libexec/agent_three_par",
        "ibmsvc/libexec/agent_ibmsvc",
        "innovaphone/libexec/agent_innovaphone",
        "jira/libexec/agent_jira",
        "jolokia/libexec/agent_jolokia",
        "mobileiron/libexec/agent_mobileiron",
        "mqtt/libexec/agent_mqtt",
        "oracle/.f12",
        "oracle/agents/oracle_unified_async",
        "oracle/agents/oracle_unified_sync",
        "prometheus/libexec/agent_prometheus",
        "ruckus_spot/libexec/agent_ruckus_spot",
        "salesforce/libexec/agent_salesforce",
        "sftp/libexec/check_sftp",
        "siemens_plc/libexec/agent_siemens_plc",
        "smb/libexec/agent_smb_share",
        "smb/libexec/check_disk_smb",
        "sql/libexec/check_sql",
        "storeonce/libexec/agent_storeonce",
        "storeonce4x/libexec/agent_storeonce4x",
        "tinkerforge/libexec/agent_tinkerforge",
        "traceroute/libexec/check_traceroute",
        "uniserv/libexec/check_uniserv",
        "vnx_quotas/libexec/agent_vnx_quotas",
        "zerto/libexec/agent_zerto",
    ],
)
