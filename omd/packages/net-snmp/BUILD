load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_filegroup", "pkg_files", "pkg_mkdirs")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("//bazel/rules:exclude_from_filegroup.bzl", "exclude_from_filegroup")
load("//bazel/rules:make_deployable.bzl", "make_deployable_dir", "make_deployable_file")

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

[make_deployable_file(
    name = "net-snmp_deployable_%s" % filename,
    src = "@net-snmp//:gen_dir",
    out = "bin/%s" % filename,
    rpath = "\\$ORIGIN/../lib",
) for filename in bin_paths]

make_deployable_dir(
    name = "net-snmp_deployable_lib",
    src = "@net-snmp//:gen_dir",
    input_dir = "lib",
    rpath = "\\$ORIGIN/../lib",
)

pkg_files(
    name = "net-snmp_bin_pkg",
    srcs = ["net-snmp_deployable_%s" % f for f in bin_paths],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "bin",
)

exclude_from_filegroup(
    name = "net-snmp_rest",
    src = "@net-snmp//:gen_dir",
    excludes = bin_paths + ["lib/*"],
)

pkg_files(
    name = "net-snmp_rest_pkg",
    srcs = [
        ":net-snmp_rest",
    ],
    strip_prefix = "rest",
)

pkg_files(
    name = "net-snmp_deployable_lib_pkg",
    srcs = [
        ":net-snmp_deployable_lib",
    ],
)

pkg_mkdirs(
    name = "net-snmp_skel",
    dirs = ["skel/local/share/snmp/mibs/"],
)

pkg_filegroup(
    name = "net-snmp_files_pkg",
    srcs = [
        ":net-snmp_bin_pkg",
        ":net-snmp_deployable_lib_pkg",
        ":net-snmp_rest_pkg",
        ":net-snmp_skel",
    ],
    visibility = ["//visibility:public"],
)

pkg_tar(
    name = "net-snmp_tar",
    srcs = [":net-snmp_files_pkg"],
    package_file_name = "net-snmp.tar",
    visibility = ["//visibility:public"],
)
