load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files", "pkg_mkdirs", "pkg_mklink", "strip_prefix")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("//bazel/rules:file_from_flag.bzl", "file_from_flag")
load("//bazel/rules:replace_string_in_file.bzl", "replace_string_in_file")

exports_files([
    "use_system_openssl",
    "skel.permissions",
])

# Make it possible to replace OMD_VERSION by labels
replace_string_in_file(
    name = "omd_main_in",
    src = "omd.bin",
    out = "bin/omd_in",
    replace_dict = {
        "###OMD_VERSION###": "{CMK_VERSION}.{CMK_EDITION}",
    },
)

file_from_flag(
    name = "omd_main",
    src = "omd_main_in",
    out = "bin/omd",
    replace_labels = {
        "CMK_VERSION": "@cmk//version",
        "CMK_EDITION": "@cmk//edition",
    },
)

pkg_files(
    name = "omd_main_pkg",
    srcs = [":omd_main"],
    attributes = pkg_attributes(mode = "0755"),
    prefix = "bin",
)

# SUP-10161: our openssl is incompatible with some system executables on various sles15sp*
# SUP-26565: Getting an exception error when baking agent almalinux-9+
# SUP-26879: Wrap other tools commonly used by users that require linking to the system openssl
# etc.
WRAPPED_EXECUTABLES = [
    "curl",
    "dig",
    "host",
    "nc",
    "nmap",
    "nslookup",
    "pdftoppm",
    "php",
    "php-cgi",
    "php5",
    "php5-cgi",
    "resolvectl",
    "rpmbuild",
    "scp",
    "ssh",
    "systemctl",
    "zypper",
]

[pkg_files(
    name = "wrapper_" + executable,
    srcs = ["use_system_openssl"],
    attributes = pkg_attributes(mode = "0755"),
    prefix = "bin",
    renames = {"use_system_openssl": executable},
) for executable in WRAPPED_EXECUTABLES]

genrule(
    name = "omd_man_gz",
    srcs = ["omd.8"],
    outs = ["omd.8.gz"],
    cmd = "gzip -n -f -c $(location omd.8) > $@",
)

pkg_files(
    name = "man",
    srcs = [":omd_man_gz"],
    prefix = "share/man/man8",
)

replace_string_in_file(
    name = "omd_init",
    src = "omd.init",
    out = "share/omd/omd.init",
    replace_dict = select({
        "@cmk//distro:sles": {"{DEFAULT_RUNLEVELS}": "2 3 5"},
        "//conditions:default": {"{DEFAULT_RUNLEVELS}": "2 3 4 5"},
    }),
)

pkg_files(
    name = "omd_init_pkg",
    srcs = [":omd_init"],
    attributes = pkg_attributes(mode = "0755"),
    prefix = "share/omd",
)

pkg_files(
    name = "omd_service",
    srcs = ["omd.service"],
    prefix = "share/omd",
)

pkg_files(
    name = "doc",
    srcs = [
        "COPYING",
        "README",
    ],
    prefix = "share/doc",
)

pkg_files(
    name = "lib",
    srcs = [
        "bash_completion",
        "init_profile",
    ],
    prefix = "lib/omd",
)

# Make it possible to replace OMD_VERSION by labels
replace_string_in_file(
    name = "restart_site_apache_in",
    src = "restart_site_apache",
    out = "lib/omd/restart_site_apache_in",
    replace_dict = {
        "###OMD_VERSION###": "{CMK_VERSION}.{CMK_EDITION}",
    },
)

file_from_flag(
    name = "restart_site_apache_omd_version",
    src = ":restart_site_apache_in",
    out = "lib/omd/restart_site_apache",
    replace_labels = {
        "CMK_VERSION": "@cmk//version",
        "CMK_EDITION": "@cmk//edition",
    },
)

pkg_files(
    name = "lib_755",
    srcs = [
        "next_free_port",
        ":restart_site_apache_omd_version",
    ],
    attributes = pkg_attributes(mode = "0755"),
    prefix = "lib/omd",
)

pkg_files(
    name = "hooks",
    srcs = [
        "hooks/ADMIN_MAIL",
        "hooks/APACHE_MODE",
        "hooks/AUTOSTART",
        "hooks/CORE",
        "hooks/TMPFS",
    ],
    attributes = pkg_attributes(mode = "0755"),
    prefix = "lib/omd/hooks",
)

file_from_flag(
    name = "omdlib_init",
    src = "omdlib/__template_init__.py",
    out = "omdlib/__init__.py",
    replace_labels = {
        "CMK_VERSION": "@cmk//version",
        "CMK_EDITION": "@cmk//edition",
    },
)

py_library(
    name = "omdlib",
    srcs = [
        "omdlib/backup.py",
        "omdlib/config_hooks.py",
        "omdlib/console.py",
        "omdlib/contexts.py",
        "omdlib/crash_reporting.py",
        "omdlib/dialog.py",
        "omdlib/finalize.py",
        "omdlib/global_options.py",
        "omdlib/init_scripts.py",
        "omdlib/instance_id.py",
        "omdlib/main.py",
        "omdlib/options.py",
        "omdlib/package_manager.py",
        "omdlib/restore.py",
        "omdlib/scripts.py",
        "omdlib/site_name.py",
        "omdlib/site_paths.py",
        "omdlib/sites.py",
        "omdlib/skel_permissions.py",
        "omdlib/system_apache.py",
        "omdlib/tmpfs.py",
        "omdlib/type_defs.py",
        "omdlib/update.py",
        "omdlib/update_check.py",
        "omdlib/user_processes.py",
        "omdlib/users_and_groups.py",
        "omdlib/utils.py",
        "omdlib/version.py",
        "omdlib/version_info.py",
        "omdlib_init",
    ],
    imports = ["."],
    visibility = ["//:__subpackages__"],
    deps = [
        "//cmk:lib_cmk",
        "//packages/cmk-ccc:archive",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:resulttype",
        "//packages/cmk-ccc:version",
        requirement("psutil"),
    ],
)

pkg_files(
    name = "omdlib_pkg",
    srcs = [":omdlib"],
    prefix = "lib/python3/omdlib",
)

pkg_files(
    name = "skel",
    srcs = [
        "skel/.bashrc",
        "skel/.profile",
        "skel/etc/apache/conf.d/auth.conf",
        "skel/etc/apache/conf.d/var_www.conf",
        "skel/etc/environment",
        "skel/etc/init.d/xinetd",
        "skel/etc/init-hooks.d/README",
        "skel/etc/init-hooks.d/sample-start-pre",
        "skel/etc/logrotate.d/agent-receiver",
        "skel/etc/logrotate.d/agent-registration",
        "skel/etc/logrotate.d/automation-helper",
        "skel/etc/logrotate.d/update",
        "skel/etc/logrotate.d/xinetd",
        "skel/etc/xinetd.conf",
    ],
    strip_prefix = strip_prefix.from_pkg(""),
)

pkg_mklink(
    name = "bash_completion_link",
    link_name = "skel/etc/bash_completion.d/bash_completion",
    target = "../../lib/omd/bash_completion",
)

pkg_mklink(
    name = "xinetd_link",
    link_name = "skel/etc/rc.d/90-xinetd",
    target = "../init.d/xinetd",
)

pkg_mkdirs(
    name = "empty_dirs",
    dirs = [
        "lib/omd/scripts/post-create",
        "skel/.restore_working_dir",
        "skel/etc/omd",
        "skel/etc/xinetd.d",
        "skel/local/bin",
        "skel/local/lib",
        "skel/local/lib/python3",
        "skel/local/lib/apache",
        "skel/local/lib/python",
        "skel/var/ssl",
        "skel/var/log",
        "skel/var/log/agent-receiver",
        "skel/tmp/lock",
        "skel/tmp/run",
    ],
)

pkg_tar(
    name = "omd",
    srcs = [
        ":bash_completion_link",
        ":doc",
        ":empty_dirs",
        ":hooks",
        ":lib",
        ":lib_755",
        ":man",
        ":omd_init_pkg",
        ":omd_main_pkg",
        ":omd_service",
        ":omdlib_pkg",
        ":skel",
        ":xinetd_link",
    ] + select({
        "@cmk//distro:incompatible-openssl": ["wrapper_" + executable for executable in WRAPPED_EXECUTABLES],
        "//conditions:default": [],
    }),
    stamp = 1,
    visibility = ["//omd:__pkg__"],
)
