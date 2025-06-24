load("@rules_pkg//pkg:mappings.bzl", "pkg_files", "pkg_mkdirs", "strip_prefix")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

exports_files(["skel.permissions"])

pkg_files(
    name = "skel",
    srcs = [
        "skel/etc/logrotate.d/redis",
        "skel/etc/redis/redis.conf",
    ],
    strip_prefix = strip_prefix.from_pkg(""),
)

pkg_files(
    name = "share",
    srcs = [
        "@nagvis//:share_fg",
    ],
    prefix = "share/nagvis/htdocs",
    strip_prefix = strip_prefix.from_pkg("share"),
)

pkg_files(
    name = "NagVisCompressed_js",
    srcs = [
        "@nagvis//:NagVisCompressed_js",
    ],
    prefix = "share/nagvis/htdocs/frontend/nagvis-js/js",
)

pkg_files(
    name = "doc_general",
    srcs = [
        "@nagvis//:doc_general_fg",
    ],
    prefix = "share/doc/nagvis",
)

pkg_files(
    name = "doc_de",
    srcs = [
        "@nagvis//:doc_de_fg",
    ],
    prefix = "share/nagvis/htdocs/docs/de_DE",
    strip_prefix = "docs/de_DE",
)

pkg_files(
    name = "doc_en",
    srcs = [
        "@nagvis//:doc_en_fg",
    ],
    prefix = "share/nagvis/htdocs/docs/en_US",
    strip_prefix = "docs/en_US",
)

pkg_files(
    name = "general",
    srcs = [
        "@nagvis//:general",
    ],
    prefix = "share/nagvis/htdocs/docs/general",
    strip_prefix = "docs/general",
)

pkg_files(
    name = "skel_etc",
    srcs = [
        "skel/etc/apache/conf.d/nagvis.conf",
        "skel/etc/nagvis/apache.conf",
        "skel/etc/nagvis/conf.d/omd.ini.php",
        "@nagvis//:etc/conf.d/demo.ini.php",
        "@nagvis//:etc/geomap/demo-locations.csv",
    ],
    renames = {
        "@nagvis//:etc/geomap/demo-locations.csv": "skel/etc/nagvis/geomap/demo-locations.csv",
        "@nagvis//:etc/conf.d/demo.ini.php": "skel/etc/nagvis/conf.d/demo.ini.php",
    },
    strip_prefix = strip_prefix.from_pkg(""),
)

pkg_mkdirs(
    name = "var_dir",
    dirs = ["share/nagvis/htdocs/var"],
)

pkg_mkdirs(
    name = "userfiles_empty_dirs",
    dirs = [
        "share/nagvis/htdocs/userfiles/images/gadgets",
        "share/nagvis/htdocs/userfiles/styles",
    ],
)

pkg_mkdirs(
    name = "skel_local",
    dirs = [
        "skel/local/share/nagvis/htdocs/server/core/classes/objects",
        "skel/local/share/nagvis/htdocs/userfiles/gadgets",
        "skel/local/share/nagvis/htdocs/userfiles/images/iconsets",
        "skel/local/share/nagvis/htdocs/userfiles/images/maps",
        "skel/local/share/nagvis/htdocs/userfiles/images/shapes",
        "skel/local/share/nagvis/htdocs/userfiles/scripts",
        "skel/local/share/nagvis/htdocs/userfiles/styles",
        "skel/local/share/nagvis/htdocs/userfiles/templates",
    ],
)

pkg_mkdirs(
    name = "skel_tmp",
    dirs = [
        "skel/tmp/nagvis/share",
        "skel/tmp/nagvis/tmpl/cache",
        "skel/tmp/nagvis/tmpl/compile",
    ],
)

pkg_files(
    name = "nagvis_ini_skel",
    srcs = [
        "@nagvis//:etc/nagvis.ini.php-sample",
    ],
    renames = {"@nagvis//:etc/nagvis.ini.php-sample": "skel/etc/nagvis/nagvis.ini.php"},
)

pkg_mkdirs(
    name = "skel_var",
    dirs = [
        "skel/var/nagvis/profiles",
    ],
)

pkg_mkdirs(
    name = "skel_etc_dirs",
    dirs = [
        "skel/etc/nagvis/maps",
        "skel/etc/nagvis/geomap",
    ],
)

pkg_tar(
    name = "pkg_tar",
    srcs = [
        "NagVisCompressed_js",
        "doc_de",
        "doc_en",
        "doc_general",
        "general",
        "nagvis_ini_skel",
        "share",
        "skel_etc",
        "skel_etc_dirs",
        "skel_local",
        "skel_tmp",
        "skel_var",
        "userfiles_empty_dirs",
        "var_dir",
    ],
    visibility = ["//omd:__pkg__"],
)
