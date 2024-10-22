load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files", "pkg_mklink", "strip_prefix")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

pkg_files(
    name = "stunnel",
    srcs = [":skel/etc/init.d/stunnel"],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "skel/etc/init.d",
)

pkg_mklink(
    name = "stunnel-symlink",
    link_name = "skel/etc/rc.d/85-stunnel",
    target = "../init.d/stunnel",
)

pkg_files(
    name = "skel_files",
    srcs = glob(
        include = ["skel/**/*"],
        exclude = [
            "skel/etc/rc.d/85-stunnel",
            "skel/etc/init.d/stunnel",
            "**/.gitignore",
        ],
    ) + [
    ],
    strip_prefix = strip_prefix.from_pkg(""),
)

pkg_tar(
    name = "skel_dir",
    srcs = [
        "skel_files",
        "stunnel",
        "stunnel-symlink",
    ],
    extension = "tar.gz",
    package_file_name = "stunnel-skel.tar.gz",
    strip_prefix = ".",
    visibility = ["//visibility:public"],
)
