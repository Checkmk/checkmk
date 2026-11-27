# Modified by Checkmk GmbH, see bazel/tools/rules_mypy/VENDORED.md
import argparse
import contextlib
import os
import pathlib
import shutil
import sys
import tempfile
from collections.abc import Iterator

import mypy.api
import mypy.util


def _hardlink_tree(src: str, dst: str) -> None:
    """Iteratively merge src into dst via hardlinks.

    Hardlinks share inodes so each downstream cache adds essentially zero
    unique disk blocks rather than re-copying the transitive merge content.

    Deliberately use os.scandir for best performance.
    Falls back to shutil.copy if os.link fails (e.g. cross-filesystem).

    Checkmk, unverified: locally this probably always copies. bazel/rc/performance.rc
    sets --sandbox_base=/dev/shm, so a sandboxed action writes dst on tmpfs, while src
    resolves to bazel-out on disk, and os.link fails with EXDEV across filesystems. Only
    CI, which resets --sandbox_base in bazel/rc/ci.rc, would link. Check this before
    setting cache = True in bazel/tools/aspects.bzl again.
    """
    stack = [(src, dst)]
    while stack:
        cur_src, cur_dst = stack.pop()
        with contextlib.suppress(FileExistsError):
            os.mkdir(cur_dst)

        with os.scandir(cur_src) as it:
            for entry in it:
                sp = entry.path
                dp = cur_dst + "/" + entry.name
                if entry.is_dir(follow_symlinks=False):
                    stack.append((sp, dp))
                    continue

                try:
                    os.link(sp, dp)
                except FileExistsError:
                    pass
                except OSError:
                    shutil.copy(sp, dp)


def _merge_upstream_caches(cache_dir: str, upstream_caches: list[str]) -> None:
    current = pathlib.Path(cache_dir)
    current.mkdir(parents=True, exist_ok=True)

    for upstream_dir in upstream_caches:
        _hardlink_tree(upstream_dir, cache_dir)

    # missing_stubs is mutable; the merge may have hardlinked it from upstream.
    # Unlink so mypy can rewrite it without touching the upstream inode.
    (current / "missing_stubs").unlink(missing_ok=True)


@contextlib.contextmanager
def managed_cache_dir(cache_dir: str | None, upstream_caches: list[str]) -> Iterator[str]:
    """
    Returns a managed cache directory.

    When cache_dir exists, returns a merged view of cache_dir with upstream_caches.
    Otherwise, returns a temporary directory that will be cleaned up when the resource
    is released.
    """
    if cache_dir:
        _merge_upstream_caches(cache_dir, list(upstream_caches))
        yield cache_dir
    else:
        tmpdir = tempfile.TemporaryDirectory()
        yield tmpdir.name
        tmpdir.cleanup()


def run_mypy(
    mypy_ini: str | None, cache_dir: str, srcs: list[str], extra_args: list[str]
) -> tuple[str, str, int]:
    maybe_config = ["--config-file", mypy_ini] if mypy_ini else []
    report, errors, status = mypy.api.run(
        maybe_config
        + [
            # do not check mtime in cache
            "--skip-cache-mtime-checks",
            # mypy defaults to incremental, but force it on anyway
            "--incremental",
            # use a known cache-dir
            f"--cache-dir={cache_dir}",
            # use current dir + MYPYPATH to resolve deps
            "--explicit-package-bases",
            # speedup
            "--fast-module-lookup",
            "--show-column-numbers",
        ]
        + extra_args
        + srcs
    )
    if status:
        sys.stderr.write(errors)
        sys.stderr.write(report)

    return report, errors, status


def run(
    output: str | None,
    cache_dir: str | None,
    upstream_caches: list[str],
    mypy_ini: str | None,
    srcs: list[str],
) -> None:
    if len(srcs) > 0:
        # Downstream actions merge this cache file by file (see _merge_upstream_caches), so it
        # needs one file per module, not mypy's default SQLite database.
        extra_args = [] if cache_dir is None else ["--no-sqlite-cache"]
        with managed_cache_dir(cache_dir, upstream_caches) as mypy_cache_dir:
            report, errors, status = run_mypy(mypy_ini, mypy_cache_dir, srcs, extra_args)
    else:
        report, errors, status = "", "", 0

    if output:
        with open(output, "w+") as file:
            file.write(errors)
            file.write(report)

    # use mypy's hard_exit to exit without freeing objects, it can be meaningfully
    # faster than an orderly shutdown
    mypy.util.hard_exit(status)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=False)
    parser.add_argument("-c", "--cache-dir", required=False)
    parser.add_argument("--upstream-cache", required=False, action="append")
    parser.add_argument("--mypy-ini", required=False)
    parser.add_argument("src", nargs="*")
    args = parser.parse_args()

    output: str | None = args.output
    cache_dir: str | None = args.cache_dir
    upstream_cache: list[str] = args.upstream_cache or []
    mypy_ini: str | None = args.mypy_ini
    srcs: list[str] = args.src

    run(output, cache_dir, upstream_cache, mypy_ini, srcs)


if __name__ == "__main__":
    main()
