load("@aspect_rules_py//py:defs.bzl", "py_binary", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

package(
    default_visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
)

exports_files([
    "password_store/cli.py",
])

py_library(
    name = "utils",
    srcs = glob(
        include = ["**/*.py"],
        exclude = [
            "**/community/**",
            "**/nonfree/**",
        ],
    ),
    data = [
        "werks/mail/templates/mail.txt.jinja2",
        "//cmk/utils/werks/announce/templates:j2_templates",
    ],
    visibility = [
        "//bin:__subpackages__",
        "//cmk:__subpackages__",
        "//non-free/packages:__subpackages__",
        "//omd/packages:__subpackages__",
        "//packages:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
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
        "//packages/cmk-werks",
        requirement("azure-identity"),
        requirement("azure-storage-blob"),
        requirement("boto3"),
        requirement("cryptography"),
        requirement("GitPython"),
        requirement("jinja2"),
        requirement("pillow"),
        requirement("pydantic"),
        requirement("pyopenssl"),
        requirement("python-dateutil"),
        requirement("pyyaml"),
        requirement("redis"),
        requirement("requests"),
        requirement("urllib3"),
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
    deps = [":utils"],
)
