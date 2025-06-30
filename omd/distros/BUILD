#TODO: Replace those *.mk files with bazel files and replace these genrules: CMK-24412
genrule(
    name = "dependencies",
    srcs = select(
        {
            "@//bazel/cmk/distro:almalinux-8": ["ALMALINUX_8.mk"],
            "@//bazel/cmk/distro:almalinux-9": ["ALMALINUX_9.mk"],
            "@//bazel/cmk/distro:debian-11": ["DEBIAN_11.mk"],
            "@//bazel/cmk/distro:debian-12": ["DEBIAN_12.mk"],
            "@//bazel/cmk/distro:sles-15sp3": ["SLES_15SP3.mk"],
            "@//bazel/cmk/distro:sles-15sp4": ["SLES_15SP4.mk"],
            "@//bazel/cmk/distro:sles-15sp5": ["SLES_15SP5.mk"],
            "@//bazel/cmk/distro:sles-15sp6": ["SLES_15SP6.mk"],
            "@//bazel/cmk/distro:ubuntu-22.04": ["UBUNTU_22.04.mk"],
            "@//bazel/cmk/distro:ubuntu-24.04": ["UBUNTU_24.04.mk"],
        },
    ),
    outs = ["dependencies.txt"],
    cmd = """
            grep -e "^OS_PACKAGES\\s\\++" $< | sed 's/^OS_PACKAGES\\s\\++=\\s\\([^[:space:]]*\\).*/\\1/' | tr '\n\r' ', ' > $@
        """,
    visibility = ["//omd:__pkg__"],
)

genrule(
    name = "distro_version_file",
    srcs = select(
        {
            "@//bazel/cmk/distro:almalinux-8": ["ALMALINUX_8.mk"],
            "@//bazel/cmk/distro:almalinux-9": ["ALMALINUX_9.mk"],
            "@//bazel/cmk/distro:debian-11": ["DEBIAN_11.mk"],
            "@//bazel/cmk/distro:debian-12": ["DEBIAN_12.mk"],
            "@//bazel/cmk/distro:sles-15sp3": ["SLES_15SP3.mk"],
            "@//bazel/cmk/distro:sles-15sp4": ["SLES_15SP4.mk"],
            "@//bazel/cmk/distro:sles-15sp5": ["SLES_15SP5.mk"],
            "@//bazel/cmk/distro:sles-15sp6": ["SLES_15SP6.mk"],
            "@//bazel/cmk/distro:ubuntu-22.04": ["UBUNTU_22.04.mk"],
            "@//bazel/cmk/distro:ubuntu-24.04": ["UBUNTU_24.04.mk"],
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
