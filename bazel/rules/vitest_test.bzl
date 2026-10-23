"""vitest_test: a single-worker vitest run; Bazel parallelizes it through shards."""

load("@aspect_rules_js//js:defs.bzl", "js_test")

def _vitest_test_impl(name, visibility, data, shard_count, timeout):
    js_test(
        name = name,
        args = ["--configLoader=runner"],
        chdir = native.package_name(),
        data = data + [Label("//bazel/rules:vitest_runner")],
        entry_point = Label("//bazel/rules:vitest_runner"),
        shard_count = shard_count,
        timeout = timeout,
        visibility = visibility,
    )

vitest_test = macro(
    doc = "Runs vitest in the calling package, one test file at a time per shard.",
    implementation = _vitest_test_impl,
    attrs = {
        "data": attr.label_list(
            doc = "`vite.config.ts`, the tests and everything they import.",
            mandatory = True,
        ),
        "shard_count": attr.int(
            doc = "Number of shards; each runs its share of the test files.",
            default = 1,
            configurable = False,
        ),
        "timeout": attr.string(
            default = "moderate",
            configurable = False,
        ),
    },
)
