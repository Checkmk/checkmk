"""vitest_test: a single-worker vitest run; Bazel parallelizes it through shards."""

load("@aspect_rules_js//js:defs.bzl", "js_test")
load("//bazel/rules:vue_tsc.bzl", "vue_tsc_project")

def _vitest_test_impl(name, visibility, project, data, shard_count, timeout):
    vue_tsc_project(
        name = name + "_project",
        project = project,
        testonly = True,
    )

    js_test(
        name = name,
        args = ["--configLoader=runner"],
        chdir = native.package_name(),
        data = data + [
            ":" + name + "_project",
            Label("//bazel/rules:vitest_runner"),
        ],
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
            doc = "`vite.config.ts` and whatever else the tests read besides `project`.",
            mandatory = True,
        ),
        "project": attr.label(
            doc = "The vue_library of the tests, whose `_type_check` covers them.",
            configurable = False,
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
