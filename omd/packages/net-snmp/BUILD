load("@aspect_bazel_lib//lib:copy_to_directory.bzl", "copy_to_directory")
load("@aspect_bazel_lib//lib:directory_path.bzl", "directory_path")
load("@aspect_rules_py//py:defs.bzl", "py_binary")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_filegroup", "pkg_files", "pkg_mkdirs", "pkg_mklink")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("//bazel/rules:patchelf.bzl", "set_runpath", "set_runpath_tree")
load("//omd/packages/net-snmp:snmp-rules.bzl", "snmp_compile_mibs")

bin_paths = [
    "encode_keychange",
    "snmpbulkget",
    "snmpbulkwalk",
    "snmpdelta",
    "snmpdf",
    "snmpget",
    "snmpgetnext",
    "snmpnetstat",
    "snmppcap",
    "snmpping",
    "snmpps",
    "snmpset",
    "snmpstatus",
    "snmptable",
    "snmptest",
    "snmptranslate",
    "snmptrap",
    "snmpusm",
    "snmpvacm",
    "snmpwalk",
]

lib_shared_libs = [
    "libnetsnmp.so.40.1.0",
]

[filegroup(
    name = "bin_%s" % f,
    srcs = ["@net-snmp"],
    output_group = f,
    tags = ["manual"],
) for f in bin_paths]

set_runpath(
    name = "bin_runpath",
    srcs = [":bin_%s" % f for f in bin_paths],
    rpaths = ["$ORIGIN/../lib"],
    tags = ["manual"],
)

pkg_files(
    name = "bin_pkg",
    srcs = [":bin_runpath"],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "bin",
    tags = ["manual"],
)

[filegroup(
    name = "lib_%s" % f,
    srcs = ["@net-snmp"],
    output_group = f,
    tags = ["manual"],
) for f in lib_shared_libs]

set_runpath(
    name = "lib_runpath",
    srcs = [":lib_%s" % f for f in lib_shared_libs],
    rpaths = ["$ORIGIN"],
    tags = ["manual"],
)

pkg_files(
    name = "lib_shared_files",
    srcs = [":lib_runpath"],
    prefix = "lib",
    tags = ["manual"],
)

pkg_mklink(
    name = "libnetsnmp_so",
    link_name = "lib/libnetsnmp.so",
    tags = ["manual"],
    target = "libnetsnmp.so.40",
)

pkg_mklink(
    name = "libnetsnmp_so40",
    link_name = "lib/libnetsnmp.so.40",
    tags = ["manual"],
    target = "libnetsnmp.so.40.1.0",
)

pkg_filegroup(
    name = "lib_shared_pkg",
    srcs = [
        ":lib_shared_files",
        ":libnetsnmp_so",
        ":libnetsnmp_so40",
    ],
    tags = ["manual"],
)

filegroup(
    name = "libnetsnmp_a",
    srcs = ["@net-snmp"],
    output_group = "libnetsnmp.a",
    tags = ["manual"],
)

pkg_files(
    name = "lib_static_pkg",
    srcs = [":libnetsnmp_a"],
    prefix = "lib",
    tags = ["manual"],
)

filegroup(
    name = "gen_dir",
    srcs = ["@net-snmp"],
    output_group = "gen_dir",
    tags = ["manual"],
)

directory_path(
    name = "libnetsnmp_la",
    directory = ":gen_dir",
    path = "lib/libnetsnmp.la",
    tags = ["manual"],
)

directory_path(
    name = "lib_perl",
    directory = ":gen_dir",
    path = "lib/perl5",
    tags = ["manual"],
)

directory_path(
    name = "lib_python",
    directory = ":gen_dir",
    path = "lib/python3.13",
    tags = ["manual"],
)

directory_path(
    name = "share",
    directory = ":gen_dir",
    path = "share",
    tags = ["manual"],
)

copy_to_directory(
    name = "rest",
    srcs = [
        ":lib_perl",
        ":lib_python",
        ":libnetsnmp_la",
        ":share",
    ],
    include_external_repositories = ["**"],
    root_paths = ["**/net-snmp"],
    tags = ["manual"],
)

set_runpath_tree(
    name = "rest_runpath",
    src = ":rest",
    rpath = "$ORIGIN",
    tags = ["manual"],
)

pkg_files(
    name = "rest_pkg",
    srcs = [":rest_runpath"],
    strip_prefix = "rest_runpath",
    tags = ["manual"],
)

pkg_mkdirs(
    name = "skel",
    dirs = ["skel/local/share/snmp/mibs/"],
    tags = ["manual"],
)

py_binary(
    name = "compile_mibs",
    srcs = ["compile_mibs.py"],
    tags = ["manual"],
    deps = [
        requirement("pysmi"),
    ],
)

snmp_compile_mibs(
    name = "generate_python_mibs",
    compiler = ":compile_mibs",
    mibs = ["@net-snmp//:mibs"],
    tags = ["manual"],
)

pkg_tar(
    name = "net-snmp",
    srcs = [
        ":bin_pkg",
        ":generate_python_mibs",
        ":lib_shared_pkg",
        ":lib_static_pkg",
        ":rest_pkg",
        ":skel",
    ],
    stamp = 1,
    tags = ["manual"],
    visibility = ["//omd:__subpackages__"],
)
