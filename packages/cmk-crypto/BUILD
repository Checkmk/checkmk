load("@aspect_rules_lint//format:defs.bzl", "format_multirun")
load("@aspect_rules_py//py:defs.bzl", "py_library", "py_pytest_main", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//bazel/rules:doctest.bzl", "py_doc_test")
load("//bazel/rules:package_wheel.bzl", "package_wheel")

exports_files([
    "pyproject.toml",
    "requirements.txt",
])

py_library(
    name = "cmk-crypto",
    srcs = [
        "cmk/crypto/__init__.py",
        "cmk/crypto/certificate.py",
        "cmk/crypto/deprecated.py",
        "cmk/crypto/hash.py",
        "cmk/crypto/keys.py",
        "cmk/crypto/password.py",
        "cmk/crypto/password_hashing.py",
        "cmk/crypto/pem.py",
        "cmk/crypto/secrets.py",
        "cmk/crypto/symmetric.py",
        "cmk/crypto/totp.py",
    ],
    imports = ["."],
    visibility = ["//cmk:__pkg__"],
    deps = [
        requirement("bcrypt"),
        requirement("cryptography"),
        requirement("python-dateutil"),
    ],
)

py_doc_test(
    name = "doctest",
    size = "small",
    srcs = ["cmk-crypto"],
    tags = ["no-mypy"],
)

py_pytest_main(
    name = "__test__",
    deps = [
        requirement("pytest"),
    ],
)

py_test(
    name = "unit",
    size = "small",
    srcs = glob(["tests/**/*.py"]) + [":__test__.py"],
    main = "__test__.py",
    deps = [
        ":__test__",
        ":cmk-crypto",
        requirement("cryptography"),
        requirement("pytest"),
        requirement("python-dateutil"),
        requirement("time-machine"),
    ],
)

format_multirun(
    name = "format",
    python = "@aspect_rules_lint//format:ruff",
)

py_wheel(
    name = "wheel",
    distribution = "cmk-crypto",
    strip_path_prefixes = ["packages/cmk-crypto"],
    # TODO: Duplicated from pyproject.toml
    version = "0.9.0",
    deps = [":cmk-crypto"],
)

package_wheel(
    name = "pkg_tar",
    visibility = ["//visibility:public"],
    whl = "wheel",
)
