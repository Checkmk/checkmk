load("@aspect_rules_py//py:defs.bzl", "py_library")

exports_files(
    [
        "dev-requirements.in",
    ],
)

exports_files(
    ["mk_redis"],
    visibility = ["//tests/unit-shell/agents:__pkg__"],
)

filegroup(
    name = "srcs",
    srcs = glob(
        include = ["*"],
        exclude = [
            "__init__.py",
            "BUILD",
            "OWNERS",
            "Makefile",
        ],
    ),
    visibility = ["//visibility:public"],
)

py_library(
    name = "agent-plugins-python",
    srcs = [
        "mk_logwatch.py",
        "mk_tinkerforge.py",
    ],
    imports = ["."],
    visibility = ["//tests:__subpackages__"],
)

sh_library(
    name = "agents_plugins_sh",
    srcs = [
        "asmcmd.sh",
        "hpux_lunstats",
        "hpux_statgrab",
        "ibm_mq",
        "jar_signature",
        "lnx_container_host_if.linux",
        "mk_apt",
        "mk_errpt.aix",
        "mk_informix",
        "mk_inventory.aix",
        "mk_inventory.linux",
        "mk_inventory.solaris",
        "mk_mysql",
        "mk_omreport",
        "mk_oracle",
        "mk_oracle_crs",
        "mk_redis",
        "mk_scaleio",
        "runas",
        "//agents/cfg_examples:agents_cfg_examples_sh",
    ],
    visibility = ["//visibility:public"],
)
