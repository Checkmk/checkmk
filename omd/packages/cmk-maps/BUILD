load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files", "pkg_mklink", "strip_prefix")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

exports_files(["skel.permissions"])

pkg_files(
    name = "skel",
    srcs = glob(
        ["skel/**/*"],
        exclude = ["skel/etc/init.d/*"],
    ),
    strip_prefix = strip_prefix.from_pkg(""),
)

pkg_files(
    name = "skel_755",
    srcs = glob(["skel/etc/init.d/*"]),
    attributes = pkg_attributes(mode = "0755"),
    strip_prefix = strip_prefix.from_pkg(""),
)

# Start before Apache (85-apache): Apache reverse-proxies /<site>/check_mk/maps
# to the daemon's socket, so the daemon must be listening first — otherwise early
# requests right after a boot/restart hit Apache before the backend is up (502).
pkg_mklink(
    name = "84-maps",
    link_name = "skel/etc/rc.d/84-maps",
    target = "../init.d/maps",
)

# The OMD config hook (on/off switch). It must be shipped as a file under
# lib/omd/hooks (mirroring liveproxyd's LIVEPROXYD.hook): omdlib only applies a
# hook's default and writes CONFIG_MAPS to site.conf for hooks whose file is
# found there. Maps ships in every edition, so the hook file is always present.
pkg_files(
    name = "omd_hook",
    srcs = ["MAPS.hook"],
    attributes = pkg_attributes(mode = "0644"),
    prefix = "lib/omd/hooks",
    renames = {"MAPS.hook": "MAPS"},
)

# Downstream packaging for Checkmk Maps: the OMD skel/hook/init glue plus the
# application wheel built upstream in //packages/cmk-maps (mirroring how
# omd/non-free/packages/cmk-liveproxyd packages //non-free/packages/cmk-liveproxyd).
pkg_tar(
    name = "pkg_tar",
    srcs = [
        ":84-maps",
        ":omd_hook",
        ":skel",
        ":skel_755",
        "//packages/cmk-maps:cmk-maps-server-pkg",
    ],
    visibility = ["//omd:__pkg__"],
    deps = [
        "//packages/cmk-maps:wheel_pkg",
    ],
)
