load(
    "//omd/packages/python3-modules:create_python_requirements.bzl",
    _create_python_requirements = "create_python_requirements",
)

def _impl(module_ctx):
    for mod in module_ctx.modules:
        if not mod.is_root:
            fail("Only the root module can use this extension")

        for reqs in mod.tags.requirements:
            _create_python_requirements(
                name = reqs.name,
                requirements_lock = reqs.requirements_lock,
                ignored_modules = reqs.ignored_modules,
            )

create_python_requirements = module_extension(
    implementation = _impl,
    tag_classes = {
        "requirements": tag_class(
            attrs = {
                "name": attr.string(mandatory = True),
                "requirements_lock": attr.string(mandatory = True),
                "ignored_modules": attr.string_list(),
            },
        ),
    },
)
