load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_mypy//mypy:mypy.bzl", "mypy_cli")

mypy_cli(
    name = "mypy_cli",
    mypy_requirement = requirement("mypy"),
    deps = [
        # for `plugins = ["pydantic.mypy"]`
        requirement("pydantic"),
    ],
)

sh_binary(
    name = "clangtidy_bin",
    srcs = ["run-clang-tidy"],
)

filegroup(
    name = "clang_tidy_config",
    srcs = [".clang-tidy"],
    visibility = ["//visibility:public"],
)

sh_binary(
    name = "iwyu_bin",
    srcs = ["run-iwyu"],
)

filegroup(
    name = "iwyu_mappings",
    srcs = glob(["mappings/*.imp"]),
)

genrule(
    name = "pyproject_isort_toml",
    srcs = ["//:pyproject.toml"],
    outs = ["pyproject.isort.toml"],
    # HACK:  There are many better ways to handle this but that's the easiest now.
    # * since toml is structured, we could
    #   `yq ".tool.ruff.lint.select = [\"I\"]" ../../pyproject.toml`
    #   but `yq` doesn't currently support writing TOML.
    # * we could use python for this as well but there's no `dump` functions
    #   for TOML in the standard library.
    # * instead of modifying the configuration, we could change the
    #   runner to `ruff --select I` one way or the other but that requires
    #   writing a rule.
    # * last but not least, we could just use our tools the way they were designed
    #   and make a single pass with ruff.
    cmd = r"perl -0pe 's/(\[tool\.ruff\.lint\](?:\n.*?)+select\ =\ \[)(.*?)(]\n)/$$1\"I\"$$3/g' $< > $@",
)
