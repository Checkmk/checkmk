load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files", "pkg_mklink", "strip_prefix")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

exports_files(["skel.permissions"])

pkg_files(
    name = "rabbitmq_hooks",
    srcs = [
        "RABBITMQ_DIST_PORT",
        "RABBITMQ_MANAGEMENT_PORT",
        "RABBITMQ_ONLY_FROM",
        "RABBITMQ_PORT",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "lib/omd/hooks",
)

pkg_files(
    name = "skel",
    srcs = [
        "skel/etc/logrotate.d/rabbitmq",
        "skel/etc/rabbitmq/advanced_conf.d/00-advanced.conf",
        "skel/etc/rabbitmq/conf.d/00-default.conf",
        "skel/etc/rabbitmq/conf.d/03-tracing.conf",
        "skel/etc/rabbitmq/definitions.d/00-default.json",
        "skel/etc/rabbitmq/enabled_plugins",
    ],
    strip_prefix = strip_prefix.from_pkg(""),
)

pkg_files(
    name = "skel_755",
    srcs = [
        "skel/etc/init.d/rabbitmq",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    strip_prefix = strip_prefix.from_pkg(""),
)

pkg_mklink(
    name = "85-rabbitmq",
    link_name = "skel/etc/rc.d/85-rabbitmq",
    target = "../init.d/rabbitmq",
)

pkg_tar(
    name = "rabbitmq_lib",
    package_dir = "lib/rabbitmq",
    deps = [
        "@rabbitmq//:rabbitmq.tar.gz",
    ],
)

pkg_tar(
    name = "rabbitmq",
    srcs = [
        ":85-rabbitmq",
        ":rabbitmq_hooks",
        ":skel",
        ":skel_755",
    ],
    visibility = ["//omd:__pkg__"],
    deps = [
        "rabbitmq_lib",
    ],
)
