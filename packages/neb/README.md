#  Neb shared library(former Livestatus)


## Requirements

- CMake 3.24 or better: you may need manual installation
- C++17
- Git

## Build using CMAKE

To manual run(may be usedul during setting up cmake):

```bash
cmake -S . -B build
cmake --build build  --target neb --verbose
```

To full build:
```bash
./run --all
```


## Build using Bazel

Todo...
