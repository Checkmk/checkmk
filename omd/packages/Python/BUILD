load("@rules_pkg//pkg:mappings.bzl", "filter_directory", "pkg_attributes", "pkg_filegroup", "pkg_files", "pkg_mklink")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("@omd_packages//:package_versions.bzl", "PYTHON_VERSION")
load("@omd_packages//omd/packages/Python:version.bzl", "PYTHON_MAJOR_DOT_MINOR", "PYTHON_VERSION_MAJOR")
load(":make_deployable.bzl", "make_deployable")

exports_files([
    "sitecustomize.py",
    "pip",
])

bin_paths = [
    "bin/2to3-%s" % PYTHON_MAJOR_DOT_MINOR,
    "bin/idle%s" % PYTHON_MAJOR_DOT_MINOR,
    "bin/pip%s" % PYTHON_MAJOR_DOT_MINOR,
    "bin/pydoc%s" % PYTHON_MAJOR_DOT_MINOR,
    "bin/python%s" % PYTHON_MAJOR_DOT_MINOR,
    "bin/python%s-config" % PYTHON_MAJOR_DOT_MINOR,
]

# target_name -> target
bin_symlinks = [
    (
        "python",
        "python%s" % PYTHON_VERSION_MAJOR,
    ),
    (
        "python%s" % PYTHON_VERSION_MAJOR,
        "python%s" % PYTHON_MAJOR_DOT_MINOR,
    ),
    (
        "pip%s" % PYTHON_VERSION_MAJOR,
        "pip%s" % PYTHON_MAJOR_DOT_MINOR,
    ),
    (
        "2to3",
        "2to3-%s" % PYTHON_MAJOR_DOT_MINOR,
    ),
    (
        "idle%s" % PYTHON_VERSION_MAJOR,
        "idle%s" % PYTHON_MAJOR_DOT_MINOR,
    ),
    (
        "pydoc%s" % PYTHON_VERSION_MAJOR,
        "pydoc%s" % PYTHON_MAJOR_DOT_MINOR,
    ),
    (
        "python%s-config" % PYTHON_VERSION_MAJOR,
        "python%s-config" % PYTHON_MAJOR_DOT_MINOR,
    ),
]

lib_symlinks = [
    (
        "libpython%s.so" % PYTHON_MAJOR_DOT_MINOR,
        "libpython%s.so.1.0" % PYTHON_MAJOR_DOT_MINOR,
    ),
    (
        "libpython%s.so" % PYTHON_VERSION_MAJOR,
        "libpython%s.so.1.0" % PYTHON_MAJOR_DOT_MINOR,
    ),
]

# lib/pkgconfig
pkgconfig_symlinks = [
    (
        "python%s-embed.pc" % PYTHON_VERSION_MAJOR,
        "python-%s-embed.pc" % PYTHON_MAJOR_DOT_MINOR,
    ),
    (
        "python%s.pc" % PYTHON_VERSION_MAJOR,
        "python-%s.pc" % PYTHON_MAJOR_DOT_MINOR,
    ),
]

# share/man/man1/
share_symlinks = [
    (
        "python%s.1" % PYTHON_VERSION_MAJOR,
        "python%s.1" % PYTHON_MAJOR_DOT_MINOR,
    ),
]

symlinks = bin_symlinks + lib_symlinks + pkgconfig_symlinks + share_symlinks

# Deployable means binaries are modified to be pacakged.
genrule(
    name = "python_bin_deployable",
    srcs = ["@python//:gen_dir"],
    outs = bin_paths,
    cmd = """
        BIN=$$(find $(location @python//:gen_dir) -name bin)
        rsync -r -L --chmod='u+w' $$BIN $$(realpath $(RULEDIR))

        # set RPATH for all ELF binaries we find
        file -L $(OUTS) \\
            | grep ELF | cut -d ':' -f1 \\
            | xargs patchelf --force-rpath --set-rpath "\\$$ORIGIN/../lib"
    """,
)

pkg_files(
    name = "python_bin_pkg",
    srcs = [
        ":python_bin_deployable",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "bin",
)

make_deployable(
    name = "python_lib_dynload_deployable",
    src = "@python//:gen_dir",
    input_dir = "lib/python%s/lib-dynload" % PYTHON_MAJOR_DOT_MINOR,
    rpath = "\\$ORIGIN/../..",
)

pkg_files(
    name = "python_lib_dynload_pkg",
    srcs = [":python_lib_dynload_deployable"],
    attributes = pkg_attributes(
        mode = "0755",
    ),
)

#pkg_mklink(name, link_name, target, attributes, src, kwargs)
[pkg_mklink(
    name = link_name,
    link_name = link_name,
    target = target,
) for link_name, target in symlinks]

pkg_filegroup(
    name = "python_bin_symlinks_pkg",
    srcs = [
        ":%s" % link_name
        for link_name, target in bin_symlinks
    ],
    prefix = "bin",
)

pkg_filegroup(
    name = "python_lib_symlinks_pkg",
    srcs = [
        ":%s" % link_name
        for link_name, target in lib_symlinks
    ],
    prefix = "lib",
)

pkg_filegroup(
    name = "python_pkgconfig_symlinks_pkg",
    srcs = [
        ":%s" % link_name
        for link_name, target in pkgconfig_symlinks
    ],
    prefix = "lib/pkgconfig",
)

pkg_filegroup(
    name = "python_share_symlinks_pkg",
    srcs = [
        ":%s" % link_name
        for link_name, target in share_symlinks
    ],
    prefix = "share/man/man1",
)

# List all files that are explicitly referenced somewhere else
# in the exclude section, for example binaries, symlinks and
# lib-dynloaod
# Resons for referencing explicitly are permissons other than 0644,
# the RPATH needs patching, symlinking.
filter_directory(
    name = "python_filtered",
    src = "@python//:gen_dir",
    excludes = bin_paths +
               ["bin/%s" % i[0] for i in bin_symlinks] +
               ["lib/%s" % i[0] for i in lib_symlinks] +
               ["lib/pkgconfig/%s" % i[0] for i in pkgconfig_symlinks] +
               ["share/man/man1/%s" % i[0] for i in share_symlinks],
)

# This target should contain all files that are not referenced
# explicitly somewhere else (see filter).
pkg_files(
    name = "python_rest_pkg",
    srcs = [
        ":python_filtered",
    ],
    strip_prefix = "python_filtered",
)

pkg_filegroup(
    name = "python_files_pkg",
    srcs = [
        ":python_bin_pkg",
        ":python_bin_symlinks_pkg",
        ":python_lib_dynload_pkg",
        ":python_lib_symlinks_pkg",
        ":python_pkgconfig_symlinks_pkg",
        ":python_rest_pkg",
        ":python_share_symlinks_pkg",
    ],
    visibility = ["//visibility:public"],
)

pkg_tar(
    name = "python_tar",
    srcs = [":python_files_pkg"],
    package_file_name = "python.tar",
    visibility = ["//visibility:public"],
)

# only necessary for intermediate install
# can be removed once that is obsolete
pkg_filegroup(
    name = "python_files_with_prefix_pkg",
    srcs = [
        ":python_bin_pkg",
        ":python_bin_symlinks_pkg",
        ":python_lib_dynload_pkg",
        ":python_lib_symlinks_pkg",
        ":python_pkgconfig_symlinks_pkg",
        ":python_rest_pkg",
        ":python_share_symlinks_pkg",
    ],
    prefix = "Python-%s" % PYTHON_VERSION,
    visibility = ["//visibility:public"],
)

pkg_tar(
    name = "python_tar_with_prefix",
    srcs = [":python_files_with_prefix_pkg"],
    package_file_name = "python.tar",
    visibility = ["//visibility:public"],
)
