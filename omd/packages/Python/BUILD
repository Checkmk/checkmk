load("@aspect_bazel_lib//lib:copy_file.bzl", "copy_file")
load("@aspect_bazel_lib//lib:copy_to_directory.bzl", "copy_to_directory")
load("@aspect_bazel_lib//lib:directory_path.bzl", "directory_path")
load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_filegroup", "pkg_files", "pkg_mklink", "strip_prefix")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("//bazel/rules:make_deployable.bzl", "string_replace")
load("//bazel/rules:patchelf.bzl", "set_runpath", "set_runpath_tree")
load("//omd/packages/Python:version.bzl", "PYTHON_MAJOR_DOT_MINOR", "PYTHON_VERSION_MAJOR")

exports_files([
    "sitecustomize.py",
    "pip",
])

bin_paths = [
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

filegroup(
    name = "python_gen_dir",
    srcs = ["@python"],
    output_group = "gen_dir",
    tags = ["manual"],
)

[directory_path(
    name = "python_bin_path_%s" % f.replace("/", "_").replace(".", "_"),
    directory = ":python_gen_dir",
    path = f,
    tags = ["manual"],
) for f in bin_paths]

[copy_file(
    name = "python_bin_copy_%s" % f.replace("/", "_").replace(".", "_"),
    src = ":python_bin_path_%s" % f.replace("/", "_").replace(".", "_"),
    out = f.split("/")[-1],
    tags = ["manual"],
) for f in bin_paths]

elf_bin_paths = [
    "bin/python%s" % PYTHON_MAJOR_DOT_MINOR,
]

script_bin_paths = [f for f in bin_paths if f not in elf_bin_paths]

set_runpath(
    name = "python_bin_deployable",
    srcs = [":python_bin_copy_%s" % f.replace("/", "_").replace(".", "_") for f in elf_bin_paths],
    rpaths = ["$ORIGIN/../lib"],
    tags = ["manual"],
)

pkg_files(
    name = "python_bin_pkg",
    srcs = [
        ":python_bin_deployable",
    ] + [":python_bin_copy_%s" % f.replace("/", "_").replace(".", "_") for f in script_bin_paths],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "bin",
    tags = ["manual"],
)

directory_path(
    name = "python_lib_dynload_path",
    directory = ":python_gen_dir",
    path = "lib/python%s/lib-dynload" % PYTHON_MAJOR_DOT_MINOR,
    tags = ["manual"],
)

copy_to_directory(
    name = "python_lib_dynload_copy",
    srcs = [":python_lib_dynload_path"],
    include_external_repositories = ["**"],
    root_paths = ["**/lib-dynload"],
    tags = ["manual"],
)

set_runpath_tree(
    name = "python_lib_dynload_deployable",
    src = ":python_lib_dynload_copy",
    rpath = "$ORIGIN/../..",
    tags = ["manual"],
)

pkg_files(
    name = "python_lib_dynload_pkg",
    srcs = [":python_lib_dynload_deployable"],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "lib/python%s/lib-dynload" % PYTHON_MAJOR_DOT_MINOR,
    strip_prefix = "python_lib_dynload_deployable",
    tags = ["manual"],
)

[pkg_mklink(
    name = link_name,
    link_name = link_name,
    tags = ["manual"],
    target = target,
) for link_name, target in symlinks]

pkg_filegroup(
    name = "python_bin_symlinks_pkg",
    srcs = [
        ":%s" % link_name
        for link_name, _ in bin_symlinks
    ],
    prefix = "bin",
    tags = ["manual"],
)

pkg_filegroup(
    name = "python_lib_symlinks_pkg",
    srcs = [
        ":%s" % link_name
        for link_name, _ in lib_symlinks
    ],
    prefix = "lib",
    tags = ["manual"],
)

pkg_filegroup(
    name = "python_pkgconfig_symlinks_pkg",
    srcs = [
        ":%s" % link_name
        for link_name, _ in pkgconfig_symlinks
    ],
    prefix = "lib/pkgconfig",
    tags = ["manual"],
)

pkg_filegroup(
    name = "python_share_symlinks_pkg",
    srcs = [
        ":%s" % link_name
        for link_name, _ in share_symlinks
    ],
    prefix = "share/man/man1",
    tags = ["manual"],
)

# List all files that are explicitly referenced somewhere else
# in the exclude section, for example binaries, symlinks and
# lib-dynloaod
# Resons for referencing explicitly are permissons other than 0644,
# the RPATH needs patching, symlinking.
# This target should contain all files that are not referenced
# explicitly somewhere else.
copy_to_directory(
    name = "python_rest",
    srcs = ["@python"],
    exclude_srcs_patterns =
        ["lib/python%s/lib-dynload/**" % PYTHON_MAJOR_DOT_MINOR] +
        ["lib/%s" % i[0] for i in lib_symlinks] +
        ["lib/pkgconfig/%s" % i[0] for i in pkgconfig_symlinks] +
        ["share/man/man1/%s" % i[0] for i in share_symlinks],
    include_external_repositories = ["**"],
    include_srcs_patterns = [
        "include/**",
        "lib/**",
        "share/**",
    ],
    root_paths = ["python"],
    tags = ["manual"],
)

string_replace(
    name = "python_rest_with_version",
    src = ":python_rest",
    filepattern = ["_sysconfigdata__linux_x86_64-linux-gnu.py"],
    replace_labels = {
        "cmk_version": "@cmk//version",
        "cmk_edition": "@cmk//edition",
    },
    replace_pattern = "/replace-me",
    tags = ["manual"],
    value = "/opt/omd/versions/{cmk_version}.{cmk_edition}",
)

pkg_files(
    name = "python_rest_pkg",
    srcs = [
        ":python_rest_with_version",
    ],
    strip_prefix = strip_prefix.from_pkg("python_rest_with_version"),
    tags = ["manual"],
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
    tags = ["manual"],
    visibility = ["//visibility:public"],
)

pkg_tar(
    name = "python_tar",
    srcs = [":python_files_pkg"],
    package_file_name = "python.tar",
    stamp = 1,
    tags = ["manual"],
    visibility = ["//visibility:public"],
)
