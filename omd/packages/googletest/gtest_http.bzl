load("@bazel_tools//tools/build_defs/repo:git.bzl", "git_repository")

def googletest(commit):
    git_repository(
        name = "gtest",
        commit = commit,
        remote = "https://github.com/google/googletest.git",
    )
