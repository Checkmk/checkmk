load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

pkg_files(
    name = "agents_linux",
    srcs = [
        "@robotmk//:artifact/micromamba/micromamba",
        "@robotmk//:artifact/rcc/linux64/rcc",
        "@robotmk//:artifact/rmk_linux64/robotmk_scheduler",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "share/check_mk/agents/robotmk/linux",
)

pkg_files(
    name = "agents_windows",
    srcs = [
        "@robotmk//:artifact/micromamba/micromamba.exe",
        "@robotmk//:artifact/rcc/windows64/rcc.exe",
        "@robotmk//:artifact/rmk_windows64/robotmk_scheduler.exe",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "share/check_mk/agents/robotmk/windows",
)

pkg_files(
    name = "plugins_linux",
    srcs = [
        "@robotmk//:artifact/rmk_linux64/robotmk_agent_plugin",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "share/check_mk/agents/plugins",
)

pkg_files(
    name = "plugins_windows",
    srcs = [
        "@robotmk//:artifact/rmk_windows64/robotmk_agent_plugin.exe",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "share/check_mk/agents/windows/plugins",
)

pkg_tar(
    name = "robotmk",
    srcs = [
        ":agents_linux",
        ":agents_windows",
        ":plugins_linux",
        ":plugins_windows",
    ],
    visibility = ["//omd:__pkg__"],
)
