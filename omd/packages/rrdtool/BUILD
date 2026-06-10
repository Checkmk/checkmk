load("@bazel_skylib//rules:copy_directory.bzl", "copy_directory")
load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_filegroup", "pkg_files", "pkg_mkdirs", "pkg_mklink", "strip_prefix")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("//bazel/rules:package_wheel.bzl", "package_wheel")
load("//bazel/rules:patchelf.bzl", "set_runpath", "set_runpath_tree")

exports_files(["skel.permissions"])

rrd_cli_symlinks = [
    "rrdcreate",
    "rrdinfo",
]

set_runpath(
    name = "rrdtool_bin_runpath",
    srcs = [
        "@rrdtool_native//:rrdcached",
        "@rrdtool_native//:rrdtool",
        "@rrdtool_native//:rrdupdate",
    ],
    rpaths = ["$ORIGIN/../lib"],
    tags = ["manual"],
)

set_runpath(
    name = "rrdtool_lib_runpath",
    srcs = ["@rrdtool_native//:rrd_shared"],
    rpaths = ["$ORIGIN"],
    tags = ["manual"],
)

pkg_files(
    name = "rrdtool_bin",
    srcs = [":rrdtool_bin_runpath"],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "bin",
    tags = ["manual"],
)

pkg_files(
    name = "rrdtool_lib",
    srcs = [":rrdtool_lib_runpath"],
    attributes = pkg_attributes(
        mode = "0644",
    ),
    prefix = "lib",
    tags = ["manual"],
)

[
    pkg_mklink(
        name = "%s_symlink" % b,
        link_name = "bin/%s" % b,
        tags = ["manual"],
        target = "rrdupdate",
    )
    for b in rrd_cli_symlinks
]

pkg_mklink(
    name = "librrd_symlink",
    # The "8" is the version of the library - no idea yet how to get this
    link_name = "lib/librrd.so.8",
    tags = ["manual"],
    target = "librrd.so",
)

pkg_filegroup(
    name = "rrdtool_pkg",
    srcs = [
        ":librrd_symlink",
        ":rrdtool_bin",
        ":rrdtool_lib",
        ":rrdtool_skel_pkg",
    ] + ["%s_symlink" % b for b in rrd_cli_symlinks],
    tags = ["manual"],
    visibility = ["//visibility:public"],
)

pkg_tar(
    name = "rrdtool_tar",
    srcs = [":rrdtool_pkg"],
    package_file_name = "rrdtool.tar",
    stamp = 1,
    tags = ["manual"],
    visibility = ["//visibility:public"],
)

package_wheel(
    name = "rrdtool_python_tar",
    rpath = "$ORIGIN/../..",
    visibility = ["//visibility:public"],
    whl = "@rrdtool_native//:rrdtool_python_wheel",
)

# 'rrdtool' prefix cannot be stripped from filegroup
# this is a workaround to be able to strip prefix
copy_directory(
    name = "rrdtool_bindings_workaround",
    src = "@rrdtool//:perl_bindings_gen_dir",
    out = "perl_bindings_dir",
    tags = ["manual"],
)

set_runpath_tree(
    name = "rrdtool_perl_bindings_runpath",
    src = ":rrdtool_bindings_workaround",
    rpath = "$ORIGIN",
    tags = ["manual"],
)

pkg_files(
    name = "rrdtool_perl_bindings_files",
    srcs = [":rrdtool_perl_bindings_runpath"],
    strip_prefix = strip_prefix.from_pkg("rrdtool_perl_bindings_runpath"),
    tags = ["manual"],
    visibility = ["//visibility:public"],
)

pkg_tar(
    name = "rrdtool_perl_bindings",
    srcs = ["rrdtool_perl_bindings_files"],
    stamp = 1,
    tags = ["manual"],
    visibility = ["//visibility:public"],
)

pkg_files(
    name = "rrdtool_skel",
    srcs = glob(
        ["skel/**/*"],
        exclude = [
            "**/.gitignore",
        ],
    ),
    strip_prefix = strip_prefix.from_pkg(""),
    tags = ["manual"],
    visibility = ["//omd:__pkg__"],
)

pkg_files(
    name = "rrdtool_rrdcached_skel",
    srcs = ["skel/etc/init.d/rrdcached"],
    strip_prefix = strip_prefix.from_pkg(""),
    tags = ["manual"],
    visibility = ["//omd:__pkg__"],
)

pkg_mklink(
    name = "20-rrdchached",
    link_name = "skel/etc/rc.d/20-rrdcached",
    tags = ["manual"],
    target = "../init.d/rrdcached",
)

pkg_mkdirs(
    name = "rrdtool_skel_folders",
    dirs = [
        "skel/etc/rrdcached.d",
        "skel/tmp/rrdcached",
        "skel/var/rrdcached",
    ],
    tags = ["manual"],
)

pkg_filegroup(
    name = "rrdtool_skel_pkg",
    srcs = [
        "20-rrdchached",
        "rrdtool_skel_folders",
        ":rrdtool_skel",
    ],
    tags = ["manual"],
)

pkg_tar(
    name = "rrdtool_skel_tar",
    srcs = [":rrdtool_skel_pkg"],
    stamp = 1,
    tags = ["manual"],
)

sh_library(
    name = "omd_packages_rrdtool_sh",
    srcs = [
        "skel/etc/init.d/rrdcached",
    ],
)
