"""Repository rule for extracting snap7 7z archives.

This rule handles the extraction of snap7 source archives from SourceForge,
which are distributed as 7z files not natively supported by Bazel.

Downloads 7zip binary from official source and extracts it.
"""

_SNAP7_EXTRACT_DIR_NAME = "extracted"
_SEVEN_ZIP_EXTRACT_DIR_NAME = "7zip"
_SEVEN_ZIP_VERSION = "25.01"
_SEVEN_ZIP_ARCHIVE_TYPE = "tar.xz"
_SEVEN_ZIP_SHA256 = "4ca3b7c6f2f67866b92622818b58233dc70367be2f36b498eb0bdeaaa44b53f4"
_SEVEN_ZIP_BINARY = "7zz"

def _get_7zip_url():
    """Get the 7zip download URL constructed from version and archive type."""
    version_no_dot = _SEVEN_ZIP_VERSION.replace(".", "")
    return "https://www.7-zip.org/a/7z{}-linux-x64.{}".format(version_no_dot, _SEVEN_ZIP_ARCHIVE_TYPE)

def _download_7zip(repository_ctx):
    """Download and extract 7zip binary from official source."""
    url = _get_7zip_url()
    result = repository_ctx.download_and_extract(
        url = url,
        type = _SEVEN_ZIP_ARCHIVE_TYPE,
        sha256 = _SEVEN_ZIP_SHA256,
        output = _SEVEN_ZIP_EXTRACT_DIR_NAME,
    )
    if not result.success:
        fail("Failed to download and extract 7zip archive from {}: {}".format(
            url,
            result.error,
        ))

    # Verify the binary exists and is executable.
    extracted_bin_path = repository_ctx.path(_SEVEN_ZIP_EXTRACT_DIR_NAME).get_child(_SEVEN_ZIP_BINARY)
    extracted_bin_path_str = str(extracted_bin_path)
    if not extracted_bin_path.exists:
        fail("7zip binary '{}' not found after extraction".format(extracted_bin_path_str))

    return extracted_bin_path

def _extract_archive(repository_ctx, archive_path, extract_dir, seven_zip):
    """Extract the 7z archive to the specified directory."""
    extract_cmd = [str(seven_zip), "x", "-y", "-o{}".format(str(extract_dir)), str(archive_path)]
    result = repository_ctx.execute(extract_cmd)
    if result.return_code != 0:
        fail("Failed to extract archive '{}' to '{}'. Command: '{}'. Error: {}".format(
            archive_path,
            extract_dir,
            " ".join(extract_cmd),
            result.stderr,
        ))

    # Clean up the downloaded 7zip binary.
    repository_ctx.delete(_SEVEN_ZIP_EXTRACT_DIR_NAME)

def _move_extracted_files_to_root(repository_ctx, extract_dir):
    """Move extracted files to repository root, stripping the top-level directory."""
    entries = repository_ctx.path(extract_dir).readdir()

    # Snap7 archives always have exactly one top-level directory
    top_level_dir = entries[0]
    subentries = top_level_dir.readdir()

    # Move each item from the top-level directory to repository root
    for item in subentries:
        repository_ctx.rename(item, item.basename)

    # Remove the now-empty top-level directory
    repository_ctx.delete(top_level_dir)

    # Remove the now-empty extracted directory
    repository_ctx.delete(extract_dir)

def _snap7_repository_impl(repository_ctx):
    """Implementation of the snap7 repository rule."""

    repository_ctx.report_progress("Downloading 7zip binary")
    seven_zip = _download_7zip(repository_ctx)

    repository_ctx.report_progress("Extracting snap7 archive")
    archive_path = repository_ctx.path(repository_ctx.attr.archive)
    extract_dir = repository_ctx.path(_SNAP7_EXTRACT_DIR_NAME)
    _extract_archive(repository_ctx, archive_path, extract_dir, seven_zip)

    repository_ctx.report_progress("Setting up repository")
    _move_extracted_files_to_root(repository_ctx, extract_dir)

    build_snap7_content = repository_ctx.read(repository_ctx.attr.build_file)
    repository_ctx.file("BUILD.bazel", build_snap7_content)

snap7_repository = repository_rule(
    implementation = _snap7_repository_impl,
    attrs = {
        "archive": attr.label(
            mandatory = True,
            allow_single_file = True,
            doc = "The 7z archive file to extract",
        ),
        "build_file": attr.label(
            mandatory = True,
            allow_single_file = True,
            doc = "The BUILD file template to copy",
        ),
    },
    doc = "Provides a repository for the snap7 library, extracting a 7z archive and generating BUILD.bazel. Downloads 7zip from official source.",
)
