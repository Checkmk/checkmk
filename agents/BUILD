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
    ],
    visibility = ["//visibility:public"],
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
