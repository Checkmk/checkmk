load("@rules_pkg//pkg:mappings.bzl", "pkg_files", "strip_prefix")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

# The signed Windows agent PowerShell plugins are produced by the Windows
# signing CI job (`agents/windows/plugins:signed_plugins`) and dropped here as
# `signed_plugins.tar` (see artifacts.make). The tar is shipped verbatim into
# the version tree; the OMD install scripts (omd/debian/postinst.in and the
# %post section of omd/omd.spec.in) unpack it in place at install time.
#
# When the artifact is absent (Linux/Windows dev builds without signing) a
# zero-size placeholder is shipped instead. Its zero size makes the install-time
# unpack skip it (the scripts guard on a non-empty file).
SIGNED_PLUGINS_TAR = glob(
    ["*.tar"],
    allow_empty = True,
)

genrule(
    name = "zero_signed_plugins_tar",
    outs = ["zero/signed_plugins.tar"],
    cmd = "touch $@",
)

pkg_files(
    name = "win-signed-plugins_files",
    srcs = SIGNED_PLUGINS_TAR or [":zero_signed_plugins_tar"],
    prefix = "share/check_mk/agents/windows/plugins/signed",
    strip_prefix = strip_prefix.files_only(),
    tags = ["manual"],
)

pkg_tar(
    name = "win-signed-plugins",
    srcs = [":win-signed-plugins_files"],
    visibility = ["//omd:__pkg__"],
)
