load("@rules_cc//cc/toolchains:args.bzl", "cc_args")

package(default_visibility = ["//visibility:public"])

# Replaces the link-time path portability that
# bazel/patches/rules_cc-drop_sanitize_pwd_env.patch removes from rules_cc's
# sanitize_pwd feature.
cc_args(
    name = "sanitize_pwd_link_args",
    actions = [
        "@rules_cc//cc/toolchains/actions:link_actions",
    ],
    args = ["-ffile-prefix-map=__BAZEL_EXECUTION_ROOT__=."],
)
