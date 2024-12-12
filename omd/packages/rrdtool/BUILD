load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_filegroup", "pkg_files", "pkg_mkdirs", "pkg_mklink", "strip_prefix")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("//bazel/rules:exclude_from_filegroup.bzl", "exclude_from_filegroup")
load("//bazel/rules:package_wheel.bzl", "package_wheel")

pkg_files(
    name = "rrdtool_bin",
    srcs = [
        "@rrdtool_native//:rrdcached",
        "@rrdtool_native//:rrdtool",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "bin",
)

pkg_filegroup(
    name = "rrdtool_pkg",
    srcs = [
        ":rrdtool_bin",
        ":rrdtool_skel_pkg",
    ],
    visibility = ["//visibility:public"],
)

pkg_tar(
    name = "rrdtool_tar",
    srcs = [":rrdtool_pkg"],
    package_file_name = "rrdtool.tar",
    visibility = ["//visibility:public"],
)

package_wheel(
    name = "rrdtool_python_tar",
    visibility = ["//visibility:public"],
    whl = "@rrdtool_native//:rrdtool_python_wheel",
)

# 'rrdtool' prefix cannot be stripped from filegroup
# this is a workaround to be able to strip prefix
exclude_from_filegroup(
    name = "rrdtool_bindings_workaround",
    src = "@rrdtool//:perl_bindings_gen_dir",
    excludes = ["noting_to_exclude"],
)

pkg_files(
    name = "rrdtool_perl_bindings_files",
    srcs = [":rrdtool_bindings_workaround"],
    strip_prefix = strip_prefix.from_pkg("rest"),
    visibility = ["//visibility:public"],
)

pkg_tar(
    name = "rrdtool_perl_bindings",
    srcs = ["rrdtool_perl_bindings_files"],
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
    visibility = ["//omd:__pkg__"],
)

pkg_files(
    name = "rrdtool_rrdcached_skel",
    srcs = ["skel/etc/init.d/rrdcached"],
    strip_prefix = strip_prefix.from_pkg(""),
    visibility = ["//omd:__pkg__"],
)

pkg_mklink(
    name = "20-rrdchached",
    link_name = "skel/etc/rc.d/20-rrdcached",
    target = "../init.d/rrdcached",
)

pkg_mkdirs(
    name = "rrdtool_skel_folders",
    dirs = [
        "skel/etc/rrdcached.d",
        "skel/tmp/rrdcached",
        "skel/var/rrdcached",
    ],
)

pkg_filegroup(
    name = "rrdtool_skel_pkg",
    srcs = [
        "20-rrdchached",
        "rrdtool_skel_folders",
        ":rrdtool_skel",
    ],
)

pkg_tar(
    name = "rrdtool_skel_tar",
    srcs = [":rrdtool_skel_pkg"],
)
