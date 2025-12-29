filegroup(
    name = "agents",
    srcs = [
        "CONTENTS",
        "check_mk_agent.aix",
        "check_mk_agent.freebsd",
        "check_mk_agent.hpux",
        "check_mk_agent.linux",
        "check_mk_agent.macosx",
        "check_mk_agent.netbsd",
        "check_mk_agent.openbsd",
        "check_mk_agent.openvms",
        "check_mk_agent.openwrt",
        "check_mk_agent.solaris",
        "check_mk_caching_agent.linux",
        "mk-job",
        "mk-job.aix",
        "mk-job.solaris",
        "waitmax",
    ] + glob(
        [
            "check-mk-agent-*.noarch.rpm",
            "check-mk-agent_*_all.deb",
        ],
        # Files created elsewhere
        allow_empty = True,
    ),
    visibility = ["//omd:__subpackages__"],
)

filegroup(
    name = "agents-linux",
    srcs = [
        "linux/cmk-agent-ctl",
        "linux/cmk-agent-ctl.gz",
        "linux/cmk-agent-ctl-aarch64",
        "linux/cmk-agent-ctl-aarch64.gz",
        "linux/mk-sql",
    ],
    visibility = ["//omd:__subpackages__"],
)

filegroup(
    name = "srcs",
    srcs = [
        "scripts/manage-agent-user.sh",
        "scripts/manage-binaries.sh",
        "scripts/migrate.sh",
    ],
    visibility = ["//visibility:public"],
)

filegroup(
    name = "super-server",
    srcs = glob(["scripts/super-server/**"]),
    visibility = ["//visibility:public"],
)
