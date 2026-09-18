# GCC toolchain

Builds a relocatable, sysroot-bearing x86_64 gcc toolchain.

## Version pins

We need to take the floor across every distro supported by checkmk.

| Distro                                   | glibc    | kernel-headers |
| ---------------------------------------- | -------- | -------------- |
| **AlmaLinux 8.10** (`IMAGE_ALMALINUX_8`) | **2.28** | **4.18.0**     |
| AlmaLinux 9.2                            | 2.34     | -              |
| Debian 12                                | 2.36     | -              |
| Ubuntu 22.04                             | 2.35     | -              |
| SLES 15 SP6 (proxy for pinned SP7)       | 2.38     | -              |

Target triplet: `x86_64-checkmk-linux-gnu`.

## Files

- `x86_64-checkmk-linux-gnu.defconfig`: crosstool-NG config.
- `common.sh`: constants and helpers shared by `build.sh` and `test.sh`.
- `build.sh`: builds the image, runs `docker/build.sh` inside it, packages two
  deterministic tarballs (toolchain, gdb).
- `test.sh`: given a toolchain tarball, compiles a C and C++ hello-world against
  it and runs both inside the actual floor distro.
- `upload.sh`: upload the artifacts to AWS, requires credentials.
- `docker/`: everything that runs inside Docker, never directly.
- `docker/Dockerfile`: `ubuntu:24.04` base, crosstool-NG build dependencies,
  crosstool-NG built from the pinned tag.
- `docker/build.sh`: runs `ct-ng build`, packages both tarballs, invoked by the
  top-level `build.sh`.
- `docker/test.sh`: compiles the hello-worlds and stages gdb, invoked by the
  top-level `test.sh`.

## Usage

```sh
./build.sh <output-dir>
./test.sh <output-dir>
```

`build.sh` produces
`<output-dir>/x86_64-checkmk-linux-gnu-gcc14.4.0-glibc2.28.tar.xz` and
`<output-dir>/x86_64-checkmk-linux-gnu-gdb.tar.xz`. `test.sh` takes the same
`<output-dir>` and looks for both tarballs there by those fixed names.

## Testing

`test.sh` compiles a C and C++ hello-world with
`--sysroot=<toolchain>/x86_64-checkmk-linux-gnu/sysroot`, then runs both
binaries inside an AlmaLinux 8.10 container. If the gdb tarball is also
present in `<output-dir>`, it also runs `gdb --version` against the same
floor distro for the same reason; otherwise gdb testing is skipped.
