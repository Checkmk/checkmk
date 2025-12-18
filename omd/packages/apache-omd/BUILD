load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files", "pkg_mkdirs", "pkg_mklink", "strip_prefix")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

exports_files(["skel.permissions"])

pkg_files(
    # See also `//omd/packages/omd:hooks`.
    name = "omd_hooks",
    srcs = [
        "APACHE_TCP_ADDR",
        "APACHE_TCP_PORT",
    ],
    attributes = pkg_attributes(mode = "0755"),
    prefix = "lib/omd/hooks",
)

pkg_files(
    name = "share_omd",
    srcs = ["apache.conf"],
    prefix = "share/omd",
)

pkg_files(
    name = "skel_files",
    srcs = glob(
        include = ["skel/**/*"],
    ),
    strip_prefix = strip_prefix.from_pkg(""),
    tags = ["manual"],
)

pkg_mklink(
    name = "bin_htpasswd",
    link_name = "bin/htpasswd",
    tags = ["manual"],
    target = select({
        "@cmk//distro:debian": "/usr/bin/htpasswd",
        "@cmk//distro:ubuntu": "/usr/bin/htpasswd",
        "@cmk//distro:almalinux": "/usr/bin/htpasswd",
        "@cmk//distro:sles": "/usr/bin/htpasswd2",
    }),
)

[pkg_mklink(
    name = "apache_module_" + name,
    link_name = "lib/apache/modules/mod_" + name + ".so",
    tags = ["manual"],
    target = select({
        "@cmk//distro:debian": "/usr/lib/apache2/modules/mod_" + name + ".so",
        "@cmk//distro:ubuntu": "/usr/lib/apache2/modules/mod_" + name + ".so",
        "@cmk//distro:almalinux": "/usr/lib64/httpd/modules/mod_" + name + ".so",
        "@cmk//distro:sles": "/usr/lib64/apache2-prefork/mod_" + name + ".so",
    }),
) for name in [
    "access_compat",
    "alias",
    "auth_basic",
    "authn_core",
    "authn_file",
    "authz_core",
    "authz_host",
    "authz_user",
    "autoindex",
    "cgi",
    "deflate",
    "dir",
    "env",
    "expires",
    "filter",
    "headers",
    "log_config",
    "mime",
    "mime_magic",
    "mpm_prefork",
    "negotiation",
    "rewrite",
    "setenvif",
    "status",
    "unixd",
    "proxy",
    "proxy_http",
]]

pkg_mklink(
    name = "85-apache-symlink",
    link_name = "skel/etc/rc.d/85-apache",
    tags = ["manual"],
    target = "../init.d/apache",
)

pkg_mkdirs(
    name = "apache_skel_dirs",
    dirs = [
        "skel/var/log/apache",
        "skel/var/www",
        "skel/tmp/apache/run",
        "skel/tmp/php/session",
        "skel/tmp/php/upload",
        "skel/tmp/php/wsdl-cache",
    ],
)

pkg_tar(
    name = "apache-omd",
    srcs = [
        "85-apache-symlink",
        "apache_module_access_compat",
        "apache_module_alias",
        "apache_module_auth_basic",
        "apache_module_authn_core",
        "apache_module_authn_file",
        "apache_module_authz_core",
        "apache_module_authz_host",
        "apache_module_authz_user",
        "apache_module_autoindex",
        "apache_module_cgi",
        "apache_module_deflate",
        "apache_module_dir",
        "apache_module_env",
        "apache_module_expires",
        "apache_module_filter",
        "apache_module_headers",
        "apache_module_mime",
        "apache_module_mime_magic",
        "apache_module_negotiation",
        "apache_module_proxy",
        "apache_module_proxy_http",
        "apache_module_rewrite",
        "apache_module_setenvif",
        "apache_module_status",
        "skel_files",
        ":apache_skel_dirs",
        ":bin_htpasswd",
        ":omd_hooks",
        ":share_omd",
    ] + select({
        # TODO: Do we really want differences between distros?
        "@cmk//distro:debian": [
            "apache_module_mpm_prefork",
        ],
        "@cmk//distro:ubuntu": [
            "apache_module_mpm_prefork",
        ],
        "@cmk//distro:almalinux": [
            "apache_module_log_config",
            "apache_module_mpm_prefork",
            "apache_module_unixd",
        ],
        "@cmk//distro:sles": [
            "apache_module_log_config",
        ],
    }),
    stamp = 1,
    visibility = ["//omd:__subpackages__"],
)
