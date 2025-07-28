# BCR Mirror
This is an attempt to mirror the bazel central registry on our nexus server.

# How To
In case an upstream resource (most likely github) is unavailable and the corresponding package is not already part of this mirror here, do the following:
* create the folder structure under `bazel/registry/modules`
  * `{module_name}/{version}/source.json`
  * you can also easily copy it from [bazel-central-registry](https://github.com/bazelbuild/bazel-central-registry/tree/main/modules)
  * e.g. in order to get `alsa_lib` in version `1.2.0`, copy `alsa_lib/1.2.9/source.json` including the folders to `bazel/registry/modules`
* afterwards upload the file from `url` to nexus's `upstream-archives`
* add a field to the `source.json` which points to the nexus mirror:
```
"mirror_urls": {"https://artifacts.lan.tribe29.com/repository/upstream-archives/{THE_FILE_NAME_FROM_url}"}
```

# Test the mirror
* clean the repository cache:
```
rm -rf ~/.cache/bazel/_bazel_$(whoami)/cache/repos/v1
```
* clean the bazel cache:
```
bazel clean --expunge
```
* test the mirror by blocking the upstream url (e.g. by introducing a typo in the url) and do a `bazel build` which would pull that depend
This should result in using the nexus url for downloading.
