load("//bazel/rules:sign_package.bzl", "sign_package")
load(":sign_package_analysis_test.bzl", "sign_package_only_declares_src_as_input_test")

sh_test(
    name = "sign_package_failure_test",
    srcs = ["sign_package_failure_test.sh"],
    args = ["$(location //bazel/rules:sign_package.sh)"],
    data = ["//bazel/rules:sign_package.sh"],
)

sh_test(
    name = "sign_package_secret_leak_rpm_test",
    srcs = ["sign_package_secret_leak_rpm_test.sh"],
    args = ["$(location //bazel/rules:sign_package.sh)"],
    data = ["//bazel/rules:sign_package.sh"],
)

genrule(
    name = "fake_package",
    outs = ["fake.rpm"],
    cmd = "echo not-a-real-package > $@",
    tags = ["manual"],
)

sign_package(
    name = "sign_fake_package",
    src = ":fake_package",
    expected_fingerprint = "0000000000000000000000000000000000000000",
    tags = ["manual"],
)

sign_package_only_declares_src_as_input_test(
    name = "sign_package_only_declares_src_as_input_test",
    target_under_test = ":sign_fake_package",
)
