load("@bazel_skylib//rules:write_file.bzl", "write_file")

def touch_file(name, out, **kwargs):
    """Creates an empty file.

    Args:
        name: Name of the rule.
        out: Path of the output file, relative to this package.
        **kwargs: Arguments forwarded to write_file.
    """

    # buildifier: disable=unused-variable
    _ = kwargs.pop("content", None)
    _ = kwargs.pop("is_executable", None)
    _ = kwargs.pop("newline", None)
    write_file(name, out, content = [], is_executable = False, **kwargs)
