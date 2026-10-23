# Expose the MODULE.bazel segments whose version literals are cross-checked
# against //:package_versions.bzl by the code-quality tests.
exports_files(
    [
        "py.MODULE.bazel",
        "python_cab.MODULE.bazel",
    ],
    visibility = ["//tests/code_quality/requirements:__pkg__"],
)
