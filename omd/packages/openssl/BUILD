load("@aspect_rules_py//py:defs.bzl", "py_binary")
load("@bazel_skylib//rules:write_file.bzl", "write_file")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_pkg//pkg:mappings.bzl", "filter_directory", "pkg_attributes", "pkg_filegroup", "pkg_files", "pkg_mkdirs", "pkg_mklink", "strip_prefix")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("//bazel/rules:binreplace_version_from_flag.bzl", "binreplace_version_from_flag")
load("//bazel/rules:patchelf.bzl", "set_runpath")

exports_files(["skel.permissions"])

bin_elf_paths = [
    "bin/openssl",
]

bin_noelf_paths = [
    "bin/c_rehash",
]

bin_paths = bin_elf_paths + bin_noelf_paths

lib_symlinks = [
    ("libcrypto.so", "libcrypto.so.3"),
    ("libssl.so", "libssl.so.3"),
]

# skel/etc/ssl/misc/
skel_symlinks = [
    ("tsget", "tsget.pl"),
]

symlinks = lib_symlinks + skel_symlinks

executable_paths = [
    "skel/etc/ssl/misc/CA.pl",
    "skel/etc/ssl/misc/tsget.pl",
]

lib_paths = [
    "lib/libssl.so.3",
    "lib/libcrypto.so.3",
]

genrule(
    name = "openssl_files",
    srcs = ["@openssl//:gen_dir"],
    outs = bin_paths + lib_paths,
    cmd = """
        for F in $(OUTS); do
            cp -L $(location @openssl//:gen_dir)/$${F#$(RULEDIR)/} $$F
        done
        chmod u+w $(OUTS)
    """,
    tags = ["manual"],
)

set_runpath(
    name = "openssl_bin_runpath",
    srcs = bin_elf_paths,
    rpaths = ["$ORIGIN/../lib"],
    tags = ["manual"],
)

set_runpath(
    name = "openssl_libssl_runpath",
    srcs = ["lib/libssl.so.3"],
    rpaths = ["$ORIGIN"],
    tags = ["manual"],
)

genrule(
    name = "openssl_executables_deployable",
    srcs = ["@openssl//:gen_dir"],
    outs = executable_paths,
    cmd = """
        for F in $(OUTS); do
            cp -L $(location @openssl//:gen_dir)/$${F#$(RULEDIR)/} $$F
        done
    """,
    tags = ["manual"],
)

pkg_files(
    name = "openssl_bin_pkg",
    srcs = [":openssl_bin_runpath"] + bin_noelf_paths,
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "bin",
    tags = ["manual"],
)

write_file(
    name = "binreplace",
    out = "binreplace.py",
    content = [
        "import runpy",
        "runpy.run_module('cmk_dev.binreplace', run_name=('__main__'))",
    ],
    tags = ["manual"],
)

py_binary(
    name = "binreplace_binary",
    srcs = [":binreplace.py"],
    tags = ["manual"],
    deps = [
        requirement("checkmk-dev-tools"),
    ],
)

binreplace_version_from_flag(
    name = "run_binreplace",
    src = ":lib/libcrypto.so.3",
    # File has to be called .replaced because this produce in this format by binreplace
    out = "lib/libcrypto.so.3.replaced",
    reg_ex = r"/(?:home|root)/.*?/openssl\.build_tmpdir/openssl/",
    replace_labels = {
        "version": "@cmk//version",
        "edition": "@cmk//edition",
    },
    tags = ["manual"],
    template = "/omd/versions/{version}.{edition}/",
    tool = ":binreplace_binary",
)

set_runpath(
    name = "openssl_libcrypto_runpath",
    srcs = ["lib/libcrypto.so.3.replaced"],
    rpaths = ["$ORIGIN"],
    tags = ["manual"],
)

pkg_files(
    name = "openssl_lib_pkg",
    srcs = [
        ":openssl_libcrypto_runpath",
        ":openssl_libssl_runpath",
    ],
    prefix = "lib",
    renames = {":openssl_libcrypto_runpath": "libcrypto.so.3"},
    tags = ["manual"],
)

[pkg_mklink(
    name = link_name,
    link_name = link_name,
    tags = ["manual"],
    target = target,
) for link_name, target in symlinks]

pkg_filegroup(
    name = "openssl_lib_symlinks_pkg",
    srcs = [
        ":%s" % link_name
        for link_name, target in lib_symlinks
    ],
    prefix = "lib",
    tags = ["manual"],
)

pkg_filegroup(
    name = "openssl_skel_symlinks_pkg",
    srcs = [
        ":%s" % link_name
        for link_name, target in skel_symlinks
    ],
    prefix = "skel/etc/ssl/misc",
    tags = ["manual"],
)

# empty dir:
pkg_mkdirs(
    name = "openssl_empty_dirs",
    dirs = [
        "lib/engines-3",
        "lib/ossl-modules",
        "skel/etc/ssl/certs",
        "skel/etc/ssl/private",
    ],
    tags = ["manual"],
)

pkg_files(
    name = "openssl_executables_pkg",
    srcs = [
        ":openssl_executables_deployable",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    strip_prefix = strip_prefix.from_pkg(""),
    tags = ["manual"],
)

filter_directory(
    name = "openssl_filtered",
    src = "@openssl//:gen_dir",
    excludes = bin_paths + lib_paths +
               ["lib/%s" % i[0] for i in lib_symlinks] +
               ["skel/etc/ssl/misc/%s" % i[0] for i in skel_symlinks] +
               executable_paths,
    tags = ["manual"],
)

# This target should contain all files that are not referenced
# explicitly somewhere else (see filter).
pkg_files(
    name = "openssl_rest_pkg",
    srcs = [
        ":openssl_filtered",
    ],
    strip_prefix = "openssl_filtered",
    tags = ["manual"],
)

pkg_filegroup(
    name = "openssl_files_pkg",
    srcs = [
        ":openssl_bin_pkg",
        ":openssl_empty_dirs",
        ":openssl_executables_pkg",
        ":openssl_lib_pkg",
        ":openssl_lib_symlinks_pkg",
        ":openssl_rest_pkg",
        ":openssl_skel_symlinks_pkg",
    ],
    tags = ["manual"],
    visibility = ["//visibility:public"],
)

pkg_tar(
    name = "openssl_tar",
    srcs = [":openssl_files_pkg"],
    mtime = 1767744000,
    portable_mtime = False,
    tags = ["manual"],
    visibility = ["//visibility:public"],
)
