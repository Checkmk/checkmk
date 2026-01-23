load("@bazel_skylib//rules:write_file.bzl", "write_file")
load("//bazel/rules:filename_from_flag.bzl", "filename_from_flag")

AGENT_PACKAGES = {
    "check-mk-agent.noarch.rpm": "check-mk-agent-{VERSION}-1.noarch.rpm",
    "check-mk-agent_all.deb": "check-mk-agent_{VERSION}-1_all.deb",
}

[
    write_file(
        name = package + "_write",
        out = package + ".faked",
        content = ["This artifact was faked during the build process by bazel."],
        visibility = ["//omd:__subpackages__"],
    )
    for package in AGENT_PACKAGES
]

[
    filename_from_flag(
        name = package + "_with_version",
        src = select({
            "@//:use_fake_artifacts_enabled": package + ".faked",
            "//conditions:default": package,
        }),
        file_name = template,
        replacements = {
            "VERSION": "@cmk//version",
        },
    )
    for package, template in AGENT_PACKAGES.items()
]

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
    ] + [
        package + "_with_version"
        for package in AGENT_PACKAGES
    ],
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
