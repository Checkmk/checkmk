load("@aspect_rules_py//py:defs.bzl", "py_binary")
load("@bazel_skylib//rules:run_binary.bzl", "run_binary")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_pkg//pkg:deb.bzl", "pkg_deb")
load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("@rules_uv//uv:pip.bzl", "pip_compile")
load("@rules_uv//uv:venv.bzl", "create_venv")
load("//:bazel_variables.bzl", "edition_deps", "edition_skel_permissions")
load("//bazel/rules:file_from_flag.bzl", "file_from_flag")
load("//bazel/rules:pkg_name_info.bzl", "pkg_name_info")

exports_files([
    "requirements.txt",
])

pip_compile(
    name = "requirements_lock",
    requirements_in = ":requirements.txt",
    requirements_txt = ":requirements_lock.txt",
    tags = ["manual"],
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
        "cmk_version": "@cmk//version",
        "cmk_edition": "@cmk//edition",
    },
    tags = ["manual"],
)

run_binary(
    name = "generate_doc.spec",
    outs = ["doc.spec"],
    args = [
        "generate",
        "--version",
        "v1",
        "--target",
        "doc",
        "--out",
        "$(execpath doc.spec)",
        "--format",
        "dict",
    ],
    tags = ["manual"],
    tool = "//cmk:generate_api_spec",
)

run_binary(
    name = "generate_swagger_ui.spec",
    outs = ["swagger-ui.spec"],
    args = [
        "generate",
        "--version",
        "v1",
        "--target",
        "swagger-ui",
        "--out",
        "$(execpath swagger-ui.spec)",
        "--format",
        "dict",
    ],
    tags = ["manual"],
    tool = "//cmk:generate_api_spec",
)

pkg_files(
    name = "rest_api_spec",
    srcs = [
        ":doc.spec",
        ":swagger-ui.spec",
    ],
    prefix = "share/doc/check_mk/rest-api/spec",
)

pkg_files(
    name = "share_doc_check-mk",
    srcs = [
        "//:AUTHORS",
        "//:COPYING",
    ],
    prefix = "share/doc/check_mk",
)

pkg_files(
    name = "share_doc_check-mk_agents",
    srcs = ["//doc/agents:readme_files"],
    prefix = "share/doc/check_mk/agents",
)

pkg_files(
    name = "share_doc_check-mk_documentation",
    srcs = ["//doc/documentation:srcs"],
    prefix = "share/doc/check_mk/documentation",
)

pkg_files(
    name = "diskspace_cleanup_plugin",
    srcs = ["//omd/packages/check_mk:diskspace"],
    prefix = "share/diskspace",
    renames = {"//omd/packages/check_mk:diskspace": "check_mk"},
)

pkg_files(
    # See also `//omd/packages/omd:hooks`.
    name = "omd_hooks",
    srcs = ["//omd/packages/check_mk:hooks"],
    attributes = pkg_attributes(mode = "0755"),
    prefix = "lib/omd/hooks",
)

[pkg_tar(
    name = "deps_install_" + edition,
    srcs = [
        ":diskspace_cleanup_plugin",
        ":omd_hooks",
        ":rest_api_spec",
        ":share_doc_check-mk",
        ":share_doc_check-mk_agents",
        ":share_doc_check-mk_documentation",
        "//omd/packages/freetds:freetds_pkg",
        "//omd/packages/protobuf",
        "//packages/check-http:check_http_pkg",
    ],
    extension = "tar.xz",
    package_dir_file = ":omd_root_dir",
    tags = ["manual"],
    deps = [
               "//bin:pkg_tar",
               "//active_checks:pkg_tar",
               "//doc/plugin-api:pkg_tar",
               "//locale",
               #added here instead of above because of disappearing file
               "//omd/packages/Python:python_tar",
               "//omd/packages/changelog",
               "//omd/packages/check-cert",
               "//omd/packages/cpp-libs",
               "//omd/packages/erlang",
               "//omd/packages/heirloom-mailx",
               "//omd/packages/heirloom-pkgtools",
               "//omd/packages/lcab",
               "//omd/packages/maintenance",
               "//omd/packages/mk-livestatus",
               "//omd/packages/mk-oracle",
               "//omd/packages/mod_fcgid",
               "//omd/packages/mod_wsgi",
               "//omd/packages/monitoring-plugins",
               "//omd/packages/msitools",
               "//omd/packages/nagios",
               "//omd/packages/net-snmp:net-snmp_tar",
               "//omd/packages/nrpe",
               "//omd/packages/omd",
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
               "//packages/cmk-check-engine:pkg_tar",
               "//packages/cmk-crypto:pkg_tar",
               "//packages/cmk-events:pkg_tar",
               "//packages/cmk-frontend",
               "//packages/cmk-frontend-vue",
               "//packages/cmk-livestatus-client:cmk_livestatus_client_pkg_tar",
               "//packages/cmk-livestatus-client:cmk_livestatus_pkg_tar",
               "//packages/cmk-messaging:pkg_tar",
               "//packages/cmk-mkp-tool:pkg_tar",
               "//packages/cmk-plugin-apis:pkg_tar",
               "//packages/cmk-relay-protocols:pkg_tar",
               "//packages/cmk-trace:pkg_tar",
               "//packages/cmk-werks:pkg_tar",
               "//packages/livestatus:livestatus_pkg",
               "//packages/neb:neb_pkg",
               "//packages/cmk-shared-typing:pkg_tar",
               "//packages/unixcat:unixcat_tar",
               ":license_info",
           ] + select({
               "@cmk//distro:almalinux": ["//omd/packages/xinetd"],
               "@cmk//distro:sles": [
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
    tags = ["manual"],
) for edition in [
    "raw",
    "cloud",
    "enterprise",
    "managed",
    "saas",
]]

py_binary(
    name = "generate_bom_csv_py",
    srcs = ["license_sources/generate_bom_csv.py"],
    tags = ["manual"],
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
    tags = ["manual"],
    tool = ":generate_bom_csv_py",
)

filegroup(
    name = "license_texts",
    srcs = glob([
        "license_sources/license_texts/*.txt",
    ]),
    tags = ["manual"],
)

py_binary(
    name = "build_bom_texts_pdf_py",
    srcs = ["license_sources/build_bom_texts_pdf.py"],
    data = [
        "license_sources/Calibri.ttf",
        "license_sources/checkmk_logo.svg",
        ":license_texts",
    ],
    tags = ["manual"],
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
    tags = ["manual"],
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
    tags = ["manual"],
)

editions = {
    "cce": "cloud",
    "cee": "enterprise",
    "cme": "managed",
    "cre": "raw",
    "cse": "saas",
}

[pkg_name_info(
    name = "cmk_pkg_variables_" + edition,
    architecture = "amd64",
    cmk_version = "@cmk//version",
    package = "check-mk-" + editions[edition],
    tags = ["manual"],
    version = select({
        "@cmk//distro:almalinux-8": "el8-38",
        "@cmk//distro:almalinux-9": "el9-38",
        "@cmk//distro:almalinux-10": "el10-38",
        "@cmk//distro:debian-12": "0.bookworm",
        "@cmk//distro:debian-13": "0.trixie",
        "@cmk//distro:sles-15sp5": "sles15sp5",
        "@cmk//distro:sles-15sp6": "sles15sp6",
        "@cmk//distro:ubuntu-22.04": "0.jammy",
        "@cmk//distro:ubuntu-24.04": "0.noble",
    }),
) for edition in [
    "cre",
    "cce",
    "cee",
    "cme",
    "cse",
]]

[pkg_deb(
    name = "deb_" + edition,
    architecture = "amd64",
    changelog = ":changelog_" + edition,
    config = "//omd/debian:config",
    #control = "//omd/debian:control", Field does not exist, do we need it?
    data = "deps_install_" + edition,
    #data = "//omd/packages/heirloom-mailx",
    depends_file = "//omd/distros:dependencies",
    description = "Checkmk - Best-in-class infrastructure & application monitoring",
    homepage = "https://checkmk.com",
    maintainer = "Checkmk team <feedback@checkmk.com>",
    # check-mk-enterprise-2.5.0-2025.06.26_0.noble_amd64.deb
    package = "check-mk-" + editions[edition],
    package_file_name = "{package}-{cmk_version}_{version}_{architecture}.deb",
    package_variables = ":cmk_pkg_variables_" + edition,
    postinst = "//omd/debian:postinst",
    postrm = "//omd/debian:postrm",
    preinst = "//omd/debian:preinst",
    prerm = "//omd/debian:prerm",
    priority = "optional",
    section = "admin",
    tags = ["manual"],
    templates = "//omd/debian:templates",
    triggers = "//omd/debian:triggers",
    version_file = "//omd/distros:distro_version_file",
) for edition in [
    "cre",
    "cce",
    "cee",
    "cme",
    "cse",
]]
