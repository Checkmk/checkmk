load("@rules_gzip//gzip/compress:defs.bzl", "gzip_compress")
load("@rules_pkg//pkg:deb.bzl", "pkg_deb")
load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files", "pkg_mkdirs", "strip_prefix")
load("//bazel/rules:agent_package_signing.bzl", "signed_or_unsigned_agent_rpm")
load("//bazel/rules:file_from_flag.bzl", "file_from_flag")
load("//bazel/rules:filename_from_flag.bzl", "filename_from_flag")
load("//bazel/rules:installed_size_from_archive.bzl", "installed_size_from_archive")
load("//bazel/rules:pkg.bzl", "pkg_tar")
load("//bazel/rules:pkg_rpm_from_buildroot.bzl", "pkg_rpm_from_buildroot")
load("//bazel/rules:replace_lines.bzl", "replace_lines")
load("//bazel/rules:sign_package.bzl", "RELEASE_KEY_FINGERPRINT", "sign_package")

# The prebuilt packages install into the single-directory layout, the same tree
# the agent bakery builds from UnixSingleDirectoryKeeper (see
# packages/cmk-plugin-apis/cmk/bakery/internal/_common_config.py). "default" is
# the package name the bakery appends to the configured installation directory.
_INSTALL_DIR = "/opt/checkmk/agent/default"

_PACKAGE_PREFIX = _INSTALL_DIR.lstrip("/") + "/package"

_RUNTIME_PREFIX = _INSTALL_DIR.lstrip("/") + "/runtime"

_BIN_DIR = _INSTALL_DIR + "/package/bin"

# Directory modes, named after UnixSingleDirectoryKeeper's own constants.
_ACCESSIBLE_FOR_OTHERS = "0755"

# runtime and runtime/job, so that mk-job can traverse to runtime/job/<user>.
_TRAVERSABLE_FOR_OTHERS = "0751"

_FORBIDDEN_FOR_OTHERS = "0750"

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

# Scripts that branch on MK_INSTALLDIR. The bakery rewrites the line per host,
# the prebuilt packages have no bakery and rewrite it here.
_INSTALLDIR_SCRIPTS = [
    "scripts/manage-agent-user.sh",
    "scripts/manage-binaries.sh",
    "scripts/migrate.sh",
    "scripts/super-server/0_systemd/setup",
    "scripts/super-server/1_xinetd/setup",
    "scripts/super-server/setup",
]

_MK_INSTALLDIR_UNSET = ': "${MK_INSTALLDIR:=""}"'

_MK_INSTALLDIR_SET = ': "${MK_INSTALLDIR:="%s"}"' % _INSTALL_DIR

[
    replace_lines(
        name = "patched_" + script.replace("/", "_").replace(".", "_"),
        src = script,
        out = "patched/" + script,
        substitutions = {_MK_INSTALLDIR_UNSET: _MK_INSTALLDIR_SET},
    )
    for script in _INSTALLDIR_SCRIPTS
]

replace_lines(
    name = "patched_check_mk_agent",
    src = "check_mk_agent.linux",
    out = "patched/bin/check_mk_agent",
    # The agent declares its default inside set_up_single_directory(), indented.
    substitutions = {
        "    " + _MK_INSTALLDIR_UNSET: "    " + _MK_INSTALLDIR_SET,
    },
)

replace_lines(
    name = "patched_mk_job",
    src = "mk-job",
    out = "patched/bin/mk-job",
    # mk-job never reads MK_INSTALLDIR, it carries its own MK_VARDIR default.
    substitutions = {
        'MK_VARDIR="${MK_VARDIR:-/var/lib/check_mk_agent}"': 'MK_VARDIR="${MK_VARDIR:-%s/runtime}"' % _INSTALL_DIR,
    },
)

# The systemd units and the xinetd template name the agent binaries by absolute
# path. They have to point into the package, not at /usr/bin: super-server/setup
# starts them before manage-binaries.sh has registered the symlinks there, and on
# an update the old package's cleanup has already removed the classic binaries.
# The bakery solves this the same way, see get_systemd_service(),
# get_systemd_agent_ctl_service() and get_xinetd_conf() in super_server.py.
replace_lines(
    name = "patched_check_mk_agent_async_service",
    src = "scripts/super-server/0_systemd/check-mk-agent-async.service",
    out = "patched/scripts/super-server/0_systemd/check-mk-agent-async.service",
    substitutions = {
        "ExecStart=/usr/bin/check_mk_agent": "ExecStart=%s/check_mk_agent" % _BIN_DIR,
    },
)

replace_lines(
    name = "patched_check_mk_agent_service",
    src = "scripts/super-server/0_systemd/check-mk-agent@.service",
    out = "patched/scripts/super-server/0_systemd/check-mk-agent@.service",
    substitutions = {
        "ExecStart=-/usr/bin/check_mk_agent": "ExecStart=-%s/check_mk_agent" % _BIN_DIR,
    },
)

replace_lines(
    name = "patched_cmk_agent_ctl_daemon_service",
    src = "scripts/super-server/0_systemd/cmk-agent-ctl-daemon.service",
    out = "patched/scripts/super-server/0_systemd/cmk-agent-ctl-daemon.service",
    substitutions = {
        "ExecStart=/usr/bin/cmk-agent-ctl daemon": "ExecStart=%s/cmk-agent-ctl daemon" % _BIN_DIR,
    },
)

replace_lines(
    name = "patched_xinetd_service_template",
    src = "scripts/super-server/1_xinetd/check-mk-agent",
    out = "patched/config/xinetd-service-template.cfg",
    substitutions = {
        "    #server         = /usr/bin/check_mk_caching_agent": "    #server         = %s/check_mk_caching_agent" % _BIN_DIR,
        "    server         = /usr/bin/check_mk_agent": "    server         = %s/check_mk_agent" % _BIN_DIR,
    },
)

pkg_files(
    name = "agent_pkg_conffile",
    srcs = ["conffiles/super-server.cfg"],
    attributes = pkg_attributes(mode = "0644"),
    prefix = _PACKAGE_PREFIX + "/config",
)

pkg_files(
    name = "agent_pkg_xinetd_conf",
    srcs = [":patched_xinetd_service_template"],
    # Mode preserved as committed (0755) - a quirk of the original Makefile's
    # plain `mv`, which never changed the file's mode when relocating it out
    # of the scripts tree into the configuration directory.
    attributes = pkg_attributes(mode = "0755"),
    prefix = _PACKAGE_PREFIX + "/config",
    strip_prefix = strip_prefix.from_pkg("patched/config"),
)

pkg_files(
    name = "agent_pkg_bin",
    srcs = [
        "check_mk_caching_agent.linux",
        ":patched_check_mk_agent",
        ":patched_mk_job",
    ],
    attributes = pkg_attributes(mode = "0755"),
    prefix = _PACKAGE_PREFIX + "/bin",
    renames = {
        ":patched_check_mk_agent": "check_mk_agent",
        ":patched_mk_job": "mk-job",
        "check_mk_caching_agent.linux": "check_mk_caching_agent",
    },
)

pkg_files(
    name = "agent_pkg_waitmax",
    srcs = ["waitmax"],
    attributes = pkg_attributes(mode = "0755"),
    prefix = _PACKAGE_PREFIX + "/bin",
)

_SYSTEMD_SERVICE_FILES = glob(["scripts/super-server/0_systemd/*.service"])

_SYSTEMD_SOCKET_FILES = glob(["scripts/super-server/0_systemd/*.socket*"])

_SYSTEMD_UNIT_FILES = _SYSTEMD_SERVICE_FILES + _SYSTEMD_SOCKET_FILES

# Every .service file carries an ExecStart and ships patched, see
# agent_pkg_units_patched. The .socket files name no binary.
_PATCHED_UNIT_FILES = [
    "patched/scripts/super-server/0_systemd/check-mk-agent-async.service",
    "patched/scripts/super-server/0_systemd/check-mk-agent@.service",
    "patched/scripts/super-server/0_systemd/cmk-agent-ctl-daemon.service",
]

# Globbed (not listed explicitly) so a new file under scripts/ is picked up
# automatically. systemd unit files are 0644 (agent_pkg_scripts_644 below);
# everything else here defaults to 0755. scripts/super-server/1_xinetd/
# check-mk-agent is excluded - it's relocated separately, see
# agent_pkg_xinetd_conf. _INSTALLDIR_SCRIPTS are excluded - they ship patched,
# see agent_pkg_scripts_patched. Every file under scripts/ falls into one of
# these three groups today, so the glob is empty until a new one arrives.
pkg_files(
    name = "agent_pkg_scripts_755",
    srcs = glob(
        ["scripts/**"],
        allow_empty = True,
        exclude = _SYSTEMD_UNIT_FILES + _INSTALLDIR_SCRIPTS + [
            "scripts/super-server/1_xinetd/check-mk-agent",
        ],
    ),
    attributes = pkg_attributes(mode = "0755"),
    prefix = _PACKAGE_PREFIX + "/scripts",
    strip_prefix = strip_prefix.from_pkg("scripts"),
)

pkg_files(
    name = "agent_pkg_scripts_patched",
    srcs = ["patched/" + script for script in _INSTALLDIR_SCRIPTS],
    attributes = pkg_attributes(mode = "0755"),
    prefix = _PACKAGE_PREFIX + "/scripts",
    strip_prefix = strip_prefix.from_pkg("patched/scripts"),
)

pkg_files(
    name = "agent_pkg_scripts_644",
    srcs = _SYSTEMD_SOCKET_FILES,
    attributes = pkg_attributes(mode = "0644"),
    prefix = _PACKAGE_PREFIX + "/scripts",
    strip_prefix = strip_prefix.from_pkg("scripts"),
)

pkg_files(
    name = "agent_pkg_units_patched",
    srcs = _PATCHED_UNIT_FILES,
    attributes = pkg_attributes(mode = "0644"),
    prefix = _PACKAGE_PREFIX + "/scripts",
    strip_prefix = strip_prefix.from_pkg("patched/scripts"),
)

pkg_mkdirs(
    name = "agent_pkg_dirs_accessible",
    attributes = pkg_attributes(mode = _ACCESSIBLE_FOR_OTHERS),
    dirs = [
        "opt/checkmk",
        "opt/checkmk/agent",
        _INSTALL_DIR.lstrip("/"),
        _PACKAGE_PREFIX,
        _PACKAGE_PREFIX + "/bin",
        _PACKAGE_PREFIX + "/plugins",
    ],
)

pkg_mkdirs(
    name = "agent_pkg_dirs_traversable",
    attributes = pkg_attributes(mode = _TRAVERSABLE_FOR_OTHERS),
    dirs = [
        _RUNTIME_PREFIX,
        _RUNTIME_PREFIX + "/job",
    ],
)

# The agent and its plug-ins would otherwise create the last five on demand,
# readable for others.
pkg_mkdirs(
    name = "agent_pkg_dirs_forbidden",
    attributes = pkg_attributes(mode = _FORBIDDEN_FOR_OTHERS),
    dirs = [
        _PACKAGE_PREFIX + "/agent",
        _PACKAGE_PREFIX + "/config",
        _PACKAGE_PREFIX + "/local",
        _PACKAGE_PREFIX + "/scripts",
        _RUNTIME_PREFIX + "/controller",
        _RUNTIME_PREFIX + "/log",
        _RUNTIME_PREFIX + "/spool",
        _RUNTIME_PREFIX + "/cache",
        _RUNTIME_PREFIX + "/logwatch-batches",
        _RUNTIME_PREFIX + "/persisted",
        _RUNTIME_PREFIX + "/rtc_remotes",
        _RUNTIME_PREFIX + "/tmp",
    ],
)

pkg_files(
    name = "agent_pkg_ctl_gz",
    srcs = [":cmk-agent-ctl-agent-pkg-gz"],
    attributes = pkg_attributes(mode = "0640"),
    prefix = _PACKAGE_PREFIX + "/agent",
)

pkg_files(
    name = "agent_pkg_ctl_gz_aarch64",
    srcs = [":cmk-agent-ctl-aarch64-agent-pkg-gz"],
    attributes = pkg_attributes(mode = "0640"),
    prefix = _PACKAGE_PREFIX + "/agent",
)

pkg_tar(
    name = "agent_pkg_buildroot",
    srcs = [
        ":agent_pkg_bin",
        ":agent_pkg_conffile",
        ":agent_pkg_ctl_gz",
        ":agent_pkg_dirs_accessible",
        ":agent_pkg_dirs_forbidden",
        ":agent_pkg_dirs_traversable",
        ":agent_pkg_scripts_644",
        ":agent_pkg_scripts_755",
        ":agent_pkg_scripts_patched",
        ":agent_pkg_units_patched",
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
        ":agent_pkg_dirs_accessible",
        ":agent_pkg_dirs_forbidden",
        ":agent_pkg_dirs_traversable",
        ":agent_pkg_scripts_644",
        ":agent_pkg_scripts_755",
        ":agent_pkg_scripts_patched",
        ":agent_pkg_units_patched",
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

installed_size_from_archive(
    name = "agent_pkg_installed_size",
    src = ":agent_pkg_buildroot",
    out = "agent_pkg_installed_size.txt",
)

installed_size_from_archive(
    name = "agent_pkg_installed_size_aarch64",
    src = ":agent_pkg_buildroot_aarch64",
    out = "agent_pkg_installed_size_aarch64.txt",
)

pkg_deb(
    name = "check-mk-agent-deb",
    architecture = "all",
    conffiles = [
        _INSTALL_DIR + "/package/config/super-server.cfg",
        _INSTALL_DIR + "/package/config/xinetd-service-template.cfg",
    ],
    data = ":agent_pkg_buildroot",
    description = "Checkmk Agent for Linux\n The Checkmk Agent for Linux provides information about the system.\n This can be used to monitor the host via Checkmk.",
    installed_size_file = ":agent_pkg_installed_size",
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
        _INSTALL_DIR + "/package/config/super-server.cfg",
        _INSTALL_DIR + "/package/config/xinetd-service-template.cfg",
    ],
    data = ":agent_pkg_buildroot_aarch64",
    description = "Checkmk Agent for Linux\n The Checkmk Agent for Linux provides information about the system.\n This can be used to monitor the host via Checkmk.",
    installed_size_file = ":agent_pkg_installed_size_aarch64",
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
