load("@aspect_rules_py//py:defs.bzl", "py_binary")
load("@bazel_skylib//rules:run_binary.bzl", "run_binary")
load("@bazel_skylib//rules:write_file.bzl", "write_file")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("@rules_uv//uv:pip.bzl", "pip_compile")
load("@rules_uv//uv:venv.bzl", "create_venv")
load("//:bazel_variables.bzl", "edition_deps", "edition_skel_permissions")

exports_files([
    "requirements.txt",
])

pip_compile(
    name = "requirements_lock",
    requirements_in = ":requirements.txt",
    requirements_txt = ":requirements_lock.txt",
)

create_venv(
    name = "venv",
    destination_folder = "omd/.venv",
    requirements_txt = ":requirements_lock.txt",
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
        "//omd/packages/Python:python_tar",
        "//omd/packages/heirloom-pkgtools",
        "//omd/packages/net-snmp:net-snmp_tar",
        "//omd/packages/openssl:openssl_tar_" + edition,
        "//omd/packages/perl-modules",
        "//omd/packages/python3-modules:python3-modules.tar",
        "//omd/packages/rrdtool:rrdtool_perl_bindings",
        "//omd/packages/rrdtool:rrdtool_python_tar",
        "//omd/packages/rrdtool:rrdtool_tar",
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
        ":license_info",
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

write_file(
    name = "werks_utils",
    out = "werks_utils.py",
    content = [
        "import runpy",
        "runpy.run_module('cmk.werks.utils', run_name=('__main__'))",
    ],
)

py_binary(
    name = "werks_utils_binary",
    srcs = [":werks_utils.py"],
    deps = ["//packages/cmk-werks"],
)

[run_binary(
    name = "run_werks_precompile_" + edition,
    srcs = [
        # //.:werks warns for dependency checking of directories is unsound but
        # we only use it to get the path with $location
        # the real dependency is the //:werks_group filegroup
        "//:werks_group",
    ],
    outs = ["werks_precompiled_" + edition],
    args = [
        "precompile",
        "$(location //:werks_group)",
        "--filter-by-edition",
        edition,
        "$(location werks_precompiled_%s)" % edition,
    ],
    tool = ":werks_utils_binary",
) for edition in [
    "cre",
    "cce",
    "cee",
    "cme",
    "cse",
]]

[run_binary(
    name = "run_changelog_" + edition,
    srcs = ["werks_precompiled_" + edition],
    outs = ["changelog_" + edition],
    args = [
        "changelog",
        "$(location changelog_%s)" % edition,
        "$(location werks_precompiled_%s)" % edition,
    ],
    tool = ":werks_utils_binary",
) for edition in [
    "cre",
    "cce",
    "cee",
    "cme",
    "cse",
]]

py_binary(
    name = "generate_licenses_csv_py",
    srcs = ["license_sources/generate_licenses_csv.py"],
)

run_binary(
    name = "generate_licenses_csv",
    srcs = ["bill-of-materials.json"],
    outs = ["Licenses.csv"],
    args = [
        "--bom",
        "$(location bill-of-materials.json)",
        "--out",
        "$(location Licenses.csv)",
    ],
    tool = ":generate_licenses_csv_py",
)

filegroup(
    name = "license_texts",
    srcs = glob([
        "license_sources/license_texts/*.txt",
    ]),
)

py_binary(
    name = "build_license_texts_pdf_py",
    srcs = ["license_sources/build_license_texts_pdf.py"],
    data = [
        "license_sources/Calibri.ttf",
        "license_sources/checkmk_logo.svg",
        ":license_texts",
    ],
    deps = [
        requirement("reportlab"),
        requirement("svglib"),
    ],
)

run_binary(
    name = "build_license_texts_pdf",
    srcs = [":generate_licenses_csv"],
    outs = ["License_texts.pdf"],
    args = [
        "--pdf",
        "$(location License_texts.pdf)",
        "--csv",
        "$(location :generate_licenses_csv)",
    ],
    tool = ":build_license_texts_pdf_py",
)

pkg_tar(
    name = "license_info",
    srcs = [
        "bill-of-materials.json",
        ":build_license_texts_pdf",
        ":generate_licenses_csv",
    ],
    package_dir = "share/doc/",
    package_file_name = "license_info_archive.tar",
)
