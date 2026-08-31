load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

package(default_visibility = [":__subpackages__"])

exports_files(["dev-requirements.in"])

py_library(
    name = "pkg_marker",
    srcs = ["__init__.py"],
    imports = [".."],
    visibility = ["//:__subpackages__"],
)

py_library(
    name = "conftest",
    testonly = True,
    srcs = ["conftest.py"],
    deps = [
        "//tests/testlib/common:repo",
        "//tests/testlib/common:utils",
        requirement("playwright"),
        requirement("pytest"),
        requirement("pytest-check"),
        requirement("pytest-metadata"),
        "//tests/testlib",
    ],
)

py_library(
    name = "bandit-nosec-markers",
    testonly = True,
    srcs = glob(
        include = ["bandit-nosec-markers/**/*.py"],
    ),
    imports = [".."],
)

py_library(
    name = "docker",
    testonly = True,
    srcs = glob(
        include = ["docker/**/*.py"],
    ),
    imports = [".."],
    deps = [
        requirement("docker"),
        requirement("pytest"),
        requirement("requests"),
        "//tests/testlib",
    ],
)

py_library(
    name = "etc",
    testonly = True,
    srcs = glob(
        include = ["etc/**/*.py"],
        allow_empty = True,
        exclude = ["etc/**/nonfree/**"],
    ) + select({
        "//:gpl+nonfree_repo": glob(
            include = ["etc/**/nonfree/**/*.py"],
            allow_empty = True,
        ),
        "//:gpl_repo": [],
    }),
    imports = [".."],
)

py_library(
    name = "packaging",
    testonly = True,
    srcs = glob(
        include = ["packaging/**/*.py"],
    ),
    imports = [".."],
    deps = [
        "//tests/testlib",
        "//tests/testlib/common:utils",
        requirement("pytest"),
    ],
)

py_library(
    name = "plugins_siteless",
    testonly = True,
    # TODO: The tests include non-free plugins (cmk.plugins.custom_query_metric_backend.special_agents.nonfree.ultimate)
    # Introduce a folder structure to separate free and non-free tests.
    srcs = select({
        "//:gpl+nonfree_repo": glob(
            include = ["plugins_siteless/**/*.py"],
        ),
        "//:gpl_repo": [],
    }),
    imports = [".."],
    deps = [
        "//tests/testlib/common:empty_config",
        "//tests/testlib/common:repo",
        requirement("pytest"),
    ],
)

py_library(
    name = "scripts",
    testonly = True,
    srcs = glob(
        include = ["scripts/**/*.py"],
        exclude = ["scripts/**/nonfree/**"],
    ) + select({
        "//:gpl+nonfree_repo": glob(
            include = ["scripts/**/nonfree/**/*.py"],
            allow_empty = True,
        ),
        "//:gpl_repo": [],
    }),
    imports = [".."],
    deps = [
        "//tests/testlib/common:repo",
        requirement("docker"),
        requirement("requests"),
        requirement("jinja2"),
        "//tests/testlib",
    ],
)

py_library(
    name = "typeshed",
    testonly = True,
    srcs = glob(
        include = ["typeshed/**/*.py"],
        allow_empty = True,
    ),
    imports = [".."],
)

sh_library(
    name = "tests_sh",
    srcs = [
        "scripts/find_modified_lock_files",
        "scripts/setup_openldap.sh",
        "scripts/setup_postfix.sh",
        "scripts/teardown_openldap.sh",
        "scripts/teardown_postfix.sh",
        "scripts/verify_test_python_files.sh",
    ],
)
