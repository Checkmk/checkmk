load("@aspect_rules_py//py:defs.bzl", "py_binary", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

package(
    default_visibility = [
        "//cmk:__subpackages__",
        "//non-free/tests:__subpackages__",
        "//tests:__subpackages__",
    ],
)

exports_files([
    "password_store/cli.py",
])

py_library(
    name = "paths",
    srcs = ["paths.py"],
    visibility = [
        "//bin:__subpackages__",
        "//cmk:__subpackages__",
        "//non-free/packages:__subpackages__",
        "//non-free/tests:__subpackages__",
        "//omd/packages:__subpackages__",
        "//packages:__subpackages__",
        "//tests:__subpackages__",
    ],
)

py_library(
    name = "encryption",
    srcs = ["encryption.py"],
    visibility = [
        "//bin:__subpackages__",
        "//cmk:__subpackages__",
        "//non-free/packages:__subpackages__",
        "//non-free/tests:__subpackages__",
        "//omd/packages:__subpackages__",
        "//packages:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-crypto",
        requirement("pyopenssl"),
    ],
)

py_library(
    name = "images",
    srcs = ["images.py"],
    visibility = [
        "//bin:__subpackages__",
        "//cmk:__subpackages__",
        "//non-free/packages:__subpackages__",
        "//non-free/tests:__subpackages__",
        "//omd/packages:__subpackages__",
        "//packages:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        requirement("pillow"),
    ],
)

py_library(
    name = "msi_patch",
    srcs = [
        "msi_engine.py",
        "msi_patch.py",
    ],
    visibility = [
        "//bin:__subpackages__",
        "//cmk:__subpackages__",
        "//non-free/packages:__subpackages__",
        "//non-free/tests:__subpackages__",
        "//omd/packages:__subpackages__",
        "//packages:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//packages/cmk-ccc:version",
        requirement("pyyaml"),
    ],
)

py_library(
    name = "redis",
    srcs = [
        "caching_redis.py",
        "redis.py",
    ],
    visibility = [
        "//bin:__subpackages__",
        "//cmk:__subpackages__",
        "//non-free/packages:__subpackages__",
        "//non-free/tests:__subpackages__",
        "//omd/packages:__subpackages__",
        "//packages:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":paths",
        "//packages/cmk-ccc:exceptions",
        requirement("redis"),
    ],
)

py_library(
    name = "unixsocket_http",
    srcs = ["unixsocket_http.py"],
    visibility = [
        "//bin:__subpackages__",
        "//cmk:__subpackages__",
        "//non-free/packages:__subpackages__",
        "//non-free/tests:__subpackages__",
        "//omd/packages:__subpackages__",
        "//packages:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        requirement("requests"),
        requirement("urllib3"),
    ],
)

py_library(
    name = "werks",
    srcs = glob(["werks/**/*.py"]),
    data = [
        "werks/mail/templates/mail.txt.jinja2",
        "//cmk/utils/werks/announce/templates:j2_templates",
    ],
    visibility = [
        "//bin:__subpackages__",
        "//cmk:__subpackages__",
        "//non-free/packages:__subpackages__",
        "//non-free/tests:__subpackages__",
        "//omd/packages:__subpackages__",
        "//packages:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":utils",
        "//packages/cmk-ccc:store",
        "//packages/cmk-ccc:version",
        "//packages/cmk-werks",
        requirement("GitPython"),
        requirement("jinja2"),
    ],
)

py_library(
    name = "utils",
    srcs = glob(
        include = ["**/*.py"],
        exclude = [
            "**/community/**",
            "**/nonfree/**",
            "caching_redis.py",
            "encryption.py",
            "images.py",
            "msi_engine.py",
            "msi_patch.py",
            "paths.py",
            "redis.py",
            "unixsocket_http.py",
            "werks/**",
        ],
    ),
    visibility = [
        "//bin:__subpackages__",
        "//cmk:__subpackages__",
        "//non-free/packages:__subpackages__",
        "//non-free/tests:__subpackages__",
        "//omd/packages:__subpackages__",
        "//packages:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":paths",
        "//packages/cmk-ccc:config-path",
        "//packages/cmk-ccc:debug",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:i18n",
        "//packages/cmk-ccc:plugin-registry",
        "//packages/cmk-ccc:regex",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:store",
        "//packages/cmk-ccc:tty",
        "//packages/cmk-ccc:user",
        "//packages/cmk-ccc:version",
        "//packages/cmk-crypto",
        "//packages/cmk-events",
        "//packages/cmk-licensing",
        "//packages/cmk-livestatus-client:py_livestatus",
        "//packages/cmk-plugin-apis:agent_based",
        "//packages/cmk-plugin-apis:password_store",
        "//packages/cmk-trace",
        "//packages/cmk-web",
        requirement("cryptography"),
        requirement("pydantic"),
        requirement("python-dateutil"),
    ],
)

py_library(
    name = "community",
    srcs = glob(
        include = ["**/community/**/*.py"],
        allow_empty = True,
    ),
    imports = ["../.."],
)

py_library(
    name = "pro",
    srcs = glob(
        include = ["**/nonfree/**/pro/**/*.py"],
        allow_empty = True,
    ),
    imports = ["../.."],
    visibility = [
        "//cmk:__subpackages__",
        "//non-free/packages/cmk-dcd:__pkg__",
        "//non-free/packages/cmk-liveproxyd:__pkg__",
        "//non-free/packages/cmk-robotmk:__pkg__",
        "//omd:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        ":utils",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:i18n",
        "//packages/cmk-ccc:resulttype",
        "//packages/cmk-ccc:store",
        "//packages/cmk-ccc:version",
        "//packages/cmk-crypto",
        "//packages/cmk-licensing",
        "//packages/cmk-livestatus-client:py_livestatus",
        requirement("pydantic"),
        requirement("python-dateutil"),
    ],
)

py_library(
    name = "ultimate",
    srcs = glob(
        include = ["**/nonfree/**/ultimate/**/*.py"],
        allow_empty = True,
    ),
    imports = ["../.."],
    deps = [
        ":utils",
        "//packages/cmk-ccc:resulttype",
        requirement("python-dateutil"),
    ],
)

py_binary(
    name = "werks_bin",
    srcs = ["werks/__main__.py"],
    tags = ["manual"],
    visibility = ["//visibility:public"],
    deps = [":werks"],
)
