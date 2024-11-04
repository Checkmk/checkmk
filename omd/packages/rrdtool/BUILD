load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_filegroup", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("@omd_packages//omd/packages/rules:package_wheel.bzl", "package_wheel")

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

# only necessary for intermediate install
# can be removed once that is obsolete
pkg_filegroup(
    name = "rrdtool_with_prefix_pkg",
    srcs = [
        ":rrdtool_bin",
    ],
    prefix = "rrdtool",
    visibility = ["//visibility:public"],
)

pkg_tar(
    name = "rrdtool_with_prefix_tar",
    srcs = [":rrdtool_with_prefix_pkg"],
    package_file_name = "rrdtool_with_prefix.tar",
    visibility = ["//visibility:public"],
)

package_wheel(
    name = "rrdtool_python_tar",
    visibility = ["//visibility:public"],
    whl = "@rrdtool_native//:rrdtool_python_wheel",
)

pkg_files(
    name = "rrdtool_perl_findings_files",
    srcs = ["@rrdtool//:perl_bindings_gen_dir"],
    visibility = ["//visibility:public"],
)

pkg_filegroup(
    name = "rrdtool_perl_findings_pkg",
    srcs = ["@rrdtool//:perl_bindings_gen_dir"],
    visibility = ["//visibility:public"],
)

pkg_tar(
    name = "rrdtool_perl_bindings",
    srcs = ["rrdtool_perl_findings_files"],
    visibility = ["//visibility:public"],
)
