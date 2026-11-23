# py_service_image

`py_service_image` builds a container image that runs one Python module as a service.

## What the image holds

| Part             | Source                                                             | Path in the image    |
| ---------------- | ------------------------------------------------------------------ | -------------------- |
| Base             | The distroless image `cc-debian13` of Google, pinned by its digest | `/`                  |
| Interpreter      | The Python of the Bazel toolchain, which also runs the tests       | `/app/python`        |
| Python libraries | The libraries of the service, from the repo lock                   | `/app/site-packages` |
| Package          | The Python package of the service                                  | `/app/src`           |

- The base has glibc, libgcc and the CA certificates, and it has no shell and no package manager.
- The image starts the interpreter directly, so it needs no shell and no writable directory.
- The image runs as the user `nonroot` of the base (UID 65532).
- The image has no stamp, so the same content gives the same digest.
  Bazel builds and tests it again only when its content changes.
- The interpreter is the same layer in each image of this macro.

## Usage

```starlark
load("//bazel/rules/py_service_image:defs.bzl", "py_service_image")

py_service_image(
    name = "image",
    env = {"MY_SERVICE_LISTEN_HOST": "0.0.0.0"},
    exposed_ports = ["8080/tcp"],
    library = ":my_service",
    module = "cmk.my_service.app",
    repo_tags = ["cmk-my-service:latest"],
    repository = "registry.example/checkmk/cmk-my-service",
)
```

This declares three targets:

- `image`: the image as an OCI layout.
- `image_load`: loads the image into Docker or Podman with the tags of `repo_tags`.
- `image_push`: pushes the image to `repository`.
  The macro declares it only with `repository`.

The image runs `python3 -m <module>`.

## Push

`bazel run <package>:image_push` pushes the image and gives it one tag: the first 12 characters of its digest.
A push of the same content changes nothing in the registry, so a pipeline can push in each run.
The registry then gets a new tag only when a part of the image changed.

The push reads the login for the registry from the Docker configuration (`DOCKER_CONFIG`, or `~/.docker/config.json`).
The option `--repository` sends the image to another registry path:

```sh
bazel run <package>:image_push -- --repository localhost:5000/checkmk/cmk-my-service
```

## Rules for the service

- The `py_library` of the service has its import root in its own Bazel package (`imports = ["."]`).
- A file that the service reads at run time goes into `data` of the macro.

## How it works

- `py_venv` of `rules_py` builds one directory with all libraries of the service.
  It stops with an error if two libraries have the same file.
  `rules_py` marks this rule as unstable.
- `mtree_mutate` moves that directory to `/app/site-packages`, and the package to `/app/src`.
- The target `python_layer` in this directory takes the interpreter and the standard library from the Bazel toolchain.
  It leaves out the parts that a service does not use: pip, the build configuration, IDLE and Tk.

## The interpreter

The image runs the interpreter of the Bazel toolchain.
It is a `python-build-standalone` release of Astral, which `bazel/module/py.MODULE.bazel` pins with a checksum.

- The interpreter needs only glibc and libgcc from the base.
  It has OpenSSL, SQLite and its other libraries built in.
- The tests run on the same interpreter with the same libraries.
- OpenSSL is a part of the interpreter binary.
  A fix for OpenSSL needs a newer release of the interpreter in `bazel/module/py.MODULE.bazel`.
  A newer base does not help, because the interpreter does not load the OpenSSL of the base.

We compared three other ways to get the interpreter:

| Option                                                   | Result                                                                                                                                                                                  |
| -------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| The Python that Checkmk builds (`//omd/packages/Python`) | It works, and the image has about the same size. The image then also needs the OpenSSL of Checkmk and five Debian packages with a lock, because the base lacks libraries that it loads. |
| The Python of the Debian packages                        | Debian 13 has an older Python than the repo lock, and compiled libraries fit only one minor version.                                                                                    |
| `py_image_layer` of `rules_py`                           | It needs the launcher of `py_binary`. The launcher is a shell script that creates a virtual environment at each start, so it needs a shell and a writable directory.                    |

## Update the base image

Google builds the base again when Debian has updates.
The image gets them only when the digest of the pull rule changes.

1. Read the current digest of the tag:

   ```sh
   curl -sI -H 'Accept: application/vnd.oci.image.index.v1+json' \
       https://gcr.io/v2/distroless/cc-debian13/manifests/nonroot | grep -i docker-content-digest
   ```

2. Write it to the entry `distroless_cc_debian13` in `bazel/module/oci.MODULE.bazel`.
3. Write the module lock again:

   ```sh
   bazel mod deps --lockfile_mode=update
   ```

4. Run the image tests of the services that use the macro.
5. Start a container from a new image and request a route of the service.
   Only a container shows a system library that the new base lacks.
