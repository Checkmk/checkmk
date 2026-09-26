"""vitest_test: a vitest run whose worker pool Bazel reserves as CPUs."""

load("@aspect_rules_js//js:defs.bzl", "js_library", "js_test")

def vitest_test(name, workers, data, tags = [], **kwargs):
    """Runs vitest in the calling package on a fixed pool of workers.

    Args:
      name: target name.
      workers: vitest pool size, declared to Bazel as `cpu:<workers>`.
        `--test_arg=--maxWorkers=<n>` changes the pool, not the declaration.
      data: `vite.config.ts`, the tests and everything they import.
      tags: extra tags.
      **kwargs: passed to js_test, e.g. `shard_count` and `timeout`.
    """

    # Source files listed directly on the test would be copied to bin by actions that
    # inherit the cpu tag, and clash with the untagged copies other targets make.
    js_library(
        name = name + "_data",
        data = data,
        tags = ["manual"],
        visibility = ["//visibility:private"],
    )
    js_test(
        name = name,
        args = ["--configLoader=runner"],
        chdir = native.package_name(),
        data = [
            ":%s_data" % name,
            Label("//bazel/rules:vitest_runner"),
        ],
        entry_point = Label("//bazel/rules:vitest_runner"),
        env = {"BAZEL_VITEST_WORKERS": str(workers)},
        tags = tags + ["cpu:%d" % workers],
        **kwargs
    )
