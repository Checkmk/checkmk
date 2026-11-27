# rules_mypy

An aspect to instrument `py_*` targets with mypy type-checking.

Compared to [bazel-mypy-integration](https://github.com/bazel-contrib/bazel-mypy-integration), this ruleset aims to make a couple of improvements:

- Propagation of the mypy cache between dependencies within a repository to avoid exponential type-checking work
- Robust (and automated) support for including 3rd party types/stubs packages

> [!WARNING]  
> rules_mypy's build actions produce mypy caches as outputs, and these may contain large file counts and that will only grow as a dependency chain grows. This may have an impact on the size and usage of build and/or remote caches.

## Usage

This aspect will run over any `py_binary`, `py_library` or `py_test`.

Setup is significantly easier with bzlmod, we recommend and predominantly support bzlmod, though these rules should work without issue in non-bzlmod setups, albeit with more work to configure.

### Bzlmod Setup

**Add rules_mypy to your MODULE.bazel:**

```starlark
bazel_dep(name = "rules_mypy", version = "0.0.0")
```

**Optionally, configure a types repository:**

Many Python packages have separately published types/stubs packages. While mypy (and these rules) will work without including these types, this ruleset provides some utilities for leveraging these types to improve mypy's type checking.

```starlark
types = use_extension("@rules_mypy//mypy:types.bzl", "types")
types.requirements(
    name = "pip_types",
    # `@pip` in the next line corresponds to the `hub_name` when using
    # rules_python's `pip.parse(...)`.
    pip_requirements = "@pip//:requirements.bzl",
    # also legal to pass a `requirements.in` here
    requirements_txt = "//:requirements.txt",
)
use_repo(types, "pip_types")
```

**Configure `mypy_aspect`.**

Define a new aspect in a `.bzl` file (such as `./tools/aspects.bzl`):

```starlark
load("@pip_types//:types.bzl", "types")
load("@rules_mypy//mypy:mypy.bzl", "mypy")

mypy_aspect = mypy(types = types)
```

Update your `.bazelrc` to include this new aspect:

```starlark
# register mypy_aspect with Bazel
build --aspects //tools:aspects.bzl%mypy_aspect

# optionally, default enable the mypy checks
build --output_groups=+mypy
```

## Customizing mypy

### Configuring mypy with mypy.ini

mypy's behavior may be customized using a [mypy config file](https://mypy.readthedocs.io/en/stable/config_file.html) file. To use a mypy config file, pass a label for a valid config file to the `mypy` aspect factory:

```starlark
mypy_aspect = mypy(
    mypy_ini = "@@//:mypy.ini",
    types = types,
)
```

> [!NOTE]
> The label passed to `mypy_ini` needs to be absolute (a prefix of `@@` means the root repo).

> [!NOTE]
> mypy.ini files should likely contain the following lines to suppress type-checking 3rd party modules.
>
> ```
> follow_imports = silent
> follow_imports_for_stubs = True
> ```

### Changing the version of mypy and/or including plugins

To customize the version of mypy, use rules_python's requirements resolution and construct a custom mypy CLI:

```starlark
# in a BUILD file
load("@pip//:requirements.bzl", "requirements") # '@pip' must match configured pip hub_name
load("@rules_mypy//mypy:mypy.bzl", "mypy", "mypy_cli")

mypy_cli(
    name = "mypy_cli",
    mypy_requirement = requirement("mypy"),
)
```

And in your `aspects.bzl` (or similar) file:

```starlark
load("@rules_mypy//mypy:mypy.bzl", "mypy")

mypy_aspect = mypy(
    mypy_cli = ":mypy_cli",
    types = types,
)
```

Further, to use mypy plugins referenced in any config file, use the `deps` attribute of `mypy_cli`:

```starlark
# in a BUILD file
load("@pip//:requirements.bzl", "requirement") # '@pip' must match configured pip hub_name
load("@rules_mypy//mypy:mypy.bzl", "mypy", "mypy_cli")

mypy_cli(
    name = "mypy_cli",
    mypy_requirement = requirement("mypy"),
    deps = [
        requirement("pydantic"),
    ],
)
```

## Skipping Targets

Skip running mypy on targets by tagging with `no-mypy`, or customize the tags that will suppress mypy by providing a list to the `suppression_tags` argument of the mypy aspect initializer:

```starlark
load("@rules_mypy//mypy:mypy.bzl", "mypy")

mypy_aspect = mypy(
    suppression_tags = ["no-mypy", "no-checks"],
    types = types,
)
```

## Running in opt-in mode

To add type checking to a codebase incrementally, configure a list of opt-in tags that will suppress running mypy by default unless a target is tagged explicitly with one of the opt-in tags.

```starlark
load("@rules_mypy//mypy:mypy.bzl", "mypy")

mypy_aspect = mypy(
    opt_in_tags = ["typecheck"],
    types = types,
)
```
