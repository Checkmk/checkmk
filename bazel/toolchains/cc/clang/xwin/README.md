# `xwin` Toolchain

Cross compilation to `x86_64-pc-windows-msvc` from Linux. `clang-cl`, `lld-link`
and `llvm-lib` come from the hermetic LLVM download; the MSVC CRT and Windows SDK
come from `@xwin_sysroot`.

One toolchain serves both language stacks:

- **Rust**: `rules_rust` links through the `link_actions` tool and exports the
  tools and compile arguments as `CC` / `AR` / `CFLAGS` to cargo build scripts.
  That is how crates carrying C sources, such as `ring`, get compiled.
- **C/C++**: Bazel's own `cc_*` actions, using the MSVC-style argument
  definitions in `../args/msvc` in place of Bazel's GNU-style built-ins, and header
  dependency discovery from `clang-cl`'s `/showIncludes` output.

This file holds the reasoning that is too long to sit above the targets it
explains. The BUILD files carry the short version and point here.

## Compilation Modes

`-c dbg` and `-c opt` reproduce the flags the `agents/wnx` Visual Studio projects
apply to their `Debug|x64` and `Release|x64` configurations.

| MSBuild property           | `Debug\|x64`                  | `Release\|x64`          |
| -------------------------- | ----------------------------- | ----------------------- |
| `Optimization`             | `Disabled` → `/Od`            | `MaxSpeed` → `/O2`      |
| `RuntimeLibrary`           | `MultiThreadedDebug` → `/MTd` | `MultiThreaded` → `/MT` |
| `PreprocessorDefinitions`  | `_DEBUG` (implied by `/MTd`)  | `NDEBUG`                |
| `DebugInformationFormat`   | `ProgramDatabase` → `/Z7`     | -                       |
| `GenerateDebugInformation` | `/DEBUG`                      | -                       |
| `OptimizeReferences`       | -                             | `/OPT:REF`              |
| `EnableCOMDATFolding`      | -                             | `/OPT:ICF`              |

Bazel has three modes where MSBuild has two configurations. `fastbuild`, the
default, is `Debug` without the debug information or the debug CRT.
`IntrinsicFunctions` and `FunctionLevelLinking` need no flags of their own,
`clang-cl` implies both at `/O2`.

### Deliberately Not Mirrored

- **`DebugInformationFormat=ProgramDatabase`'s `/Zi`**, which writes CodeView
  records to a compile-time `.pdb`. That file is not an output Bazel knows about,
  and a shared one is a build parallelism hazard. `/Z7` puts the same records in
  the `.obj` files, which Bazel does track, and the linker collects them into the
  executable's `.pdb` from there.
- **`Release`'s `GenerateDebugInformation=DebugFastLink`**. A `FASTLINK` `.pdb`
  only points into the `.obj` files, which are sandbox-local, so not useful for
  us.
- **`WholeProgramOptimization` (`/GL`, plus the `/LTCG` MSBuild infers from it)**,
  set in `Release|x64` by all six vcxprojs. `clang-cl` accepts `/GL` but ignores
  it ("argument unused"), so mirroring it literally buys nothing. The LLVM
  analogue is `-flto`, which `lld-link` does support. Though it makes every compile
  emit bitcode instead of COFF, changing what `llvm-lib` archives and moving
  codegen into the link. That is a toolchain change rather than a mode argument,
  so `-c opt` ships without LTO where the MSBuild Release build has it.

## Debug Information

`-c dbg` needs both halves. Without `/DEBUG` at link time, `lld-link` drops the
`/Z7` records instead of writing the `.pdb` that the `generate_pdb_file` feature
has Bazel expect next to the binary.

`generate_pdb_file` carries no arguments of its own: `cc_binary` and
`cc_shared_library` look the name up to decide whether to declare the linker's
`<target>.pdb` as an output, which they place in the `pdb_file` output group. It
has to be listed in the mode package's feature set, because a feature whose
`implies` cannot be satisfied is disabled silently — which would take `dbg`'s
arguments with it.

`/PDBALTPATH:%_PDB%` embeds only the `.pdb`'s basename rather than the execroot
path the linker sees, so debuggers find it next to the `.exe`.

The CRT and SDK libraries name PDBs that `@xwin_sysroot` does not carry, so
`/IGNORE:4099` suppresses one `LNK4099` per CRT object pulled in.

## CRT Flavor

`/MTd` is what makes `-c dbg` a debug build rather than a release one with the
optimizer switched off: it defines `_DEBUG`, which switches the CRT and STL
headers to their checked implementations (`_ITERATOR_DEBUG_LEVEL` 2, debug heap).
Every object in the binary has to agree on it.

Each CRT header names its own library with `#pragma comment(lib, ...)`, so the
linker pulls in whichever flavor an object was compiled against. Objects that
disagree leave two CRTs in the link. Sometimes duplicate symbols, sometimes only
a warning and an executable carrying two heaps. `args/crt.bzl` lists every flavor
we are not using under `/NODEFAULTLIB`, which tells the linker to ignore those
directives, so the wrong CRT is never pulled in at all.

The release and debug sets cannot be concatenated into one. `/NODEFAULTLIB` wins
over `/DEFAULTLIB` whatever the order, and each set excludes exactly what the
other requests, so a combined list would exclude both flavors and leave nothing
to link against.

## Why the Rust Command Lines Ignore `-c`

Only the `cc_*` actions follow the compilation mode. Both command lines that
`rules_rust` builds without action variables. The `$CFLAGS` it exports to cargo
build scripts, and the linker arguments it hands to `rustc`. These stay on the
release settings regardless of what `-c` is set to.

`args/build_script` and `args/mode` therefore use the _same argument names_ for
the same concepts; the package a name lives in says which command line it
reaches. Everything in `args/build_script` is gated `requires_none`, everything
in `args/mode` `requires_not_none`, so the two never both apply. They cannot be
shared, because those gates are inverses of each other.

The same gating is what keeps `args/msvc` out of those command lines. Every
argument there is gated on the action variable it formats: `source_file`,
`output_file`, `output_execpath`, `libraries_to_link`. None of which a build
script supplies. Without that, the GNU replacements would put `/c`, `/Fo` and the
rest of Bazel's per-action plumbing into the `$CFLAGS` handed to `cc-rs`.

Losing a gate is easy and the symptom shows up far from the cause, so `tests/`
pins the whole command line. It states what a build script is meant to receive,
so an argument added without a gate fails the test. Over-gating fails too, as a
missing argument. It runs once per `-c` mode, since these command lines are
release regardless of what mode is used.

The settings are fixed at release because:

- What a build script compiles ends up in a shipped binary, and `-c` is not a
  reliable shipping signal anyway — `rust_binary(opt = True)` in
  `//bazel/rules:xcomp/rust.bzl` forces `opt` when `@cmk//optimize` is enabled.
  `/O2` has to be spelled out because no mode argument reaches `$CFLAGS` and
  `clang-cl` defaults to `-O0`; without it, build-script objects would ship
  unoptimized.
- `rustc` cannot ask for a debug CRT. Its only CRT knob for this target is the
  `crt-static` target feature — static versus dynamic, with no debug/release axis
  — and `//bazel/platforms:msvc` sets it via `-Ctarget-feature=+crt-static`, so
  Rust always links the release `libcmt`. The release CRT arguments are therefore
  the only ones worth handing `rustc`, regardless of what `-c` is set to.

Upstream hits the unguarded version of this as
[rules_rust#3631](https://github.com/bazelbuild/rules_rust/issues/3631): `-c
opt`'s `-O2` leaking into build-script `$CFLAGS`.

## Gotchas

- **Write `-Xclang -internal-isystem`, not `/imsvc`.** They mean the same thing
  to `clang-cl`. The sysroot include paths are execroot-relative and cargo build
  scripts run from elsewhere, so `rules_rust` makes them absolute by prefixing
  `$(pwd)`. It only recognizes the GNU spellings when it does that. Written as
  `/imsvc` the paths would reach a build script without the path rewrite and the
  CRT headers would not be found. `args:windows_sysroot` uses the long form for
  this reason.
- **`-no-canonical-prefixes` cannot be unconditional.** Bazel runs the compiler
  through a symlink, `bin/clang-cl` pointing at `bin/clang`. Without the flag
  clang resolves that symlink to locate its resource directory, then reports its
  builtin headers as absolute paths, which Bazel's inclusion validation rejects.
  A cargo build script is the opposite case: it runs from a different working
  directory, where clang _has_ to resolve `argv0` to find those same headers.
- **`cc-rs` compiles with `/MD` unless told otherwise.** It decides from
  `CARGO_CFG_TARGET_FEATURE`, which under Bazel does not contain `crt-static`.
  `/MD` objects reach the CRT through `__imp_*` dllimport symbols that the
  static CRT cannot resolve, so the link fails.
  `args/build_script:static_release_crt` appends `/MT` after cc-rs's own flags,
  and the last `/M` flag wins.
- **The tool's basename has to contain `clang-cl`.** That is how `cc-rs`
  recognizes an MSVC-style compiler. Miss it and it emits GNU-style arguments.
- **DLLs are not supported.** Bazel emits the GNU `-shared` for a
  dynamic-library link and `lld-link` does not understand it. Overriding the
  feature with nothing would drop the flag and silently link a PE _executable_
  named `.dll`, and an unrecognized `/flag` would only warn. So
  `../args/msvc:shared_flag` passes a filename that cannot exist,
  `DLLS-NOT-SUPPORTED-BY-XWIN-TOOLCHAIN-see-args-msvc-BUILD-shared_flag`, which
  `lld-link` reports as an error naming the reason.

## Upstream Replacement

The MSVC-style argument set in `../args/msvc` is hand-rolled and modeled on
`@rules_cc//cc/toolchains/args:experimental_replace_legacy_action_config_features`.
It is expected to be superseded by upstream MSVC support in `rules_cc`:
[issue 434](https://github.com/bazelbuild/rules_cc/issues/434) tracks the plan
and [PR 561](https://github.com/bazelbuild/rules_cc/pull/561) has an
implementation in review. Once a `rules_cc` release ships an MSVC args/features
set, check whether that package can shrink to loading it.
