load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

package(default_visibility = [":__subpackages__"])

py_library(
    name = "gui_crawl",
    testonly = True,
    srcs = glob(
        include = ["**/*.py"],
    ),
    imports = ["../../.."],
    deps = [
        requirement("playwright"),
        requirement("requests"),
        requirement("lxml"),
        requirement("pytest"),
        requirement("beautifulsoup4"),
        "//scripts/html_validation",
        "//tests/system:pkg_marker",
        "//tests/testlib",
    ],
)
