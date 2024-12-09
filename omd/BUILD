load("@bazel_skylib//rules:write_file.bzl", "write_file")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("//:bazel_variables.bzl", "edition_deps", "edition_skel_permissions")

pkg_tar(
    name = "intermediate_install",
    srcs = [
        "//omd/packages/Python:python_files_with_prefix_pkg",
        "//omd/packages/openssl:openssl_files_with_prefix_pkg",
    ],
    extension = "tar.gz",
    visibility = ["//visibility:public"],
    deps = [
        "//omd/packages/python3-modules:python3-modules.tar",
        "//omd/packages/rrdtool:rrdtool_python_tar",
        "//packages/cmk-agent-based:pkg_tar",
        "//packages/cmk-agent-receiver:pkg_tar",
        "//packages/cmk-ccc:pkg_tar",
        "//packages/cmk-crypto:pkg_tar",
        "//packages/cmk-events:pkg_tar",
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

[pkg_tar(
    name = "deps_install_" + edition,
    srcs = [
        "//omd/packages/freetds:freetds_pkg",
        "//omd/packages/protobuf",
        "//packages/site/check-http:check_http_pkg",
    ],
    extension = "tar.gz",
    deps = [
        #added here instead of above because of disappearing file
        "//omd/packages/perl-modules",
        "//omd/packages/rrdtool:rrdtool_tar",
        "//omd/packages/net-snmp:net-snmp_tar",
        "//omd/packages/rrdtool:rrdtool_perl_bindings",
        "//omd/packages/rrdtool:rrdtool_python_tar",
    ] + edition_deps[edition],
) for edition in [
    "cre",
    "cce",
    "cee",
    "cme",
    "cse",
]]

[genrule(
    name = "skel_permissions_" + edition,
    srcs = edition_skel_permissions[edition],
    outs = ["skel.permissions_" + edition],
    cmd = "cat $< > $@",
) for edition in [
    "cce",
    "cee",
    "cme",
    "cse",
]]

# Placeholder since we have no cre specfic skel.permissions so far (will come soon)
write_file(
    name = "skel_permissions_cre",
    out = "skel.permissions_cre",
    content = [],
)
