load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")
load("//bazel/rules:py_requirements_test.bzl", "py_requirements_test")

exports_files([
    "dev-requirements.in",
    "requirements.in",
])

py_library(
    name = "cmk-dev-site",
    srcs = [
        "cmk_dev_site/__init__.py",
        "cmk_dev_site/cmk/__init__.py",
        "cmk_dev_site/cmk/rest_api.py",
        "cmk_dev_site/cmk_dev_install.py",
        "cmk_dev_site/cmk_dev_install_site.py",
        "cmk_dev_site/cmk_dev_site.py",
        "cmk_dev_site/omd/__init__.py",
        "cmk_dev_site/saas/__init__.py",
        "cmk_dev_site/saas/config.py",
        "cmk_dev_site/saas/constants.py",
        "cmk_dev_site/saas/oidc_service.py",
        "cmk_dev_site/utils/__init__.py",
        "cmk_dev_site/utils/cli.py",
        "cmk_dev_site/utils/log.py",
        "cmk_dev_site/utils/update_check.py",
        "cmk_dev_site/version.py",
    ],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        requirement("checkmk-dev-tools"),
        requirement("cryptography"),
        requirement("fastapi"),
        requirement("pydantic"),
        requirement("pyjwt"),
        requirement("python-multipart"),
        requirement("requests"),
        requirement("uvicorn"),
    ],
)

py_cmk_test(
    name = "unit",
    size = "small",
    srcs = glob(["tests/**/*.py"]),
    data = [
        "//scripts:cmk-dev-install.py",
        "//scripts:cmk-dev-install-site.py",
        "//scripts:cmk-dev-site.py",
        "//scripts:cmk-dev-site-mock-auth.py",
    ],
    deps = [
        ":cmk-dev-site",
        requirement("fastapi"),
        requirement("pyjwt"),
    ],
)

py_requirements_test(
    name = "requirements-test",
    known_undeclared = [
        "cmk-dev-site",  # this package's own module, named like the PyPI wheel pulled in by cmk-werk-zeug
    ],
    known_unused = [
        "python-multipart",  # imported by fastapi for form data, not by cmk_dev_site
    ],
    libs = [
        ":cmk-dev-site",
    ],
    requirements_in = "requirements.in",
)
