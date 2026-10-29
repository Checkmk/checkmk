load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:doctest.bzl", "py_doc_test")

package(default_visibility = [
    "//cmk:__subpackages__",
    "//tests:__subpackages__",
])

py_library(
    name = "plugins",
    # Agent plug-ins are payload: we ship them to run on the monitored hosts,
    # but the site does not run them. Each agents directory with Python
    # plug-ins is a Bazel package of its own with two targets:
    #  - ":files" puts the plug-in files into the wheel via ":agents" below,
    #  - the py_library ":agents" declares the third-party modules the
    #    plug-ins import on the monitored host (rados, pymongo, ...). Only
    #    tests may depend on it, so these modules do not become dependencies
    #    of this target or of anything we ship.
    # The glob stops at those package boundaries; the check below makes sure
    # there are no other agent plug-ins.
    srcs = glob(
        include = ["**/*.py"],
        exclude = [
            # this does not match, but keep it as a safeguard for now
            "**/community/**",
            "**/nonfree/**",
        ],
    ),
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//non-free/packages/cmk-data-backend:__pkg__",
        "//non-free/packages/cmk-dcd:__pkg__",
        "//non-free/packages/cmk-otel-collector:__pkg__",
        "//non-free/packages/cmk-plugins-nonfree:__subpackages__",
        "//non-free/packages/cmk-robotmk:__pkg__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/config",
        "//cmk/plugins/jolokia/agents",  # imported by the special agent
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
        requirement("msal"),
        requirement("oauthlib"),
        requirement("paho-mqtt"),
        requirement("paramiko"),
        requirement("psycopg2-binary"),  # missing wheel
        requirement("pyasn1"),
        requirement("pydantic"),
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

# See the comment on the srcs of ":plugins".
[
    fail(msg = "%s: Python agent plug-ins need a BUILD file in their agents directory." % f)
    for f in glob(
        ["**/agents/**/*.py"],
        allow_empty = True,
    )
]

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
            "oracle/agents/.gitignore",
            "oracle/agents/README.md",
        ],
    ) + [
        # A glob stops at a package boundary. Agent directories with their
        # own BUILD file contribute their files through ":files".
        "//cmk/plugins/%s:files" % package
        for package in subpackages(include = ["*/agents"])
    ],
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
        "couchbase/libexec/agent_couchbase",
        "datadog/libexec/agent_datadog",
        "ddn_s2a/libexec/agent_ddn_s2a",
        "emailchecks/libexec/check_mail",
        "emailchecks/libexec/check_mail_loop",
        "emailchecks/libexec/check_mailboxes",
        "extremecloud_iq/libexec/agent_extremecloud_iq",
        "fritzbox/libexec/agent_fritzbox",
        "hivemanager/libexec/agent_hivemanager",
        "hivemanager_ng/libexec/agent_hivemanager_ng",
        "hp_msa/libexec/agent_hp_msa",
        "hpe_3par/libexec/agent_three_par",
        "innovaphone/libexec/agent_innovaphone",
        "jira/libexec/agent_jira",
        "jolokia/libexec/agent_jolokia",
        "mobileiron/libexec/agent_mobileiron",
        "mqtt/libexec/agent_mqtt",
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
        "uniserv/libexec/check_uniserv",
        "vnx_quotas/libexec/agent_vnx_quotas",
        "zerto/libexec/agent_zerto",
    ],
)

# Lets shellcheck see the agent plug-ins and their configuration examples.
# Nothing depends on this target.
sh_library(
    name = "agents_sh",
    srcs = [
        "checkmk/agents/mk_site_object_counts",
        "cups/agents/mk_cups_queues",
        "db2/agents/db2_mem",
        "db2/agents/mk_db2.aix",
        "db2/agents/mk_db2.linux",
        "filehandler/agents/mk_filehandler",
        "logins/agents/mk_logins",
        "lvm/agents/lvm",
        "mailman_lists/agents/mailman3_lists",
        "network/agents/mk_iptables",
        "nfsexports/agents/nfsexports",
        "nfsexports/agents/nfsexports.solaris",
        "oracle/agents/mk-oracle-v2_async",
        "oracle/agents/mk-oracle-v2_async.solaris",
        "oracle/agents/mk-oracle-v2_async_custom_metrics",
        "oracle/agents/mk-oracle-v2_async_custom_metrics.solaris",
        "oracle/agents/mk-oracle-v2_sync",
        "oracle/agents/mk-oracle-v2_sync.solaris",
        "sap_hana/agents/mk_sap_hana",
        "smart/agents/smart",
        "smart/agents/smart_posix",
        "suseconnect/agents/mk_suseconnect",
        "symantec/agents/symantec_av",
        "vxvm/agents/vxvm",
        "zorp/agents/zorp",
        "//agents/cfg_examples:agents_cfg_examples_sh",
    ],
)

py_doc_test(
    name = "doctest",
    size = "small",
    srcs = [":plugins"],
)

filegroup(
    name = "powershell_scripts",
    srcs = [
        "hyperv_cluster/agents/hyperv_host.ps1",
        "oracle/agents/mk-oracle-v2_async.ps1",
        "oracle/agents/mk-oracle-v2_async_custom_metrics.ps1",
        "oracle/agents/mk-oracle-v2_sync.ps1",
    ],
    tags = ["lint-with-psscriptanalyzer"],
)
