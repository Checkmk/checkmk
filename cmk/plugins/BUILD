load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:doctest.bzl", "py_doc_test")

package(default_visibility = [
    "//cmk:__subpackages__",
    "//tests:__subpackages__",
])

py_library(
    name = "plugins",
    srcs = glob(
        include = ["**/*.py"],
        exclude = [
            # this does not match, but keep it as a safeguard for now
            "**/community/**",
            "**/nonfree/**",
        ],
    ) + [
        "//cmk/plugins/collection/agents",
        "//cmk/plugins/files/agents",
        "//cmk/plugins/jolokia/agents",
        "//cmk/plugins/mongodb/agents",
        "//cmk/plugins/mtr/agents",
        "//cmk/plugins/nginx/agents",
        "//cmk/plugins/plesk/agents",
        "//cmk/plugins/postgres/agents",
        "//cmk/plugins/sap/agents",
    ],
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//non-free/packages/cmk-dcd:__pkg__",
        "//non-free/packages/cmk-metric-backend:__pkg__",
        "//non-free/packages/cmk-otel-collector:__pkg__",
        "//non-free/packages/cmk-plugins-nonfree:__subpackages__",
        "//non-free/packages/cmk-robotmk:__pkg__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/bi",
        "//cmk/utils",
        "//packages/cmk-ccc:regex",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:store",
        "//packages/cmk-ccc:version",
        "//packages/cmk-ccc:version-info",
        "//packages/cmk-ec:syslog",
        "//packages/cmk-livestatus-client",
        "//packages/cmk-plugin-apis:agent_based",
        "//packages/cmk-plugin-apis:bakery",
        "//packages/cmk-plugin-apis:diagnostics",
        "//packages/cmk-plugin-apis:graphing",
        "//packages/cmk-plugin-apis:inventory_ui",
        "//packages/cmk-plugin-apis:password_store",
        "//packages/cmk-plugin-apis:rulesets",
        "//packages/cmk-plugin-apis:server_side_calls",
        "//packages/cmk-plugin-apis:server_side_programs",
        "//packages/cmk-plugins:lib",
        requirement("cryptography"),
        requirement("exchangelib"),  # missing wheel
        requirement("feedparser"),
        requirement("jira"),
        requirement("lxml"),
        requirement("meraki"),
        requirement("msal"),
        requirement("oauthlib"),
        requirement("paho-mqtt"),
        requirement("paramiko"),
        requirement("psycopg2-binary"),  # missing wheel
        requirement("pyasn1"),
        requirement("pydantic"),
        requirement("pymongo"),
        requirement("pymssql"),
        requirement("pymysql"),
        requirement("pysmb"),
        requirement("python-dateutil"),
        requirement("python-snap7"),
        requirement("pyyaml"),
        requirement("requests"),
        requirement("requests-oauthlib"),
    ],
)

filegroup(
    name = "checkman",
    srcs = glob(
        ["**/checkman/**"],
    ),
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
)

filegroup(
    name = "agents",
    srcs = glob(
        include = ["**/agents/**/*"],
        exclude = [
            "**/agents/**/*.py",
            "oracle/agents/.gitignore",
            "oracle/agents/README.md",
        ],
    ),
)

filegroup(
    name = "_ignored",
    srcs = glob(
        # Fails if empty. Make sure to move the exclude above when these move.
        [
            "oracle/agents/.gitignore*",
            "oracle/agents/README.md*",
        ],
    ),
)

filegroup(
    name = "libexec",
    srcs = glob(
        [
            "**/libexec/*",
        ],
    ),
    visibility = [
        "//cmk:__subpackages__",
        "//omd:__subpackages__",
        "//tests:__subpackages__",
    ],
)

sh_library(
    name = "active_checks",
    srcs = [
        "activemq/libexec/agent_activemq",
        "alertmanager/libexec/agent_alertmanager",
        "allnet_ip_sensoric/libexec/agent_allnet_ip_sensoric",
        "appdynamics/libexec/agent_appdynamics",
        "azure_status/libexec/agent_azure_status",
        "checkmk/libexec/agent_bi",
        "checkmk/libexec/check_cmk_inv",
        "checkmk/libexec/check_notify_count",
        "cisco_meraki/libexec/agent_cisco_meraki",
        "couchbase/libexec/agent_couchbase",
        "datadog/libexec/agent_datadog",
        "ddn_s2a/libexec/agent_ddn_s2a",
        "emailchecks/libexec/check_mail",
        "emailchecks/libexec/check_mail_loop",
        "emailchecks/libexec/check_mailboxes",
        "form_submit/libexec/check_form_submit",
        "fritzbox/libexec/agent_fritzbox",
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
        "oracle/agents/oracle_unified_async_custom_metrics",
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
        "storeonce/libexec/agent_storeonce4x",
        "tinkerforge/libexec/agent_tinkerforge",
        "traceroute/libexec/check_traceroute",
        "uniserv/libexec/check_uniserv",
        "vnx_quotas/libexec/agent_vnx_quotas",
        "zerto/libexec/agent_zerto",
    ],
)

py_doc_test(
    name = "doctest",
    size = "small",
    srcs = [":plugins"],
)
