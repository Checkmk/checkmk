load("//bazel/rules:write_os_dependencies.bzl", "write_os_dependencies")

exports_files([
    "ALMALINUX_8.mk",
    "ALMALINUX_9.mk",
    "ALMALINUX_10.mk",
    "DEBIAN_12.mk",
    "DEBIAN_13.mk",
    "SLES_15SP5.mk",
    "SLES_15SP6.mk",
    "SLES_15SP7.mk",
    "UBUNTU_22.04.mk",
    "UBUNTU_24.04.mk",
])

write_os_dependencies(
    name = "dependencies",
    src = select(
        {
            "@cmk//distro:almalinux-8": "ALMALINUX_8.mk",
            "@cmk//distro:almalinux-9": "ALMALINUX_9.mk",
            "@cmk//distro:almalinux-10": "ALMALINUX_10.mk",
            "@cmk//distro:debian-12": "DEBIAN_12.mk",
            "@cmk//distro:debian-13": "DEBIAN_13.mk",
            "@cmk//distro:sles-15sp5": "SLES_15SP5.mk",
            "@cmk//distro:sles-15sp6": "SLES_15SP6.mk",
            "@cmk//distro:sles-15sp7": "SLES_15SP7.mk",
            "@cmk//distro:ubuntu-22.04": "UBUNTU_22.04.mk",
            "@cmk//distro:ubuntu-24.04": "UBUNTU_24.04.mk",
        },
    ),
    out_name = "dependencies.txt",
    separator = select({
        "@cmk//distro:almalinux": " ",
        "@cmk//distro:sles": " ",
        "//conditions:default": ",",
    }),
    visibility = ["//omd:__pkg__"],
)

genrule(
    name = "distro_version_file",
    srcs = select(
        {
            "@cmk//distro:almalinux-8": ["ALMALINUX_8.mk"],
            "@cmk//distro:almalinux-9": ["ALMALINUX_9.mk"],
            "@cmk//distro:almalinux-10": ["ALMALINUX_10.mk"],
            "@cmk//distro:debian-12": ["DEBIAN_12.mk"],
            "@cmk//distro:debian-13": ["DEBIAN_13.mk"],
            "@cmk//distro:sles-15sp5": ["SLES_15SP5.mk"],
            "@cmk//distro:sles-15sp6": ["SLES_15SP6.mk"],
            "@cmk//distro:sles-15sp7": ["SLES_15SP7.mk"],
            "@cmk//distro:ubuntu-22.04": ["UBUNTU_22.04.mk"],
            "@cmk//distro:ubuntu-24.04": ["UBUNTU_24.04.mk"],
        },
    ),
    outs = ["distro_version_file.txt"],
    cmd = """
            DISTRO_CODE=$$(grep -e "^DISTRO_CODE" $< | sed 's/^DISTRO_CODE\\s\\+=\\s\\([^[:space:]]*\\).*/\\1/')
            PREFIX=""
            POSTFIX=""
            if echo "$<" | grep "UBUNTU\\|DEBIAN"; then PREFIX="0."; fi
            if echo "$<" | grep "SLES\\|ALMALINUX"; then POSTFIX="-38"; fi

            echo "$$PREFIX$$DISTRO_CODE$$POSTFIX" > $@
        """,
    visibility = ["//omd:__pkg__"],
)
