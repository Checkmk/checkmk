load("@bazel_skylib//rules:run_binary.bzl", "run_binary")
load("@rules_gzip//gzip/compress:defs.bzl", "gzip_compress")
load("@rules_pkg//pkg:deb.bzl", "pkg_deb")
load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files", "pkg_mkdirs", "strip_prefix")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("@rules_uv//uv:pip.bzl", "pip_compile")
load("@rules_uv//uv:venv.bzl", "create_venv")
load("//bazel/rules:file_from_flag.bzl", "file_from_flag")
load("//bazel/rules:git_hash_file.bzl", "git_hash_file")
load("//bazel/rules:md5sums_from_archive.bzl", "md5sums_from_archive")
load("//bazel/rules:pkg_cma_from_tar.bzl", "pkg_cma_from_tar")
load("//bazel/rules:pkg_name_info.bzl", "pkg_name_info")
load("//bazel/rules:pkg_rpm_from_tar.bzl", "pkg_rpm_from_tar")
load("//bazel/rules:write_omd_spec.bzl", "write_omd_spec")

exports_files([
    "requirements.txt",
    "bill-of-materials.json",
])

py_binary(
    name = "strip_binaries",
    srcs = ["strip_binaries.py"],
    main = "strip_binaries.py",
    visibility = ["//visibility:public"],
)

# NOTES:
# * jaeger should be added to all editions EXCEPT cloud - cloud has its own tracing collector
# * nagvis should be added to all editions EXCEPT cloud - see CMK-14926
edition_deps = select({
    "@cmk//edition:cloud": [
        "//cmk/plugins/custom_query_metric_backend:pkg_tar",
        "//non-free/packages/cmk-bakery:pkg_tar",
        "//non-free/packages/cmk-cloud:pkg_tar",
        "//non-free/packages/cmc-protocols:pkg_tar",
        "//non-free/packages/cmk-core-helpers:pkg_tar",
        "//non-free/packages/cmk-core-helpers:relay-fetcher-trigger-pkg_tar",
        "//non-free/packages/cmk-metric-backend:cmk-metric-backend-schema-manager_pkg_tar",
        "//non-free/packages/cmk-metric-backend:pkg_tar",
        "//non-free/packages/cmk-telemetry:pkg_tar",
        "//non-free/packages/cmk-mknotifyd:pkg_tar",
        "//non-free/packages/cmk-notification-plugins-nonfree:pkg_tar",
        "//non-free/packages/cmk-otel-collector:pkg_tar",
        "//non-free/packages/cmk-update-agent:pkg_tar",
        "//omd/non-free/packages/alert-handling:pkg_tar",
        "//omd/non-free/packages/cmc:pkg_tar",
        "//omd/non-free/packages/cmk-dcd:pkg_tar",
        "//omd/non-free/packages/cmk-licensing-nonfree:pkg_tar",
        "//omd/non-free/packages/cmk-liveproxyd:pkg_tar",
        "//omd/non-free/packages/cmk-robotmk:pkg_tar",
        "//omd/non-free/packages/legal-docs:ultimate_pkg_tar",
        "//omd/non-free/packages/licensing:pkg_tar",
        "//omd/non-free/packages/reporting:pkg_tar",
        "//omd/non-free/packages/robotmk:pkg_tar",
        "//omd/non-free/packages/saml2:pkg_tar",
        "//non-free/packages/cmk-relay-engine:relay_install_pkg",
    ],
    "@cmk//edition:community": [
        "//omd/packages/jaeger:pkg_tar",
        "//omd/packages/nagvis:pkg_tar",
    ],
    "@cmk//edition:pro": [
        "//non-free/packages/cmk-bakery:pkg_tar",
        "//non-free/packages/cmc-protocols:pkg_tar",
        "//non-free/packages/cmk-core-helpers:pkg_tar",
        "//non-free/packages/cmk-mknotifyd:pkg_tar",
        "//non-free/packages/cmk-notification-plugins-nonfree:pkg_tar",
        "//non-free/packages/cmk-update-agent:pkg_tar",
        "//omd/non-free/packages/alert-handling:pkg_tar",
        "//omd/non-free/packages/cmc:pkg_tar",
        "//omd/non-free/packages/cmk-dcd:pkg_tar",
        "//omd/non-free/packages/cmk-licensing-nonfree:pkg_tar",
        "//omd/non-free/packages/cmk-liveproxyd:pkg_tar",
        "//omd/non-free/packages/cmk-robotmk:pkg_tar",
        "//omd/non-free/packages/legal-docs:pro_pkg_tar",
        "//omd/non-free/packages/licensing:pkg_tar",
        "//omd/non-free/packages/reporting:pkg_tar",
        "//omd/non-free/packages/robotmk:pkg_tar",
        "//omd/non-free/packages/saml2:pkg_tar",
        "//omd/packages/jaeger:pkg_tar",
        "//omd/packages/nagvis:pkg_tar",
    ],
    "@cmk//edition:ultimate": [
        "//cmk/plugins/custom_query_metric_backend:pkg_tar",
        "//non-free/packages/cmk-bakery:pkg_tar",
        "//non-free/packages/cmc-protocols:pkg_tar",
        "//non-free/packages/cmk-core-helpers:pkg_tar",
        "//non-free/packages/cmk-core-helpers:relay-fetcher-trigger-pkg_tar",
        "//non-free/packages/cmk-metric-backend:cmk-metric-backend-schema-manager_pkg_tar",
        "//non-free/packages/cmk-metric-backend:cmk-monitor-metric-backend_pkg_tar",
        "//non-free/packages/cmk-metric-backend:pkg_tar",
        "//non-free/packages/cmk-telemetry:pkg_tar",
        "//non-free/packages/cmk-mknotifyd:pkg_tar",
        "//non-free/packages/cmk-notification-plugins-nonfree:pkg_tar",
        "//non-free/packages/cmk-otel-collector:pkg_tar",
        "//non-free/packages/cmk-update-agent:pkg_tar",
        "//omd/non-free/packages/alert-handling:pkg_tar",
        "//omd/non-free/packages/cmc:pkg_tar",
        "//omd/non-free/packages/cmk-dcd:pkg_tar",
        "//omd/non-free/packages/cmk-licensing-nonfree:pkg_tar",
        "//omd/non-free/packages/cmk-liveproxyd:pkg_tar",
        "//omd/non-free/packages/cmk-robotmk:pkg_tar",
        "//non-free/packages/cmk-plugins-nonfree:pkg_tar-aws_extended",
        "//omd/non-free/packages/legal-docs:ultimate_pkg_tar",
        "//omd/non-free/packages/licensing:pkg_tar",
        "//omd/non-free/packages/metric-backend:pkg_tar",
        "//omd/non-free/packages/reporting:pkg_tar",
        "//omd/non-free/packages/robotmk:pkg_tar",
        "//omd/non-free/packages/saml2:pkg_tar",
        "//non-free/packages/cmk-relay-engine:relay_install_pkg",
        "//omd/packages/jaeger:pkg_tar",
        "//omd/packages/nagvis:pkg_tar",
        "//non-free/packages/otel-collector",
    ],
    "@cmk//edition:ultimatemt": [
        "//cmk/plugins/custom_query_metric_backend:pkg_tar",
        "//non-free/packages/cmk-bakery:pkg_tar",
        "//non-free/packages/cmc-protocols:pkg_tar",
        "//non-free/packages/cmk-core-helpers:pkg_tar",
        "//non-free/packages/cmk-core-helpers:relay-fetcher-trigger-pkg_tar",
        "//non-free/packages/cmk-metric-backend:cmk-metric-backend-schema-manager_pkg_tar",
        "//non-free/packages/cmk-metric-backend:cmk-monitor-metric-backend_pkg_tar",
        "//non-free/packages/cmk-metric-backend:pkg_tar",
        "//non-free/packages/cmk-telemetry:pkg_tar",
        "//non-free/packages/cmk-mknotifyd:pkg_tar",
        "//non-free/packages/cmk-multi-tenancy:pkg_tar",
        "//non-free/packages/cmk-notification-plugins-nonfree:pkg_tar",
        "//non-free/packages/cmk-otel-collector:pkg_tar",
        "//non-free/packages/cmk-plugins-nonfree:pkg_tar-aws_extended",
        "//non-free/packages/cmk-relay-engine:pkg_tar",
        "//non-free/packages/cmk-update-agent:pkg_tar",
        "//omd/non-free/packages/alert-handling:pkg_tar",
        "//omd/non-free/packages/cmc:pkg_tar",
        "//omd/non-free/packages/cmk-dcd:pkg_tar",
        "//omd/non-free/packages/cmk-licensing-nonfree:pkg_tar",
        "//omd/non-free/packages/cmk-liveproxyd:pkg_tar",
        "//omd/non-free/packages/cmk-robotmk:pkg_tar",
        "//omd/non-free/packages/legal-docs:ultimate_pkg_tar",
        "//omd/non-free/packages/licensing:pkg_tar",
        "//omd/non-free/packages/metric-backend:pkg_tar",
        "//omd/non-free/packages/reporting:pkg_tar",
        "//omd/non-free/packages/robotmk:pkg_tar",
        "//omd/non-free/packages/saml2:pkg_tar",
        "//non-free/packages/cmk-relay-engine:relay_install_pkg",
        "//omd/packages/jaeger:pkg_tar",
        "//omd/packages/nagvis:pkg_tar",
        "//non-free/packages/otel-collector",
    ],
})

edition_skel_permissions = select({
    "@cmk//edition:cloud": [
        "//non-free/packages/cmk-mknotifyd:skel.permissions",
        "//omd/non-free/packages/cmc:skel.permissions",
        "//omd/non-free/packages/cmk-dcd:skel.permissions",
        "//omd/non-free/packages/cmk-liveproxyd:skel.permissions",
        "//omd/non-free/packages/licensing:skel.permissions",
        "//omd/non-free/packages/metric-backend:skel.permissions",
        "//omd/non-free/packages/reporting:skel.permissions",
        "//omd/non-free/packages/saml2:skel.permissions",
        "//omd/packages/apache-omd:skel.permissions",
        "//omd/packages/check_mk:skel.permissions",
        "//omd/packages/maintenance:skel.permissions",
        "//omd/packages/nagios:skel.permissions",
        "//omd/packages/omd:skel.permissions",
        "//omd/packages/pnp4nagios:skel.permissions",
        "//omd/packages/rabbitmq:skel.permissions",
        "//omd/packages/redis:skel.permissions",
        "//omd/packages/rrdtool:skel.permissions",
        "//omd/packages/stunnel:skel.permissions",
        "//omd/packages/openssl:skel.permissions",
        "//omd/packages/perl-modules:skel.permissions",
    ],
    "@cmk//edition:community": [
        "//omd/packages/apache-omd:skel.permissions",
        "//omd/packages/check_mk:skel.permissions",
        "//omd/packages/jaeger:skel.permissions",
        "//omd/packages/maintenance:skel.permissions",
        "//omd/packages/nagios:skel.permissions",
        "//omd/packages/nagvis:skel.permissions",
        "//omd/packages/omd:skel.permissions",
        "//omd/packages/pnp4nagios:skel.permissions",
        "//omd/packages/rabbitmq:skel.permissions",
        "//omd/packages/redis:skel.permissions",
        "//omd/packages/rrdtool:skel.permissions",
        "//omd/packages/stunnel:skel.permissions",
        "//omd/packages/openssl:skel.permissions",
        "//omd/packages/perl-modules:skel.permissions",
    ],
    "@cmk//edition:pro": [
        "//omd/packages/apache-omd:skel.permissions",
        "//non-free/packages/cmk-mknotifyd:skel.permissions",
        "//omd/non-free/packages/cmc:skel.permissions",
        "//omd/non-free/packages/cmk-dcd:skel.permissions",
        "//omd/non-free/packages/cmk-liveproxyd:skel.permissions",
        "//omd/non-free/packages/saml2:skel.permissions",
        "//omd/packages/check_mk:skel.permissions",
        "//omd/packages/jaeger:skel.permissions",
        "//omd/packages/maintenance:skel.permissions",
        "//omd/packages/nagios:skel.permissions",
        "//omd/packages/nagvis:skel.permissions",
        "//omd/packages/omd:skel.permissions",
        "//omd/packages/pnp4nagios:skel.permissions",
        "//omd/packages/rabbitmq:skel.permissions",
        "//omd/packages/redis:skel.permissions",
        "//omd/packages/rrdtool:skel.permissions",
        "//omd/packages/stunnel:skel.permissions",
        "//omd/packages/openssl:skel.permissions",
        "//omd/packages/perl-modules:skel.permissions",
    ],
    "@cmk//edition:ultimate": [
        "//omd/packages/apache-omd:skel.permissions",
        "//non-free/packages/cmk-mknotifyd:skel.permissions",
        "//non-free/packages/otel-collector:skel.permissions",
        "//omd/non-free/packages/cmc:skel.permissions",
        "//omd/non-free/packages/cmk-dcd:skel.permissions",
        "//omd/non-free/packages/cmk-liveproxyd:skel.permissions",
        "//omd/non-free/packages/licensing:skel.permissions",
        "//omd/non-free/packages/metric-backend:skel.permissions",
        "//omd/non-free/packages/reporting:skel.permissions",
        "//omd/non-free/packages/saml2:skel.permissions",
        "//omd/packages/check_mk:skel.permissions",
        "//omd/packages/jaeger:skel.permissions",
        "//omd/packages/maintenance:skel.permissions",
        "//omd/packages/nagios:skel.permissions",
        "//omd/packages/nagvis:skel.permissions",
        "//omd/packages/omd:skel.permissions",
        "//omd/packages/pnp4nagios:skel.permissions",
        "//omd/packages/rabbitmq:skel.permissions",
        "//omd/packages/redis:skel.permissions",
        "//omd/packages/rrdtool:skel.permissions",
        "//omd/packages/stunnel:skel.permissions",
        "//omd/packages/openssl:skel.permissions",
        "//omd/packages/perl-modules:skel.permissions",
    ],
    "@cmk//edition:ultimatemt": [
        "//omd/packages/apache-omd:skel.permissions",
        "//non-free/packages/cmk-mknotifyd:skel.permissions",
        "//non-free/packages/otel-collector:skel.permissions",
        "//omd/non-free/packages/cmc:skel.permissions",
        "//omd/non-free/packages/cmk-dcd:skel.permissions",
        "//omd/non-free/packages/cmk-liveproxyd:skel.permissions",
        "//omd/non-free/packages/licensing:skel.permissions",
        "//omd/non-free/packages/metric-backend:skel.permissions",
        "//omd/non-free/packages/reporting:skel.permissions",
        "//omd/non-free/packages/saml2:skel.permissions",
        "//omd/packages/check_mk:skel.permissions",
        "//omd/packages/jaeger:skel.permissions",
        "//omd/packages/maintenance:skel.permissions",
        "//omd/packages/nagios:skel.permissions",
        "//omd/packages/nagvis:skel.permissions",
        "//omd/packages/omd:skel.permissions",
        "//omd/packages/pnp4nagios:skel.permissions",
        "//omd/packages/rabbitmq:skel.permissions",
        "//omd/packages/redis:skel.permissions",
        "//omd/packages/rrdtool:skel.permissions",
        "//omd/packages/stunnel:skel.permissions",
        "//omd/packages/openssl:skel.permissions",
        "//omd/packages/perl-modules:skel.permissions",
    ],
})

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
        "cmk_edition": "@cmk//edition",
        "cmk_version": "@cmk//version",
    },
    tags = ["manual"],
)

file_from_flag(
    name = "omd_root_dir_appliance",
    out = "omd_root_dir_appliance.txt",
    content = [
        "{cmk_version}.{cmk_edition}",
        "",
    ],
    replace_labels = {
        "cmk_edition": "@cmk//edition",
        "cmk_version": "@cmk//version",
    },
    tags = ["manual"],
)

pkg_mkdirs(
    name = "omd_global_dirs",
    attributes = pkg_attributes(
        group = "root",
        mode = "0755",
        user = "root",
    ),
    dirs = [
        "/opt/omd/apache",
        "/opt/omd/sites",
    ],
)

pkg_tar(
    name = "omd_global_dirs_tar",
    srcs = [":omd_global_dirs"],
    mtime = 1767744000,
    package_dir = "/",
    portable_mtime = False,
)

_EDITION_SELECT = select({
    "@cmk//edition:cloud": ["cloud"],
    "@cmk//edition:community": ["community"],
    "@cmk//edition:pro": ["pro"],
    "@cmk//edition:ultimate": ["ultimate"],
    "@cmk//edition:ultimatemt": ["ultimatemt"],
})

run_binary(
    name = "generate_doc.spec",
    outs = ["doc.spec"],
    args = [
        "generate",
        "--version",
        "v1",
        "--edition",
    ] + _EDITION_SELECT + [
        "--target",
        "doc",
        "--out",
        "$(execpath doc.spec)",
        "--format",
        "dict",
    ],
    tags = ["manual"],
    tool = "//cmk/gui/openapi/spec:generate_api_spec",
)

run_binary(
    name = "generate_swagger_ui.spec",
    outs = ["swagger-ui.spec"],
    args = [
        "generate",
        "--version",
        "v1",
        "--edition",
    ] + _EDITION_SELECT + [
        "--target",
        "swagger-ui",
        "--out",
        "$(execpath swagger-ui.spec)",
        "--format",
        "dict",
    ],
    tags = ["manual"],
    tool = "//cmk/gui/openapi/spec:generate_api_spec",
)

run_binary(
    name = "generate_unstable_doc.spec",
    outs = ["unstable-doc.spec"],
    args = [
        "generate",
        "--version",
        "unstable",
        "--edition",
    ] + _EDITION_SELECT + [
        "--target",
        "doc",
        "--out",
        "$(execpath unstable-doc.spec)",
        "--format",
        "dict",
    ],
    tags = ["manual"],
    tool = "//cmk/gui/openapi/spec:generate_api_spec",
)

run_binary(
    name = "generate_unstable_swagger_ui.spec",
    outs = ["unstable-swagger-ui.spec"],
    args = [
        "generate",
        "--version",
        "unstable",
        "--edition",
    ] + _EDITION_SELECT + [
        "--target",
        "swagger-ui",
        "--out",
        "$(execpath unstable-swagger-ui.spec)",
        "--format",
        "dict",
    ],
    tags = ["manual"],
    tool = "//cmk/gui/openapi/spec:generate_api_spec",
)

pkg_files(
    name = "rest_api_spec",
    srcs = [
        ":doc.spec",
        ":swagger-ui.spec",
        ":unstable-doc.spec",
        ":unstable-swagger-ui.spec",
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

pkg_files(
    name = "agents",
    srcs = [
        "//agents",
    ],
    prefix = "share/check_mk/agents",
    strip_prefix = strip_prefix.from_pkg(""),
)

pkg_files(
    name = "cmk-agent-ctl-files",
    srcs = [
        "//packages/cmk-agent-ctl:cmk-agent-ctl-musl",
        "//packages/cmk-agent-ctl:cmk-agent-ctl-musl-aarch64",
    ],
    prefix = "share/check_mk/agents",
    renames = {
        "//packages/cmk-agent-ctl:cmk-agent-ctl-musl": "cmk-agent-ctl",
        "//packages/cmk-agent-ctl:cmk-agent-ctl-musl-aarch64": "cmk-agent-ctl-aarch64",
    },
)

pkg_files(
    name = "mk-sql-files",
    srcs = [
        "//packages/mk-sql:mk-sql-musl",
    ],
    prefix = "share/check_mk/agents",
    renames = {
        "//packages/mk-sql:mk-sql-musl": "mk-sql",
    },
)

genrule(
    name = "cmk-agent-ctl-renamed",
    srcs = ["//packages/cmk-agent-ctl:cmk-agent-ctl-musl"],
    outs = ["cmk-agent-ctl"],
    cmd = "cp $< $@",
)

gzip_compress(
    name = "cmk-agent-ctl-gz",
    src = ":cmk-agent-ctl",
)

pkg_tar(
    name = "cmk-agent-ctl-aarch64-gz",
    srcs = ["//packages/cmk-agent-ctl:cmk-agent-ctl-musl-aarch64"],
    out = "cmk-agent-ctl-aarch64.gz",
    extension = "tar.gz",
    mtime = 1767744000,
    portable_mtime = False,
    remap_paths = {
        "/cmk-agent-ctl-musl-aarch64": "cmk-agent-ctl-aarch64",
    },
)

pkg_files(
    name = "agents_linux",
    srcs = [
        ":cmk-agent-ctl-aarch64-gz",
        ":cmk-agent-ctl-gz",
        "//packages/cmk-agent-ctl:cmk-agent-ctl-musl",
        "//packages/cmk-agent-ctl:cmk-agent-ctl-musl-aarch64",
        "//packages/mk-sql:mk-sql-musl",
    ],
    attributes = pkg_attributes(mode = "0755"),
    prefix = "share/check_mk/agents/linux",
    renames = {
        "//packages/cmk-agent-ctl:cmk-agent-ctl-musl": "cmk-agent-ctl",
        "//packages/cmk-agent-ctl:cmk-agent-ctl-musl-aarch64": "cmk-agent-ctl-aarch64",
        "//packages/mk-sql:mk-sql-musl": "mk-sql",
    },
)

pkg_files(
    name = "agents_cfg_examples",
    srcs = ["//agents/cfg_examples:srcs"],
    prefix = "share/check_mk/agents/cfg_examples",
)

pkg_files(
    name = "agents_plugins",
    srcs = ["//agents/plugins:srcs"],
    attributes = pkg_attributes(mode = "0755"),
    prefix = "share/check_mk/agents/plugins",
)

pkg_files(
    name = "agents_sap",
    srcs = ["//agents/sap:srcs"],
    prefix = "share/check_mk/agents/sap",
)

pkg_files(
    name = "agents_windows_ext_built",
    srcs = [
        "//agents/windows:agents",
    ],
    prefix = "agents/windows",
    strip_prefix = strip_prefix.from_pkg(""),
    tags = ["no-python-extension-checker"],
)

pkg_tar(
    name = "agents_windows",
    srcs = [
        ":agents_windows_ext_built",
        "//agents/windows:cfg_examples",
        "//agents/windows:mrpe",
        "//agents/windows/plugins",
    ],
    package_dir = "share/check_mk",
    stamp = 1,
    strip_prefix = ".",
    tags = ["no-python-extension-checker"],
)

pkg_files(
    name = "agents_scripts",
    srcs = ["//agents:srcs"],
    attributes = pkg_attributes(mode = "0755"),
    prefix = "share/check_mk/agents/scripts",
)

pkg_tar(
    name = "agents_scripts_super_server",
    srcs = ["//agents:super-server"],
    mode = "0755",
    package_dir = "share/check_mk",
    stamp = 1,
    strip_prefix = "scripts",
)

pkg_files(
    name = "agents_z_os",
    srcs = ["//agents/z_os:srcs"],
    prefix = "share/check_mk/agents/z_os",
)

pkg_files(
    name = "cmk_libexec",
    srcs = ["//cmk/plugins:libexec"],
    attributes = pkg_attributes(mode = "0755"),
    prefix = "lib/python3/cmk/plugins",
    strip_prefix = strip_prefix.from_pkg(""),
)

git_hash_file(
    name = "hash_file",
    out = "COMMIT",
)

pkg_files(
    name = "hash_file_pkg",
    srcs = [":hash_file"],
    prefix = "share/doc",
)

file_from_flag(
    name = "omd_info_file",
    out = "omd.info",
    content = [
        "OMD_VERSION = {cmk_version}.{cmk_edition}",
        "OMD_PHYSICAL_BASE = /opt/omd",
        "",
    ],
    replace_labels = {
        "cmk_edition": "@cmk//edition",
        "cmk_version": "@cmk//version",
    },
    tags = ["manual"],
)

pkg_files(
    name = "info_files",
    srcs = [":omd_info_file"] + select({
        "@cmk//distro:almalinux-10": ["//omd/distros:ALMALINUX_10.mk"],
        "@cmk//distro:almalinux-8": ["//omd/distros:ALMALINUX_8.mk"],
        "@cmk//distro:almalinux-9": ["//omd/distros:ALMALINUX_9.mk"],
        "@cmk//distro:debian-12": ["//omd/distros:DEBIAN_12.mk"],
        "@cmk//distro:debian-13": ["//omd/distros:DEBIAN_13.mk"],
        "@cmk//distro:sles-15sp6": ["//omd/distros:SLES_15SP6.mk"],
        "@cmk//distro:sles-15sp7": ["//omd/distros:SLES_15SP7.mk"],
        "@cmk//distro:sles-16.0": ["//omd/distros:SLES_16.0.mk"],
        "@cmk//distro:ubuntu-22.04": ["//omd/distros:UBUNTU_22.04.mk"],
        "@cmk//distro:ubuntu-24.04": ["//omd/distros:UBUNTU_24.04.mk"],
        "@cmk//distro:ubuntu-26.04": ["//omd/distros:UBUNTU_26.04.mk"],
    }),
    prefix = "share/omd",
    renames = select({
        "@cmk//distro:almalinux-10": {"//omd/distros:ALMALINUX_10.mk": "distro.info"},
        "@cmk//distro:almalinux-8": {"//omd/distros:ALMALINUX_8.mk": "distro.info"},
        "@cmk//distro:almalinux-9": {"//omd/distros:ALMALINUX_9.mk": "distro.info"},
        "@cmk//distro:debian-12": {"//omd/distros:DEBIAN_12.mk": "distro.info"},
        "@cmk//distro:debian-13": {"//omd/distros:DEBIAN_13.mk": "distro.info"},
        "@cmk//distro:sles-15sp6": {"//omd/distros:SLES_15SP6.mk": "distro.info"},
        "@cmk//distro:sles-15sp7": {"//omd/distros:SLES_15SP7.mk": "distro.info"},
        "@cmk//distro:sles-16.0": {"//omd/distros:SLES_16.0.mk": "distro.info"},
        "@cmk//distro:ubuntu-22.04": {"//omd/distros:UBUNTU_22.04.mk": "distro.info"},
        "@cmk//distro:ubuntu-24.04": {"//omd/distros:UBUNTU_24.04.mk": "distro.info"},
        "@cmk//distro:ubuntu-26.04": {"//omd/distros:UBUNTU_26.04.mk": "distro.info"},
    }),
)

pkg_tar(
    name = "deps_packages",
    srcs = [
        ":agents",
        ":agents_cfg_examples",
        ":agents_linux",
        ":agents_plugins",
        ":agents_sap",
        ":agents_scripts",
        ":agents_z_os",
        ":cmk_libexec",
        ":diskspace_cleanup_plugin",
        ":hash_file_pkg",
        ":info_files",
        ":omd_hooks",
        ":rest_api_spec",
        ":share_doc_check-mk",
        ":share_doc_check-mk_agents",
        ":share_doc_check-mk_documentation",
        ":skel_permissions_pkg",
        "//omd/packages/freetds:freetds_pkg",
        "//omd/packages/protobuf",
        "//packages/check-http:check_http_pkg",
    ],
    stamp = 1,
    tags = ["manual"],
    deps = [
        "//active_checks:pkg_tar",
        "//bin:pkg_tar",
        "//cmk:cmk_tar",
        "//packages/cmk-plugin-apis/doc:pkg_tar",
        "//locale",
        "//packages/cmk-notification-plugins:pkg_tar",
        #added here instead of above because of disappearing file
        "//omd/packages/Python:python_tar",
        "//omd/packages/apache-omd",
        "//omd/packages/changelog",
        "//omd/packages/check-cert",
        "//omd/packages/check_mk",
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
        "//omd/packages/net-snmp",
        "//omd/packages/nrpe",
        "//omd/packages/omd",
        "//omd/packages/openssl:openssl_tar",
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
        "//packages/cmk-ec:pkg_tar",
        "//packages/cmk-events:pkg_tar",
        "//packages/cmk-licensing:pkg_tar",
        "//packages/cmk-frontend",
        "//packages/cmk-frontend-vue",
        "//packages/cmk-livestatus-client:cmk_livestatus_client_pkg_tar",
        "//packages/cmk-livestatus-client:cmk_livestatus_pkg_tar",
        "//packages/cmk-logwatch:pkg_tar",
        "//packages/cmk-messaging:pkg_tar",
        "//packages/cmk-mkp-tool:pkg_tar",
        "//packages/cmk-plugins:pkg_tar",
        "//packages/cmk-plugin-apis:pkg_tar",
        "//packages/cmk-relay-protocols:pkg_tar",
        "//packages/cmk-trace:pkg_tar",
        "//packages/cmk-werks:pkg_tar",
        "//packages/livestatus:livestatus_pkg",
        "//packages/neb:neb_pkg",
        "//packages/cmk-shared-typing:pkg_tar",
        "//packages/unixcat:unixcat_tar",
        ":agents_scripts_super_server",
        ":agents_windows",
        "//omd/dependency_management:license_info",
    ] + select({
        "@cmk//distro:almalinux": ["//omd/packages/xinetd"],
        "@cmk//distro:sles": [
            "//omd/packages/libgsf",
            "//omd/packages/xinetd",
        ],
        "//conditions:default": [],
    }) + edition_deps,
)

pkg_tar(
    name = "deps_install",
    mtime = 1767744000,
    package_dir_file = ":omd_root_dir",
    portable_mtime = False,
    tags = ["manual"],
    deps = [
        ":deps_packages",
    ],
)

pkg_tar(
    name = "complete_install",
    mtime = 1767744000,
    portable_mtime = False,
    tags = ["manual"],
    deps = [
        ":deps_install",
        ":omd_global_dirs_tar",
    ],
)

pkg_tar(
    name = "complete_install_compressed",
    compressor = "@zstd//:zstd_cli",
    compressor_args = "-19",
    extension = "tar.zst",
    mtime = 1767744000,
    portable_mtime = False,
    tags = ["manual"],
    deps = [
        ":complete_install",
    ],
)

pkg_tar(
    name = "complete_install_uncompressed",
    mtime = 1767744000,
    portable_mtime = False,
    tags = ["manual"],
    deps = [
        ":complete_install",
    ],
)

genrule(
    name = "skel_permissions",
    srcs = edition_skel_permissions,
    outs = ["skel.permissions"],
    cmd = "cat $(SRCS) > $@",
    tags = ["manual"],
)

pkg_files(
    name = "skel_permissions_pkg",
    srcs = [":skel_permissions"],
    prefix = "share/omd",
    renames = {"skel_permissions": "skel.permissions"},
)

pkg_name_info(
    name = "cmk_pkg_variables",
    architecture = "amd64",
    cmk_version = "@cmk//version",
    package = select({
        "@cmk//edition:cloud": "check-mk-cloud",
        "@cmk//edition:community": "check-mk-community",
        "@cmk//edition:pro": "check-mk-pro",
        "@cmk//edition:ultimate": "check-mk-ultimate",
        "@cmk//edition:ultimatemt": "check-mk-ultimatemt",
    }),
    tags = ["manual"],
    version = select({
        "@cmk//distro:almalinux-10": "el10-38",
        "@cmk//distro:almalinux-8": "el8-38",
        "@cmk//distro:almalinux-9": "el9-38",
        "@cmk//distro:debian-12": "0.bookworm",
        "@cmk//distro:debian-13": "0.trixie",
        "@cmk//distro:sles-15sp6": "sles15sp6",
        "@cmk//distro:sles-15sp7": "sles15sp7",
        "@cmk//distro:sles-16.0": "sles16.0",
        "@cmk//distro:ubuntu-22.04": "0.jammy",
        "@cmk//distro:ubuntu-24.04": "0.noble",
        "@cmk//distro:ubuntu-26.04": "0.resolute",
    }),
)

md5sums_from_archive(
    name = "md5sums",
    src = "//omd/packages/heirloom-mailx",
    out = "md5",
)

pkg_deb(
    name = "deb",
    architecture = "amd64",
    config = "//omd/debian:config",
    data = select({
        "@//:skip_package_compression_enabled": ":complete_install_uncompressed",
        "//conditions:default": "complete_install_compressed",
    }),
    depends_file = "//omd/distros:dependencies",
    description = "Checkmk - Best-in-class infrastructure & application monitoring",
    homepage = "https://checkmk.com",
    maintainer = "Checkmk team <feedback@checkmk.com>",
    md5sums = ":md5sums",
    package = "{package}-{cmk_version}",
    package_file_name = "{package}-{cmk_version}_{version}_{architecture}.deb",
    package_variables = ":cmk_pkg_variables",
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
)

sh_test(
    name = "validate_deb",
    srcs = ["validate_package_test.sh"],
    args = [
        "$(location :deb)",
        "$(location //tests/packaging/package_validator:package_validator)",
        "$(location //tests/packaging/package_validator:ignore_files)",
        "$(location //tests/packaging/package_validator:system_dependencies_all)",
    ] + select({
        "@cmk//distro:debian-12": [
            "$(location //tests/packaging/package_validator:system_dependencies_debian)",
            "$(location //tests/packaging/package_validator:system_dependencies_bookworm)",
        ],
        "@cmk//distro:debian-13": [
            "$(location //tests/packaging/package_validator:system_dependencies_debian)",
            "$(location //tests/packaging/package_validator:system_dependencies_trixie)",
        ],
        "@cmk//distro:ubuntu-22.04": [
            "$(location //tests/packaging/package_validator:system_dependencies_ubuntu)",
            "$(location //tests/packaging/package_validator:system_dependencies_jammy)",
        ],
        "@cmk//distro:ubuntu-24.04": [
            "$(location //tests/packaging/package_validator:system_dependencies_ubuntu)",
            "$(location //tests/packaging/package_validator:system_dependencies_noble)",
        ],
        "@cmk//distro:ubuntu-26.04": [
            "$(location //tests/packaging/package_validator:system_dependencies_ubuntu)",
            "$(location //tests/packaging/package_validator:system_dependencies_resolute)",
        ],
    }),
    data = [
        ":deb",
        "//tests/packaging/package_validator",
        "//tests/packaging/package_validator:ignore_files",
        "//tests/packaging/package_validator:system_dependencies_all",
    ] + select({
        "@cmk//distro:debian-12": [
            "//tests/packaging/package_validator:system_dependencies_bookworm",
            "//tests/packaging/package_validator:system_dependencies_debian",
        ],
        "@cmk//distro:debian-13": [
            "//tests/packaging/package_validator:system_dependencies_debian",
            "//tests/packaging/package_validator:system_dependencies_trixie",
        ],
        "@cmk//distro:ubuntu-22.04": [
            "//tests/packaging/package_validator:system_dependencies_jammy",
            "//tests/packaging/package_validator:system_dependencies_ubuntu",
        ],
        "@cmk//distro:ubuntu-24.04": [
            "//tests/packaging/package_validator:system_dependencies_noble",
            "//tests/packaging/package_validator:system_dependencies_ubuntu",
        ],
        "@cmk//distro:ubuntu-26.04": [
            "//tests/packaging/package_validator:system_dependencies_resolute",
            "//tests/packaging/package_validator:system_dependencies_ubuntu",
        ],
    }),
    tags = ["manual"],
)

write_omd_spec(
    name = "omd_spec",
    apache_conf_dir = select({
        "@cmk//distro:almalinux": "/etc/httpd/conf.d",
        "@cmk//distro:sles": "/etc/apache2/conf.d",
        "//conditions:default": "",
    }),
    apache_init_name = select({
        "@cmk//distro:almalinux": "httpd",
        "@cmk//distro:sles": "apache2",
        "//conditions:default": "",
    }),
    dependencies = "//omd/distros:dependencies",
    distro_code = select({
        "@cmk//distro:almalinux-10": "el10",
        "@cmk//distro:almalinux-8": "el8",
        "@cmk//distro:almalinux-9": "el9",
        "@cmk//distro:sles-15sp6": "sles15sp6",
        "@cmk//distro:sles-15sp7": "sles15sp7",
        "@cmk//distro:sles-16.0": "sles16.0",
        "//conditions:default": "",
    }),
    edition = "@cmk//edition",
    omd_spec = "omd.spec",
    omd_spec_in = ":omd.spec.in",
    tags = ["manual"],
    target_compatible_with = select({
        "@cmk//distro:almalinux": [],
        "@cmk//distro:sles": [],
        "//conditions:default": ["@platforms//:incompatible"],
    }),
    version = "@cmk//version",
)

pkg_rpm_from_tar(
    name = "rpm",
    distro_code = select({
        "@cmk//distro:almalinux-10": "el10",
        "@cmk//distro:almalinux-8": "el8",
        "@cmk//distro:almalinux-9": "el9",
        "@cmk//distro:sles-15sp6": "sles15sp6",
        "@cmk//distro:sles-15sp7": "sles15sp7",
        "@cmk//distro:sles-16.0": "sles16.0",
        "//conditions:default": "",
    }),
    edition = "@cmk//edition",
    input_tarball = "complete_install",
    omd_spec = ":omd_spec",
    rpm = "cmk.rpm",
    tags = ["manual"],
    target_compatible_with = select({
        "@cmk//distro:almalinux": [],
        "@cmk//distro:sles": [],
        "//conditions:default": ["@platforms//:incompatible"],
    }),
    version = "@cmk//version",
)

sh_test(
    name = "validate_rpm",
    srcs = ["validate_package_test.sh"],
    args = [
        "$(location :rpm)",
        "$(location //tests/packaging/package_validator:package_validator)",
        "$(location //tests/packaging/package_validator:ignore_files)",
        "$(location //tests/packaging/package_validator:system_dependencies_all)",
    ] + select({
        "@cmk//distro:almalinux-10": [
            "$(location //tests/packaging/package_validator:system_dependencies_el)",
            "$(location //tests/packaging/package_validator:system_dependencies_el10)",
        ],
        "@cmk//distro:almalinux-8": [
            "$(location //tests/packaging/package_validator:system_dependencies_el)",
            "$(location //tests/packaging/package_validator:system_dependencies_el8)",
        ],
        "@cmk//distro:almalinux-9": [
            "$(location //tests/packaging/package_validator:system_dependencies_el)",
            "$(location //tests/packaging/package_validator:system_dependencies_el9)",
        ],
        "@cmk//distro:sles-15sp6": [
            "$(location //tests/packaging/package_validator:system_dependencies_sles)",
            "$(location //tests/packaging/package_validator:system_dependencies_sles15sp6)",
        ],
        "@cmk//distro:sles-15sp7": [
            "$(location //tests/packaging/package_validator:system_dependencies_sles)",
            "$(location //tests/packaging/package_validator:system_dependencies_sles15sp7)",
        ],
        "@cmk//distro:sles-16.0": [
            "$(location //tests/packaging/package_validator:system_dependencies_sles)",
            "$(location //tests/packaging/package_validator:system_dependencies_sles16_0)",
        ],
    }),
    data = [
        ":rpm",
        "//tests/packaging/package_validator",
        "//tests/packaging/package_validator:ignore_files",
        "//tests/packaging/package_validator:system_dependencies_all",
    ] + select({
        "@cmk//distro:almalinux-10": [
            "//tests/packaging/package_validator:system_dependencies_el",
            "//tests/packaging/package_validator:system_dependencies_el10",
        ],
        "@cmk//distro:almalinux-8": [
            "//tests/packaging/package_validator:system_dependencies_el",
            "//tests/packaging/package_validator:system_dependencies_el8",
        ],
        "@cmk//distro:almalinux-9": [
            "//tests/packaging/package_validator:system_dependencies_el",
            "//tests/packaging/package_validator:system_dependencies_el9",
        ],
        "@cmk//distro:sles-15sp6": [
            "//tests/packaging/package_validator:system_dependencies_sles",
            "//tests/packaging/package_validator:system_dependencies_sles15sp6",
        ],
        "@cmk//distro:sles-15sp7": [
            "//tests/packaging/package_validator:system_dependencies_sles",
            "//tests/packaging/package_validator:system_dependencies_sles15sp7",
        ],
        "@cmk//distro:sles-16.0": [
            "//tests/packaging/package_validator:system_dependencies_sles",
            "//tests/packaging/package_validator:system_dependencies_sles16_0",
        ],
    }),
    tags = ["manual"],
    target_compatible_with = select({
        "@cmk//distro:almalinux": [],
        "@cmk//distro:sles": [],
        "//conditions:default": ["@platforms//:incompatible"],
    }),
)

pkg_tar(
    name = "appliance",
    extension = "tar.gz",
    mtime = 1767744000,
    package_dir_file = "//omd:omd_root_dir_appliance",
    portable_mtime = False,
    target_compatible_with = select({
        "@cmk//edition:pro": [],
        "@cmk//edition:ultimate": [],
        "@cmk//edition:ultimatemt": [],
        "//conditions:default": ["@platforms//:incompatible"],
    }),
    visibility = ["//visibility:public"],
    deps = [
        "//omd:deps_packages",
        "//omd/packages/appliance:appliance_install",
    ],
)

pkg_cma_from_tar(
    name = "cma",
    cma = "cmk.cma",
    distro_code = select({
        # CMA 4 is based on Debian 12
        "@cmk//distro:debian-12": "4",
        "//conditions:default": "",
    }),
    edition = "@cmk//edition",
    input_tarball = ":appliance",
    tags = ["manual"],
    target_compatible_with = select({
        "@cmk//distro:debian-12": [],
        "//conditions:default": ["@platforms//:incompatible"],
    }),
    version = "@cmk//version",
)

sh_test(
    name = "validate_cma",
    srcs = ["validate_package_test.sh"],
    args = [
        "$(location :cma)",
        "$(location //tests/packaging/package_validator:package_validator)",
        "$(location //tests/packaging/package_validator:ignore_files)",
        "$(location //tests/packaging/package_validator:system_dependencies_all)",
        "$(location //tests/packaging/package_validator:system_dependencies_cma)",
    ],
    data = [
        ":cma",
        "//tests/packaging/package_validator",
        "//tests/packaging/package_validator:ignore_files",
        "//tests/packaging/package_validator:system_dependencies_all",
        "//tests/packaging/package_validator:system_dependencies_cma",
    ],
    tags = ["manual"],
)

sh_library(
    name = "omd_sh",
    srcs = [
        "run-binreplace",
    ],
)
