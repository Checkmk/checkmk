load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files")
load("//bazel/rules:pkg.bzl", "pkg_tar")

pkg_files(
    name = "mk-oracle_pkg",
    # HACK
    # * mk-oracle needs to be build for three specific platforms: solaris, aix and windows
    # * that's why we pre-built it on those platforms before-hand and put it in the workspace
    # * see package_helper.groovy
    # TODO: Please let bazel take over building mk-oracle for all platforms in the current workspace eventually...
    srcs = [
        ":mk-oracle.aix",
        ":mk-oracle.exe",
        ":mk-oracle.solaris",
    ],
    attributes = pkg_attributes(mode = "0755"),
    renames = {
        ":mk-oracle.solaris": "lib/python3/cmk/plugins/oracle/agents/mk-oracle.solaris",
        ":mk-oracle.aix": "lib/python3/cmk/plugins/oracle/agents/mk-oracle.aix",
        ":mk-oracle.exe": "lib/python3/cmk/plugins/oracle/agents/mk-oracle.exe",
    },
    tags = ["manual"],
)

# Built hermetically against the glibc of the gcc_toolchain sysroot, so
# unlike the other platforms it is never fetched.
pkg_files(
    name = "mk-oracle_linux_pkg",
    srcs = ["//packages/mk-oracle"],
    attributes = pkg_attributes(mode = "0755"),
    prefix = "lib/python3/cmk/plugins/oracle/agents",
    tags = ["manual"],
)

pkg_tar(
    name = "mk-oracle",
    srcs = [
        ":mk-oracle_linux_pkg",
        ":mk-oracle_pkg",
    ],
    stamp = 1,
    tags = ["manual"],
    visibility = ["//omd:__subpackages__"],
)
