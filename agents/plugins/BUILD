load("@aspect_rules_py//py:defs.bzl", "py_binary")
load("@cmk_requirements//:requirements.bzl", "requirement")

exports_files(
    [
        "dev-requirements.in",
    ],
)

filegroup(
    name = "srcs",
    srcs = glob(
        include = ["*"],
        exclude = [
            "__init__.py",
            "BUILD",
            "OWNERS",
            ".f12",
            "Makefile",
        ],
    ),
    visibility = ["//visibility:public"],
)

py_binary(
    name = "apache_status",
    srcs = ["apache_status.py"],
    imports = ["."],
    visibility = ["//visibility:public"],
)

py_binary(
    name = "nginx_status",
    srcs = ["nginx_status.py"],
    imports = ["."],
    visibility = ["//visibility:public"],
)

py_library(
    name = "agent-plugins-python",
    srcs = [
        "apache_status.py",
        "isc_dhcpd.py",
        "mk_docker.py",
        "mk_filestats.py",
        "mk_inotify.py",
        "mk_logwatch.py",
        "mk_mongodb.py",
        "mk_podman.py",
        "mk_postgres.py",
        "mk_sap.py",
        "mk_tinkerforge.py",
        "nginx_status.py",
        "plesk_backups.py",
        "plesk_domains.py",
        "unitrends_replication.py",
    ],
    imports = ["."],
    visibility = ["//tests:__subpackages__"],
    # These dependencies are likely not complete.
    # Agent plugins sometimes depend on third party modules that
    # are currently not even a dev dependency.
    # As this is the deprecated location for agent plugins,
    # I am not cleanung this up now. This should be dealt with
    # on a case by case basis when migrating the bakery plugins to
    # the cmk.bakery.v2 API.
    # When you do so, please consider making the used libraries a
    # dev dependency and write some actual tests :-|
    deps = [
        requirement("docker"),
        requirement("pymongo"),
        requirement("requests"),
        requirement("urllib3"),
    ],
)

sh_library(
    name = "agents_plugins_sh",
    srcs = [
        ".f12",
        "asmcmd.sh",
        "db2_mem",
        "dnsclient",
        "hpux_lunstats",
        "hpux_statgrab",
        "ibm_mq",
        "jar_signature",
        "kaspersky_av",
        "lnx_container_host_if.linux",
        "lnx_quota",
        "lvm",
        "mailman3_lists",
        "mk_apt",
        "mk_cups_queues",
        "mk_db2.aix",
        "mk_db2.linux",
        "mk_errpt.aix",
        "mk_filehandler",
        "mk_informix",
        "mk_inventory.aix",
        "mk_inventory.linux",
        "mk_inventory.solaris",
        "mk_iptables",
        "mk_logins",
        "mk_mysql",
        "mk_nfsiostat",
        "mk_omreport",
        "mk_oracle",
        "mk_oracle_crs",
        "mk_redis",
        "mk_sap_hana",
        "mk_saprouter",
        "mk_scaleio",
        "mk_site_object_counts",
        "mk_sshd_config",
        "mk_suseconnect",
        "mk_tsm",
        "mk_zypper",
        "netstat.aix",
        "netstat.linux",
        "netstat.solaris",
        "nfsexports",
        "nfsexports.solaris",
        "nvidia_smi",
        "runas",
        "smart",
        "smart_posix",
        "symantec_av",
        "vxvm",
        "zorp",
        "//agents/cfg_examples:agents_cfg_examples_sh",
    ],
    visibility = ["//visibility:public"],
)
