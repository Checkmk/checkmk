load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

# The signed Windows agent PowerShell plugins are produced by the Windows
# signing CI job (`agents/windows/plugins:signed_plugins`) and dropped here as
# `signed_plugins.tar` (see artifacts.make). The tar contains the plugins at its
# root; we relocate them into the agent plugins folder of the site below.
#
# On builds without the Windows artifact (e.g. developer Linux builds with faked
# artifacts) an empty tar is merged instead so the build stays self-contained.
pkg_tar(
    name = "signed_plugins_fake",
    tags = ["manual"],
)

pkg_tar(
    name = "win-signed-plugins",
    package_dir = "share/check_mk/agents/windows/plugins/signed",
    stamp = 1,
    tags = ["manual"],
    visibility = ["//omd:__pkg__"],
    deps = select({
        "@//:use_fake_artifacts_enabled": [":signed_plugins_fake"],
        "//conditions:default": ["signed_plugins.tar"],
    }),
)
