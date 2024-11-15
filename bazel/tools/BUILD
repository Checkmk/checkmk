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
