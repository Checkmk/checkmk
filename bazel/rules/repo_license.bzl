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
    doc = "Detects whether the repo is pure GPL or enterprise and GPL",
)
