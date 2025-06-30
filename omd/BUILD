load("@aspect_rules_py//py:defs.bzl", "py_binary")
load("@bazel_skylib//rules:run_binary.bzl", "run_binary")
load("@bazel_skylib//rules:write_file.bzl", "write_file")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("@rules_uv//uv:pip.bzl", "pip_compile")
load("@rules_uv//uv:venv.bzl", "create_venv")
load("//:bazel_variables.bzl", "edition_deps", "edition_skel_permissions")
load("//bazel/rules:file_from_flag.bzl", "file_from_flag")

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

file_from_flag(
    name = "omd_root_dir",
    out = "omd_root_dir.txt",
    content = [
        "/opt/omd/versions/{cmk_version}.{cmk_edition}",
        "",
    ],
    replace_labels = {
        "cmk_version": "//bazel/cmk/version",
        "cmk_edition": "//bazel/cmk/edition",
    },
)

[pkg_tar(
    name = "deps_install_" + edition,
    srcs = [
        "//omd/packages/freetds:freetds_pkg",
        "//omd/packages/protobuf",
        "//packages/check-http:check_http_pkg",
    ],
    extension = "tar.xz",
    package_dir_file = ":omd_root_dir",
    deps = [
               #added here instead of above because of disappearing file
               "//omd/packages/Python:python_tar",
               "//omd/packages/check-cert",
               "//omd/packages/cpp-libs",
               "//omd/packages/erlang",
               "//omd/packages/heirloom-mailx",
               "//omd/packages/heirloom-pkgtools",
               "//omd/packages/lcab",
               "//omd/packages/maintenance",
               "//omd/packages/mk-livestatus",
               "//omd/packages/mod_fcgid",
               "//omd/packages/mod_wsgi",
               "//omd/packages/monitoring-plugins",
               "//omd/packages/msitools",
               "//omd/packages/nagios",
               "//omd/packages/navicli",
               "//omd/packages/net-snmp:net-snmp_tar",
               "//omd/packages/nrpe",
               "//omd/packages/openssl:openssl_tar_" + edition,
               "//omd/packages/patch",
               "//omd/packages/perl-modules",
               "//omd/packages/pnp4nagios",
               "//omd/packages/python3-modules:python3-modules.tar",
               "//omd/packages/rabbitmq",
               "//omd/packages/redis",
               "//omd/packages/rrdtool:rrdtool_perl_bindings",
               "//omd/packages/rrdtool:rrdtool_python_tar",
               "//omd/packages/rrdtool:rrdtool_tar",
               "//omd/packages/robotmk",
               "//omd/packages/snap7",
               "//omd/packages/stunnel",
               "//omd/packages/xmlsec1",
               "//packages/cmk-agent-receiver:pkg_tar",
               "//packages/cmk-ccc:pkg_tar",
               "//packages/cmk-crypto:pkg_tar",
               "//packages/cmk-events:pkg_tar",
               "//packages/cmk-frontend",
               "//packages/cmk-frontend-vue",
               "//packages/cmk-livestatus-client:cmk_livestatus_client_pkg_tar",
               "//packages/cmk-livestatus-client:cmk_livestatus_pkg_tar",
               "//packages/cmk-messaging:pkg_tar",
               "//packages/cmk-mkp-tool:pkg_tar",
               "//packages/cmk-plugin-apis:pkg_tar",
               "//packages/cmk-trace:pkg_tar",
               "//packages/cmk-werks:pkg_tar",
               "//packages/livestatus:livestatus_pkg",
               "//packages/neb:neb_pkg",
               "//packages/cmk-shared-typing:pkg_tar",
               "//packages/unixcat:unixcat_tar",
               ":license_info",
           ] + select({
               "//bazel/cmk/distro:almalinux": ["//omd/packages/xinetd"],
               "//bazel/cmk/distro:sles": [
                   "//omd/packages/libgsf",
                   "//omd/packages/xinetd",
               ],
               "//conditions:default": [],
           }) +
           edition_deps[edition],
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
    cmd = "cat $(SRCS) > $@",
) for edition in [
    "cre",
    "cce",
    "cee",
    "cme",
    "cse",
]]

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
    name = "generate_bom_csv_py",
    srcs = ["license_sources/generate_bom_csv.py"],
)

run_binary(
    name = "generate_bom_csv",
    srcs = ["bill-of-materials.json"],
    outs = ["bill-of-materials.csv"],
    args = [
        "--bom",
        "$(location bill-of-materials.json)",
        "--out",
        "$(location bill-of-materials.csv)",
    ],
    tool = ":generate_bom_csv_py",
)

filegroup(
    name = "license_texts",
    srcs = glob([
        "license_sources/license_texts/*.txt",
    ]),
)

py_binary(
    name = "build_bom_texts_pdf_py",
    srcs = ["license_sources/build_bom_texts_pdf.py"],
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
    name = "build_bom_texts_pdf",
    srcs = [":generate_bom_csv"],
    outs = ["License_texts.pdf"],
    args = [
        "--pdf",
        "$(location License_texts.pdf)",
        "--csv",
        "$(location :generate_bom_csv)",
    ],
    tool = ":build_bom_texts_pdf_py",
)

pkg_tar(
    name = "license_info",
    srcs = [
        "bill-of-materials.json",
        ":build_bom_texts_pdf",
        ":generate_bom_csv",
    ],
    package_dir = "share/doc/",
    package_file_name = "license_info_archive.tar",
)
