load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_filegroup", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("//bazel/rules:exclude_from_filegroup.bzl", "exclude_from_filegroup")
load("//bazel/rules:make_deployable.bzl", "make_deployable_file")

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
    excludes = bin_paths,
)

pkg_files(
    name = "net-snmp_rest_pkg",
    srcs = [
        ":net-snmp_rest",
    ],
    strip_prefix = "rest",
)

pkg_filegroup(
    name = "net-snmp_files_pkg",
    srcs = [
        ":net-snmp_bin_pkg",
        ":net-snmp_rest_pkg",
    ],
    visibility = ["//visibility:public"],
)

pkg_tar(
    name = "net-snmp_tar",
    srcs = [":net-snmp_files_pkg"],
    package_file_name = "net-snmp.tar",
    visibility = ["//visibility:public"],
)

# only necessary for intermediate install
# can be removed once that is obsolete
pkg_filegroup(
    name = "net-snmp_files_with_prefix_pkg",
    srcs = [
        ":net-snmp_bin_pkg",
        ":net-snmp_rest_pkg",
    ],
    prefix = "net-snmp",
    visibility = ["//visibility:public"],
)

pkg_tar(
    name = "net-snmp_with_prefix_tar",
    srcs = [":net-snmp_files_with_prefix_pkg"],
    package_file_name = "net-snmp_with_prefix.tar",
    visibility = ["//visibility:public"],
)
