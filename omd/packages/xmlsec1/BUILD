load("@bazel_skylib//lib:selects.bzl", "selects")
load("@rules_pkg//pkg:mappings.bzl", "filter_directory", "pkg_attributes", "pkg_filegroup", "pkg_files", "pkg_mklink", "strip_prefix")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("//bazel/rules:make_deployable.bzl", "make_deployable_file")

make_deployable_file(
    name = "xmlsec1_deployable_bin",
    src = "@xmlsec1//:gen_dir",
    out = "bin/xmlsec1",
    rpath = "\\$ORIGIN/../lib",
)

libs = [
    "libxmlsec1-openssl.so.1.3.0",
    "libxmlsec1.so.1.3.0",
]

lib_symlinks = {
    "libxmlsec1-openssl.so": "libxmlsec1-openssl.so.1.3.0",
    "libxmlsec1-openssl.so.1": "libxmlsec1-openssl.so.1.3.0",
    "libxmlsec1.so": "libxmlsec1.so.1.3.0",
    "libxmlsec1.so.1": "libxmlsec1.so.1.3.0",
}

[pkg_mklink(
    name = "lib_symlink_%s" % name,
    link_name = "lib/" + name,
    target = target,
) for name, target in lib_symlinks.items()]

[make_deployable_file(
    name = "xmlsec1_deployable_lib_%s" % filename,
    src = "@xmlsec1//:gen_dir",
    out = "lib/" + filename,
    rpath = "\\$ORIGIN/../lib",
) for filename in libs]

make_deployable_file(
    name = "xmlsec1_deployable_lib_gnutls",
    src = "@xmlsec1//:gen_dir",
    out = "lib/libxmlsec1-gnutls.so.1.3.0",
    rpath = "\\$ORIGIN/../lib",
)

make_deployable_file(
    name = "xmlsec1_deployable_lib_nss",
    src = "@xmlsec1//:gen_dir",
    out = "lib/libxmlsec1-nss.so.1.3.0",
    rpath = "\\$ORIGIN/../lib",
)

make_deployable_file(
    name = "xmlsec1_deployable_lib_gcrypt",
    src = "@xmlsec1//:gen_dir",
    out = "lib/libxmlsec1-gcrypt.so.1.3.0",
    rpath = "\\$ORIGIN/../lib",
)

pkg_mklink(
    name = "lib_symlink_gnutls",
    link_name = "lib/libxmlsec1-gnutls.so",
    target = "lib/libxmlsec1-gnutls.so.1.3.0",
)

pkg_mklink(
    name = "lib_symlink_nss",
    link_name = "lib/libxmlsec1-nss.so",
    target = "lib/libxmlsec1-nss.so.1.3.0",
)

pkg_mklink(
    name = "lib_symlink_nss1",
    link_name = "lib/libxmlsec1-nss.so.1",
    target = "lib/libxmlsec1-nss.so.1.3.0",
)

pkg_mklink(
    name = "lib_symlink_gcrypt",
    link_name = "lib/libxmlsec1-gcrypt.so",
    target = "lib/libxmlsec1-gcrypt.so.1.3.0",
)

pkg_mklink(
    name = "lib_symlink_gcrypt1",
    link_name = "lib/libxmlsec1-gcrypt.so.1",
    target = "lib/libxmlsec1-gcrypt.so.1.3.0",
)

filter_directory(
    name = "rest",
    src = "@xmlsec1//:gen_dir",
    excludes = ["lib/" + file for file in libs + lib_symlinks.keys()] + [
        "bin/xmlsec1",
        "bin/xmlsec1-config",
        "share/aclocal/xmlsec1.m4",
    ] + selects.with_or({
        "@//bazel/cmk/distro:almalinux-9": [],
        (
            "@//bazel/cmk/distro:almalinux-8",
            "@//bazel/cmk/distro:sles-15sp3",
            "@//bazel/cmk/distro:sles-15sp4",
            "@//bazel/cmk/distro:sles-15sp5",
            "@//bazel/cmk/distro:sles-15sp6",
        ): ["lib/libxmlsec1-gcrypt.so.1.3.0"],
        "//conditions:default": [
            "lib/libxmlsec1-gnutls.so.1.3.0",
            "lib/libxmlsec1-nss.so.1.3.0",
        ],
    }),
)

pkg_files(
    name = "rest_files",
    srcs = [
        ":rest",
    ],
    strip_prefix = strip_prefix.from_pkg("rest"),
)

pkg_filegroup(
    name = "rest_fg",
    srcs = [":rest_files"],
    prefix = "",
)

pkg_files(
    name = "bin",
    srcs = [
        ":xmlsec1_deployable_bin",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "bin/",
)

pkg_files(
    name = "xmlsec1_libs_base",
    srcs = ["xmlsec1_deployable_lib_%s" % f for f in libs],
    prefix = "lib",
)

pkg_files(
    name = "xmlsec1_additional_libs",
    srcs = selects.with_or({
        "@//bazel/cmk/distro:almalinux-9": [],
        (
            "@//bazel/cmk/distro:almalinux-8",
            "@//bazel/cmk/distro:sles-15sp3",
            "@//bazel/cmk/distro:sles-15sp4",
            "@//bazel/cmk/distro:sles-15sp5",
            "@//bazel/cmk/distro:sles-15sp6",
        ): [
            "lib_symlink_gcrypt",
            "lib_symlink_gcrypt1",
        ],
        "//conditions:default": [
            "lib_symlink_gcrypt",
            "lib_symlink_gcrypt1",
            "lib_symlink_gnutls",
            "lib_symlink_nss",
            "lib_symlink_nss1",
            "xmlsec1_deployable_lib_gnutls",
            "xmlsec1_deployable_lib_nss",
        ],
    }),
    prefix = "lib",
)

pkg_tar(
    name = "xmlsec1",
    srcs = [
        ":bin",
        ":rest_fg",
        ":xmlsec1_additional_libs",
        ":xmlsec1_libs_base",
    ] + [":lib_symlink_%s" % link for link in lib_symlinks],
    visibility = ["//omd:__pkg__"],
)
