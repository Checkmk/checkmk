load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

package(default_visibility = ["//:__subpackages__"])

py_library(
    name = "testlib",
    srcs = glob(
        include = ["**/*.py"],
        exclude = [
            "consolidation_wire.py",  # dedicated target :consolidation_wire (extra shared-typing dep)
            "fake_site.py",
        ],
    ),
    data = glob(
        include = ["**"],
        allow_empty = True,
        exclude = ["**/*.py"],
    ),
    imports = ["../.."],
    visibility = ["//:__subpackages__"],
    deps = [
        "//cmk/base",
        "//cmk/gui:core_toolkit",
        "//cmk/gui/graphing",
        "//cmk/gui/openapi:openapi_init",
        "//cmk/gui/openapi/endpoints",
        "//cmk/gui/openapi/framework",
        "//cmk/gui/openapi/restful_objects:type_defs",
        "//cmk/gui/openapi/spec/editions",
        "//cmk/gui/rest_api_types:notifications",
        "//cmk/gui/watolib",
        "//cmk/utils",
        "//packages/cmk-ccc:version",
        "//packages/cmk-relay-protocols",
        "//tests:pkg_marker",
        "//tests/testlib/common:repo",
        "//tests/testlib/common:utils",
        requirement("beautifulsoup4"),
        requirement("checkmk-dev-tools"),
        requirement("clickhouse-connect"),
        requirement("cryptography"),
        requirement("docker"),
        requirement("dockerpty"),
        requirement("fastapi"),
        requirement("flask"),
        requirement("pexpect"),
        requirement("playwright"),
        requirement("psutil"),
        requirement("pyjwt"),
        requirement("pyyaml"),
        requirement("pytest"),
        requirement("pytest-check"),
        requirement("pytest-mock"),
        requirement("requests"),
    ],
)

py_library(
    name = "rest_api_client",
    testonly = True,
    srcs = ["rest_api_client.py"],
    imports = ["../.."],
    visibility = ["//:__subpackages__"],
    deps = [
        "//cmk/gui:core_toolkit",
        "//cmk/gui/graphing",
        "//cmk/gui/openapi:openapi_init",
        "//cmk/gui/openapi/endpoints",
        "//cmk/gui/openapi/framework",
        "//cmk/gui/openapi/restful_objects:type_defs",
        "//cmk/gui/openapi/spec/editions",
        "//cmk/gui/rest_api_types:notifications",
        "//packages/cmk-crash:crash",
        requirement("requests"),
    ],
)

py_library(
    name = "consolidation_wire",
    testonly = True,
    srcs = ["consolidation_wire.py"],
    imports = ["../.."],
    visibility = ["//:__subpackages__"],
    deps = [
        "//packages/cmk-shared-typing:cmk_shared_typing_py",
    ],
)

py_library(
    name = "fake_site",
    testonly = True,
    srcs = [
        "fake_site.py",
    ],
    imports = ["../.."],
    visibility = ["//:__subpackages__"],
    deps = [
        "//cmk/utils",
        "//cmk/utils:redis",
        "//packages/cmk-ccc:debug",
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:version",
        "//packages/cmk-crash:crash",
        "//packages/cmk-crypto",
        "//packages/cmk-livestatus-client:py_livestatus",
        "//tests:pkg_marker",
        "//tests/testlib/common:repo",
        requirement("fakeredis"),
        requirement("pytest"),
    ],
)

py_library(
    name = "testlib_system_level",
    testonly = True,
    srcs = glob(
        include = ["**/*.py"],
        exclude = [
            "consolidation_wire.py",  # dedicated target :consolidation_wire (extra shared-typing dep)
            "fake_site.py",
            "unit/**",
        ],
    ),
    data = glob(
        include = ["**"],
        allow_empty = True,
        exclude = ["**/*.py"],
    ),
    imports = ["../.."],
    deps = [
        "//cmk/base",
        "//cmk/gui:core_toolkit",
        "//cmk/gui/graphing",
        "//cmk/gui/openapi:openapi_init",
        "//cmk/gui/openapi/endpoints",
        "//cmk/gui/openapi/framework",
        "//cmk/gui/openapi/restful_objects:type_defs",
        "//cmk/gui/openapi/spec/editions",
        "//cmk/gui/rest_api_types:notifications",
        "//cmk/gui/watolib",
        "//cmk/utils",
        "//packages/cmk-ccc:version",
        "//packages/cmk-relay-protocols",
        "//tests:pkg_marker",
        "//tests/testlib/common:repo",
        "//tests/testlib/common:utils",
        requirement("beautifulsoup4"),
        requirement("checkmk-dev-tools"),
        requirement("clickhouse-connect"),
        requirement("cryptography"),
        requirement("docker"),
        requirement("dockerpty"),
        requirement("fastapi"),
        requirement("pexpect"),
        requirement("playwright"),
        requirement("psutil"),
        requirement("pyjwt"),
        requirement("pytest"),
        requirement("pytest-check"),
        requirement("pyyaml"),
        requirement("requests"),
    ],
)
