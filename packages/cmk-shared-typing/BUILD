load("@aspect_bazel_lib//lib:copy_to_bin.bzl", "copy_to_bin")

# Note: this will only last for one commit
copy_to_bin(
    name = "src",
    srcs = glob(["typescript/**/*.*"]),
    visibility = ["//packages/cmk-frontend-vue:__pkg__"],
)
