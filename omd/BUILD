load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

pkg_tar(
    name = "intermediate_install",
    srcs = [
        "//omd/packages/Python:python_files_with_prefix_pkg",
        "//omd/packages/openssl:openssl_files_with_prefix_pkg",
        "//omd/packages/protobuf",
        "//omd/packages/rrdtool:rrdtool_perl_bindings_files",
        "//omd/packages/rrdtool:rrdtool_with_prefix_pkg",
    ],
    extension = "tar.gz",
    visibility = ["//visibility:public"],
    deps = [
        "//omd/packages/perl-modules:perl-modules.tar",
        "//omd/packages/python3-modules:python3-modules.tar",
        "//omd/packages/rrdtool:rrdtool_python_tar",
        "//packages/cmk-agent-based:pkg_tar",
        "//packages/cmk-agent-receiver:pkg_tar",
        "//packages/cmk-ccc:pkg_tar",
        "//packages/cmk-crypto:pkg_tar",
        "//packages/cmk-graphing:pkg_tar",
        "//packages/cmk-livestatus-client:cmk_livestatus_client_pkg_tar",
        "//packages/cmk-livestatus-client:cmk_livestatus_pkg_tar",
        "//packages/cmk-messaging:pkg_tar",
        "//packages/cmk-mkp-tool:pkg_tar",
        "//packages/cmk-rulesets:pkg_tar",
        "//packages/cmk-server-side-calls:pkg_tar",
        "//packages/cmk-trace:pkg_tar",
        "//packages/cmk-werks:pkg_tar",
    ],
)

srcs = {
    "cre": [],
    "cce": ["//cmk:python_proto_pkg"],
    "cee": ["//cmk:python_proto_pkg"],
    "cme": ["//cmk:python_proto_pkg"],
    "cse": ["//cmk:python_proto_pkg"],
}

[pkg_tar(
    name = "deps_install_" + edition,
    srcs = [
        "//omd/packages/freetds:freetds_pkg",
        "//omd/packages/net-snmp:net-snmp_files_pkg",
    ] + srcs[edition],
    extension = "tar.gz",
) for edition in [
    "cre",
    "cce",
    "cee",
    "cme",
    "cse",
]]
