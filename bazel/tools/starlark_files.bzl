"""The Starlark files that //:buildifier(.check) and //:lint(.check) -- --delta cover."""

# Paths relative to the workspace, as patterns of `find -path`
STARLARK_EXCLUDED = [
    "*/build/*",
    "container_shadow_workspace_local/*",
    ".docker_workspace/*",
    "tests/qa-test-data/*",
    ".cache/*",
    "bazel/registry/*",
    "bazel/thirdparty/*",
    ".bazelbsp/*",
]

# File names, as patterns of `find -name`
STARLARK_NAMES = [
    "*.bzl",
    "*.sky",
    "BUILD.bazel",
    "BUILD",
    "*.BUILD",
    "BUILD.*.bazel",
    "BUILD.*.oss",
    "MODULE.bazel",
    "WORKSPACE",
    "WORKSPACE.bazel",
    "WORKSPACE.oss",
    "WORKSPACE.*.bazel",
    "WORKSPACE.*.oss",
]
