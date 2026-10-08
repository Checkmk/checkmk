load("@rules_gzip//gzip/compress:defs.bzl", "gzip_compress")
load("@rules_pkg//pkg:deb.bzl", "pkg_deb")
load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files", "pkg_mkdirs", "strip_prefix")
load("//bazel/rules:agent_package_signing.bzl", "signed_or_unsigned_agent_rpm")
load("//bazel/rules:file_from_flag.bzl", "file_from_flag")
load("//bazel/rules:filename_from_flag.bzl", "filename_from_flag")
load("//bazel/rules:pkg.bzl", "pkg_tar")
load("//bazel/rules:pkg_rpm_from_buildroot.bzl", "pkg_rpm_from_buildroot")
load("//bazel/rules:sign_package.bzl", "RELEASE_KEY_FINGERPRINT", "sign_package")

AGENT_PACKAGES = {
    "check-mk-agent.aarch64.rpm": "check-mk-agent-{VERSION}-1.aarch64.rpm",
    "check-mk-agent.noarch.rpm": "check-mk-agent-{VERSION}-1.noarch.rpm",
    "check-mk-agent_all.deb": "check-mk-agent_{VERSION}-1_all.deb",
    "check-mk-agent_arm64.deb": "check-mk-agent_{VERSION}-1_arm64.deb",
}

# What each AGENT_PACKAGES key resolves to: the check-mk-agent .deb/.rpm
# built below. The .rpm is only signed if --//bazel/rules:signing_key_file is
# set and signing is neither disabled nor artifacts are faked. //agents:agents
# itself is buildable without a key, but the release packages in //omd refuse
# to build with the unsigned .rpm unless signing is disabled or artifacts are
# faked, see //:agent_package_signing_missing. .deb is never signed.
_AGENT_PACKAGE_TARGETS = {
    "check-mk-agent.aarch64.rpm": signed_or_unsigned_agent_rpm(
        signed = ":check-mk-agent-rpm-aarch64_signed",
        unsigned = ":check-mk-agent-rpm-aarch64",
    ),
    "check-mk-agent.noarch.rpm": signed_or_unsigned_agent_rpm(
        signed = ":check-mk-agent-rpm_signed",
        unsigned = ":check-mk-agent-rpm",
    ),
    "check-mk-agent_all.deb": ":check-mk-agent-deb",
    "check-mk-agent_arm64.deb": ":check-mk-agent-deb-aarch64",
}

[
    filename_from_flag(
        name = package + "_with_version",
        src = _AGENT_PACKAGE_TARGETS[package],
        file_name = template,
        replacements = {
            "VERSION": "@cmk//version",
        },
    )
    for package, template in AGENT_PACKAGES.items()
]

# --- check-mk-agent .deb/.rpm (x86_64 + aarch64) ---
#
# Replaces agents/Makefile's former rpm/deb/rpm-aarch64/deb-aarch64
# targets, assembled here from Bazel-built binaries and signed via
# sign_package.bzl.

genrule(
    name = "cmk-agent-ctl-agent-pkg",
    srcs = ["//packages/cmk-agent-ctl:cmk-agent-ctl-musl"],
    outs = ["cmk-agent-ctl"],
    cmd = "cp $< $@",
)

gzip_compress(
    name = "cmk-agent-ctl-agent-pkg-gz",
    src = ":cmk-agent-ctl-agent-pkg",
)

genrule(
    name = "cmk-agent-ctl-aarch64-agent-pkg",
    srcs = ["//packages/cmk-agent-ctl:cmk-agent-ctl-musl-aarch64"],
    outs = ["cmk-agent-ctl-aarch64"],
    cmd = "cp $< $@",
)

gzip_compress(
    name = "cmk-agent-ctl-aarch64-agent-pkg-gz",
    src = ":cmk-agent-ctl-aarch64-agent-pkg",
)

pkg_files(
    name = "agent_pkg_conffile",
    srcs = ["conffiles/super-server.cfg"],
    attributes = pkg_attributes(mode = "0644"),
    prefix = "etc/check_mk",
)

pkg_files(
    name = "agent_pkg_xinetd_conf",
    srcs = ["scripts/super-server/1_xinetd/check-mk-agent"],
    # Mode preserved as committed (0755) - a quirk of the original Makefile's
    # plain `mv`, which never changed the file's mode when relocating it out
    # of the scripts tree into /etc/check_mk.
    attributes = pkg_attributes(mode = "0755"),
    prefix = "etc/check_mk",
    renames = {
        "scripts/super-server/1_xinetd/check-mk-agent": "xinetd-service-template.cfg",
    },
)

pkg_files(
    name = "agent_pkg_bin",
    srcs = [
        "check_mk_agent.linux",
        "check_mk_caching_agent.linux",
        "mk-job",
    ],
    attributes = pkg_attributes(mode = "0755"),
    prefix = "usr/bin",
    renames = {
        "check_mk_agent.linux": "check_mk_agent",
        "check_mk_caching_agent.linux": "check_mk_caching_agent",
    },
)

pkg_files(
    name = "agent_pkg_waitmax",
    srcs = ["waitmax"],
    attributes = pkg_attributes(mode = "0755"),
    prefix = "usr/bin",
)

# Globbed (not listed explicitly) so a new file under scripts/ is picked up
# automatically. systemd unit files are 0644 (agent_pkg_scripts_644 below);
# everything else here defaults to 0755. scripts/super-server/1_xinetd/
# check-mk-agent is excluded - it's relocated separately, see
# agent_pkg_xinetd_conf.
_SYSTEMD_UNIT_FILES = glob([
    "scripts/super-server/0_systemd/*.service",
    "scripts/super-server/0_systemd/*.socket*",
])

pkg_files(
    name = "agent_pkg_scripts_755",
    srcs = glob(
        ["scripts/**"],
        exclude = _SYSTEMD_UNIT_FILES + ["scripts/super-server/1_xinetd/check-mk-agent"],
    ),
    attributes = pkg_attributes(mode = "0755"),
    prefix = "var/lib/cmk-agent/scripts",
    strip_prefix = strip_prefix.from_pkg("scripts"),
)

pkg_files(
    name = "agent_pkg_scripts_644",
    srcs = _SYSTEMD_UNIT_FILES,
    attributes = pkg_attributes(mode = "0644"),
    prefix = "var/lib/cmk-agent/scripts",
    strip_prefix = strip_prefix.from_pkg("scripts"),
)

pkg_mkdirs(
    name = "agent_pkg_emptydirs",
    dirs = [
        "usr/lib/check_mk_agent/local",
        "usr/lib/check_mk_agent/plugins",
        "var/lib/check_mk_agent/cache",
        "var/lib/check_mk_agent/job",
        "var/lib/check_mk_agent/spool",
    ],
)

pkg_files(
    name = "agent_pkg_ctl_gz",
    srcs = [":cmk-agent-ctl-agent-pkg-gz"],
    attributes = pkg_attributes(mode = "0640"),
    prefix = "var/lib/cmk-agent",
)

pkg_files(
    name = "agent_pkg_ctl_gz_aarch64",
    srcs = [":cmk-agent-ctl-aarch64-agent-pkg-gz"],
    attributes = pkg_attributes(mode = "0640"),
    prefix = "var/lib/cmk-agent",
)

pkg_tar(
    name = "agent_pkg_buildroot",
    srcs = [
        ":agent_pkg_bin",
        ":agent_pkg_conffile",
        ":agent_pkg_ctl_gz",
        ":agent_pkg_emptydirs",
        ":agent_pkg_scripts_644",
        ":agent_pkg_scripts_755",
        ":agent_pkg_waitmax",
        ":agent_pkg_xinetd_conf",
    ],
    mtime = 1767744000,
    portable_mtime = False,
)

pkg_tar(
    name = "agent_pkg_buildroot_aarch64",
    srcs = [
        ":agent_pkg_bin",
        ":agent_pkg_conffile",
        ":agent_pkg_ctl_gz_aarch64",
        ":agent_pkg_emptydirs",
        ":agent_pkg_scripts_644",
        ":agent_pkg_scripts_755",
        ":agent_pkg_xinetd_conf",
    ],
    mtime = 1767744000,
    portable_mtime = False,
)

pkg_rpm_from_buildroot(
    name = "check-mk-agent-rpm",
    buildroot_tar = ":agent_pkg_buildroot",
    rpm = "check-mk-agent.rpm",
    spec = "check-mk-agent.spec",
    version = "@cmk//version",
)

pkg_rpm_from_buildroot(
    name = "check-mk-agent-rpm-aarch64",
    buildroot_tar = ":agent_pkg_buildroot_aarch64",
    rpm = "check-mk-agent-aarch64.rpm",
    spec = "check-mk-agent-aarch64.spec",
    target_arch = "aarch64",
    version = "@cmk//version",
)

sign_package(
    name = "check-mk-agent-rpm_signed",
    src = ":check-mk-agent-rpm",
    expected_fingerprint = RELEASE_KEY_FINGERPRINT,
    tags = ["manual"],
)

sign_package(
    name = "check-mk-agent-rpm-aarch64_signed",
    src = ":check-mk-agent-rpm-aarch64",
    expected_fingerprint = RELEASE_KEY_FINGERPRINT,
    tags = ["manual"],
)

# The .deb control file's real "Version:" field, resolved from @cmk//version
# (unlike pkg_deb's plain `version` attr, `version_file` can be templated
# from a build setting - see bazel/rules/file_from_flag.bzl).
file_from_flag(
    name = "agent_pkg_deb_version",
    out = "agent_pkg_deb_version.txt",
    content = ["{cmk_version}-1"],
    replace_labels = {"cmk_version": "@cmk//version"},
)

pkg_deb(
    name = "check-mk-agent-deb",
    architecture = "all",
    conffiles = [
        "/etc/check_mk/super-server.cfg",
        "/etc/check_mk/xinetd-service-template.cfg",
    ],
    data = ":agent_pkg_buildroot",
    description = "Checkmk Agent for Linux\n The Checkmk Agent for Linux provides information about the system.\n This can be used to monitor the host via Checkmk.",
    maintainer = "Checkmk GmbH",
    package = "check-mk-agent",
    postinst = "debian/control/postinst",
    preinst = "debian/control/preinst",
    prerm = "debian/control/prerm",
    priority = "extra",
    section = "System/Monitoring",
    suggests = ["time"],
    version_file = ":agent_pkg_deb_version",
)

pkg_deb(
    name = "check-mk-agent-deb-aarch64",
    architecture = "arm64",
    conffiles = [
        "/etc/check_mk/super-server.cfg",
        "/etc/check_mk/xinetd-service-template.cfg",
    ],
    data = ":agent_pkg_buildroot_aarch64",
    description = "Checkmk Agent for Linux\n The Checkmk Agent for Linux provides information about the system.\n This can be used to monitor the host via Checkmk.",
    maintainer = "Checkmk GmbH",
    package = "check-mk-agent",
    postinst = "debian/control/postinst",
    preinst = "debian/control/preinst",
    prerm = "debian/control/prerm",
    priority = "extra",
    section = "System/Monitoring",
    suggests = ["time"],
    version_file = ":agent_pkg_deb_version",
)

filegroup(
    name = "agents",
    srcs = [
        "CONTENTS",
        "check_mk_agent.aix",
        "check_mk_agent.freebsd",
        "check_mk_agent.hpux",
        "check_mk_agent.linux",
        "check_mk_agent.macosx",
        "check_mk_agent.netbsd",
        "check_mk_agent.openbsd",
        "check_mk_agent.openvms",
        "check_mk_agent.openwrt",
        "check_mk_agent.solaris",
        "check_mk_caching_agent.linux",
        "mk-job",
        "mk-job.aix",
        "mk-job.solaris",
        "waitmax",
    ] + [
        package + "_with_version"
        for package in AGENT_PACKAGES
    ],
    visibility = ["//omd:__subpackages__"],
)

filegroup(
    name = "srcs",
    srcs = [
        "scripts/manage-agent-user.sh",
        "scripts/manage-binaries.sh",
        "scripts/migrate.sh",
    ],
    visibility = ["//visibility:public"],
)

filegroup(
    name = "super-server",
    srcs = glob(["scripts/super-server/**"]),
    visibility = ["//visibility:public"],
)

sh_library(
    name = "agents_sh",
    srcs = [
        "check_mk_agent.aix",
        "check_mk_agent.freebsd",
        "check_mk_agent.hpux",
        "check_mk_agent.linux",
        "check_mk_agent.macosx",
        "check_mk_agent.netbsd",
        "check_mk_agent.openbsd",
        "check_mk_agent.openwrt",
        "check_mk_agent.solaris",
        "check_mk_caching_agent.linux",
        "debian/control/postinst",
        "debian/control/preinst",
        "debian/control/prerm",
        "mk-job",
        "mk-job.aix",
        "mk-job.solaris",
        "scripts/manage-agent-user.sh",
        "scripts/manage-binaries.sh",
        "scripts/migrate.sh",
        "scripts/super-server/0_systemd/setup",
        "scripts/super-server/1_xinetd/setup",
        "scripts/super-server/setup",
        "//agents/cfg_examples:agents_cfg_examples_sh",
    ],
    visibility = ["//visibility:public"],
)
