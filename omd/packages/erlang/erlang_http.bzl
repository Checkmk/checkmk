load("@bazel_tools//tools/build_defs/repo:git.bzl", "git_repository")

def erlang(version_str):
    # TODO: I know http_archive is the way to go, but I am running into strange build issues when using http_archive:
    # The build tries to access e.g. lib/parsetools/ebin which is present in the source zip but somehow bazel removes it...
    git_repository(
        name = "erlang",
        build_file = "@omd_packages//omd/packages/erlang:BUILD",
        commit = version_str,
        remote = "https://github.com/erlang/otp/",
    )
