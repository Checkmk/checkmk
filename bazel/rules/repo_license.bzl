"""Detects whether the repo is pure GPL or enterprise and GPL."""

load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

def _is_non_free_repo(repository_ctx):
    return repository_ctx.path(Label("//:non-free")).exists

def _repo_license_impl(repository_ctx):
    if _is_non_free_repo(repository_ctx):
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

def _http_archive_non_free_impl(repository_ctx):
    if not _is_non_free_repo(repository_ctx):
        return
    http_archive(
        name = repository_ctx.attr.name,
        build_file = repository_ctx.attr.build_file,
        sha256 = repository_ctx.attr.sha256,
        urls = repository_ctx.attr.urls,
    )

http_archive_non_free = repository_rule(
    implementation = _http_archive_non_free_impl,
    attrs = {
        "build_file": attr.string(mandatory = True),
        "sha256": attr.string(mandatory = True),
        "urls": attr.string_list(mandatory = True),
    },
)
