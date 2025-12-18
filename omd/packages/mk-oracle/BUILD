load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

pkg_files(
    name = "mk-oracle_pkg",
    # HACK
    # * mk-oracle needs to be build for four specific platforms: solaris, aix, windows and against an old glibc (rhel8)
    # * that's why we pre-built it on those platforms before-hand and put it in the workspace
    # * see package_helper.groovy
    # TODO: Please let bazel take over building mk-oracle for all platforms in the current workspace eventually...
    srcs = [
        ":mk-oracle.aix",
        ":mk-oracle.exe",
        ":mk-oracle.rhel8",
        ":mk-oracle.solaris",
    ],
    attributes = pkg_attributes(mode = "0755"),
    renames = {
        ":mk-oracle.rhel8": "lib/python3/cmk/plugins/oracle/agents/mk-oracle",
        ":mk-oracle.solaris": "lib/python3/cmk/plugins/oracle/agents/mk-oracle.solaris",
        ":mk-oracle.aix": "lib/python3/cmk/plugins/oracle/agents/mk-oracle.aix",
        ":mk-oracle.exe": "lib/python3/cmk/plugins/oracle/agents/mk-oracle.exe",
    },
    tags = ["manual"],
)

pkg_tar(
    name = "mk-oracle",
    srcs = [":mk-oracle_pkg"],
    stamp = 1,
    tags = ["manual"],
    visibility = ["//omd:__subpackages__"],
)
