load("@aspect_bazel_lib//lib:copy_file.bzl", "copy_file")
load("@aspect_bazel_lib//lib:directory_path.bzl", "directory_path")
load("@rules_pkg//pkg:mappings.bzl", "filter_directory", "pkg_attributes", "pkg_filegroup", "pkg_files", "pkg_mklink", "strip_prefix")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("//bazel/rules:patchelf.bzl", "set_runpath")

filegroup(
    name = "xmlsec1_gen_dir",
    srcs = ["@xmlsec1"],
    output_group = "gen_dir",
    tags = ["manual"],
)

# Binary
directory_path(
    name = "xmlsec1_bin_path",
    directory = ":xmlsec1_gen_dir",
    path = "bin/xmlsec1",
    tags = ["manual"],
)

copy_file(
    name = "xmlsec1_bin_copy",
    src = ":xmlsec1_bin_path",
    out = "bin/xmlsec1",
    tags = ["manual"],
)

set_runpath(
    name = "xmlsec1_deployable_bin",
    srcs = [":xmlsec1_bin_copy"],
    # RUNPATH here only resolves the binary's direct DT_NEEDED libs (libxmlsec1,
    # libltdl, libxml2, libxslt, libstdc++). The crypto backend (libxmlsec1-openssl)
    # is dlopen()ed by libltdl, which ignores RPATH/RUNPATH entirely -- that lookup
    # is handled by a source patch (see //omd/packages/xmlsec1/patches) which calls
    # lt_dladdsearchdir() with the libxmlsec1.so directory at runtime.
    rpaths = ["$ORIGIN/../lib"],
    tags = ["manual"],
)

# Required libraries
libs = [
    "libxmlsec1-openssl.so.1.3.8",
    "libxmlsec1.so.1.3.8",
]

lib_symlinks = {
    "libxmlsec1-openssl.so": "libxmlsec1-openssl.so.1.3.8",
    "libxmlsec1-openssl.so.1": "libxmlsec1-openssl.so.1.3.8",
    "libxmlsec1.so": "libxmlsec1.so.1.3.8",
    "libxmlsec1.so.1": "libxmlsec1.so.1.3.8",
}

[directory_path(
    name = "xmlsec1_lib_path_%s" % filename,
    directory = ":xmlsec1_gen_dir",
    path = "lib/%s" % filename,
    tags = ["manual"],
) for filename in libs]

[copy_file(
    name = "xmlsec1_lib_copy_%s" % filename,
    src = ":xmlsec1_lib_path_%s" % filename,
    out = filename,
    tags = ["manual"],
) for filename in libs]

set_runpath(
    name = "xmlsec1_deployable_lib",
    srcs = [":xmlsec1_lib_copy_%s" % f for f in libs],
    rpaths = ["$ORIGIN/../lib"],
    tags = ["manual"],
)

[pkg_mklink(
    name = "lib_symlink_%s" % name,
    link_name = "lib/" + name,
    tags = ["manual"],
    target = target,
) for name, target in lib_symlinks.items()]

# Optional libraries — backend availability varies by distro family:
#   gnutls: sles and deb-based distros
#   nss:    deb-based distros only
#   almalinux: neither backend is built
optional_libs = {
    "gnutls": "libxmlsec1-gnutls.so.1.3.8",
    "nss": "libxmlsec1-nss.so.1.3.8",
}

optional_lib_symlinks = {
    "libxmlsec1-gnutls.so": "libxmlsec1-gnutls.so.1.3.8",
    "libxmlsec1-gnutls.so.1": "libxmlsec1-gnutls.so.1.3.8",
    "libxmlsec1-nss.so": "libxmlsec1-nss.so.1.3.8",
    "libxmlsec1-nss.so.1": "libxmlsec1-nss.so.1.3.8",
}

[directory_path(
    name = "xmlsec1_lib_path_%s" % name,
    directory = ":xmlsec1_gen_dir",
    path = "lib/%s" % filename,
    tags = ["manual"],
) for name, filename in optional_libs.items()]

[copy_file(
    name = "xmlsec1_lib_copy_%s" % name,
    src = ":xmlsec1_lib_path_%s" % name,
    out = filename,
    tags = ["manual"],
) for name, filename in optional_libs.items()]

[set_runpath(
    name = "xmlsec1_deployable_lib_%s" % name,
    srcs = [":xmlsec1_lib_copy_%s" % name],
    rpaths = ["$ORIGIN/../lib"],
    tags = ["manual"],
) for name in optional_libs]

[pkg_mklink(
    name = "optional_lib_symlink_%s" % name,
    link_name = "lib/" + name,
    tags = ["manual"],
    target = target,
) for name, target in optional_lib_symlinks.items()]

# Precompute path/target lists used in select() expressions below
_gnutls_rest_paths = (
    ["lib/" + s for s in optional_lib_symlinks if "gnutls" in s] +
    ["lib/" + f for f in optional_libs.values() if "gnutls" in f]
)

_all_optional_rest_paths = (
    ["lib/" + s for s in optional_lib_symlinks] +
    ["lib/" + f for f in optional_libs.values()]
)

_gnutls_symlink_targets = [":optional_lib_symlink_%s" % s for s in optional_lib_symlinks if "gnutls" in s]

_all_optional_symlink_targets = [":optional_lib_symlink_%s" % s for s in optional_lib_symlinks]

# Packaging
filter_directory(
    name = "rest",
    src = ":xmlsec1_gen_dir",
    excludes = ["lib/" + file for file in libs + lib_symlinks.keys()] + [
        "bin/xmlsec1",
        "bin/xmlsec1-config",
        "share/aclocal/xmlsec1.m4",
    ] + select({
        "@cmk//distro:almalinux": [],
        "@cmk//distro:sles": _gnutls_rest_paths,
        "//conditions:default": _all_optional_rest_paths,
    }),
    tags = ["manual"],
)

pkg_files(
    name = "rest_files",
    srcs = [":rest"],
    strip_prefix = strip_prefix.from_pkg("rest"),
    tags = ["manual"],
)

pkg_files(
    name = "bin",
    srcs = [":xmlsec1_deployable_bin"],
    attributes = pkg_attributes(mode = "0755"),
    prefix = "bin/",
    tags = ["manual"],
)

pkg_files(
    name = "xmlsec1_libs_base",
    srcs = [":xmlsec1_deployable_lib"],
    prefix = "lib",
    tags = ["manual"],
)

pkg_files(
    name = "xmlsec1_optional_lib_files",
    srcs = select({
        "@cmk//distro:almalinux": [],
        "@cmk//distro:sles": [":xmlsec1_deployable_lib_gnutls"],
        "//conditions:default": [":xmlsec1_deployable_lib_%s" % name for name in optional_libs],
    }),
    prefix = "lib",
    tags = ["manual"],
)

pkg_filegroup(
    name = "xmlsec1_additional_libs",
    srcs = [":xmlsec1_optional_lib_files"] + select({
        "@cmk//distro:almalinux": [],
        "@cmk//distro:sles": _gnutls_symlink_targets,
        "//conditions:default": _all_optional_symlink_targets,
    }),
    tags = ["manual"],
)

pkg_tar(
    name = "xmlsec1",
    srcs = [
        ":bin",
        ":rest_files",
        ":xmlsec1_additional_libs",
        ":xmlsec1_libs_base",
    ] + [":lib_symlink_%s" % link for link in lib_symlinks],
    stamp = 1,
    tags = ["manual"],
    visibility = ["//omd:__pkg__"],
)
