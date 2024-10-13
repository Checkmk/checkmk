"""Detects whether the repo is pure GPL or enterprise and GPL."""

def _repo_license_impl(repository_ctx):
    if repository_ctx.path(Label("//:non-free")).exists:
        license = "gpl+enterprise"
    else:
        license = "gpl"
    license_bzl = "license.bzl"
    repository_ctx.file(
        license_bzl,
        content = "REPO_LICENSE = %r" % license,
        executable = False,
    )
    repository_ctx.file("BUILD.bazel", 'exports_files(["' + license_bzl + '"])')

detect_repo_license = repository_rule(
    implementation = _repo_license_impl,
)
