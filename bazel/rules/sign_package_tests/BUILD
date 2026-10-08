load("//bazel/rules:sign_package.bzl", "sign_package")
load(
    ":agent_package_signing_test.bzl",
    "agent_rpm_probe",
    "release_packages_probe",
    "with_key_faked_artifacts_test",
    "with_key_signing_disabled_test",
    "with_key_test",
    "without_key_faked_artifacts_test",
    "without_key_signing_disabled_test",
    "without_key_test",
)
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

agent_rpm_probe(
    name = "agent_rpm_probe",
    tags = ["manual"],
)

release_packages_probe(
    name = "release_packages_probe",
    tags = ["manual"],
)

without_key_test(
    name = "without_key_bundles_unsigned_agent_rpm_test",
    expected = "unsigned",
    target_under_test = ":agent_rpm_probe",
)

with_key_test(
    name = "with_key_bundles_signed_agent_rpm_test",
    expected = "signed",
    target_under_test = ":agent_rpm_probe",
)

with_key_signing_disabled_test(
    name = "disabled_signing_bundles_unsigned_agent_rpm_despite_key_test",
    expected = "unsigned",
    target_under_test = ":agent_rpm_probe",
)

with_key_faked_artifacts_test(
    name = "faked_artifacts_bundle_unsigned_agent_rpm_despite_key_test",
    expected = "unsigned",
    target_under_test = ":agent_rpm_probe",
)

without_key_test(
    name = "without_key_refuses_release_packages_test",
    expected = "refused",
    target_under_test = ":release_packages_probe",
)

with_key_test(
    name = "with_key_builds_release_packages_test",
    expected = "built",
    target_under_test = ":release_packages_probe",
)

without_key_signing_disabled_test(
    name = "disabled_signing_builds_release_packages_without_key_test",
    expected = "built",
    target_under_test = ":release_packages_probe",
)

without_key_faked_artifacts_test(
    name = "faked_artifacts_build_release_packages_without_key_test",
    expected = "built",
    target_under_test = ":release_packages_probe",
)
