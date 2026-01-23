load("@bazel_skylib//rules:write_file.bzl", "write_file")
load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

ARTIFACTS = [
    "mk-oracle.aix",
    "mk-oracle.exe",
    "mk-oracle.rhel8",
    "mk-oracle.solaris",
]

[write_file(
    name = artifact + "_write",
    out = artifact + ".faked",
    content = ["This artifact was faked during the build process by bazel."],
    visibility = ["//omd:__subpackages__"],
) for artifact in ARTIFACTS]

pkg_files(
    name = "mk-oracle_pkg",
    srcs = select({
        "@//:use_fake_artifacts_enabled": [artifact + ".faked" for artifact in ARTIFACTS],
        "//conditions:default": ARTIFACTS,
    }),
    attributes = pkg_attributes(mode = "0755"),
    renames = select({
        "@//:use_fake_artifacts_enabled": {
            ":mk-oracle.rhel8.faked": "lib/python3/cmk/plugins/oracle/agents/mk-oracle.faked",
            ":mk-oracle.solaris.faked": "lib/python3/cmk/plugins/oracle/agents/mk-oracle.solaris.faked",
            ":mk-oracle.aix.faked": "lib/python3/cmk/plugins/oracle/agents/mk-oracle.aix.faked",
            ":mk-oracle.exe.faked": "lib/python3/cmk/plugins/oracle/agents/mk-oracle.exe.faked",
        },
        "//conditions:default": {
            ":mk-oracle.rhel8": "lib/python3/cmk/plugins/oracle/agents/mk-oracle",
            ":mk-oracle.solaris": "lib/python3/cmk/plugins/oracle/agents/mk-oracle.solaris",
            ":mk-oracle.aix": "lib/python3/cmk/plugins/oracle/agents/mk-oracle.aix",
            ":mk-oracle.exe": "lib/python3/cmk/plugins/oracle/agents/mk-oracle.exe",
        },
    }),
    tags = ["manual"],
)

pkg_tar(
    name = "mk-oracle",
    srcs = [":mk-oracle_pkg"],
    stamp = 1,
    tags = ["manual"],
    visibility = ["//omd:__subpackages__"],
)
