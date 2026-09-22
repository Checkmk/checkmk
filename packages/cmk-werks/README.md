# cmk-werks

Every werk ID that is reserved, consumed, freed or picked is appended to `$HOME/.local/state/cmk-werks/werk-ids.log`, one line per event, as `key:value` pairs:

```
2026-09-23 11:20:40.004+02:00 [cmk.werks.ids] [INFO] launcher:venv, action:reserve, werk IDs:11114 11115 11116
2026-09-23 11:24:11.118+02:00 [cmk.werks.ids] [INFO] launcher:bazel, action:new, werk ID:11111, werk file:/repo/.werks/11111.md
```

`launcher` says whether the werk tool ran from Bazel or from the venv, and `action` is one of `reserve`, `new`, `delete`, `migrate` and `pick`:

```sh
grep "werk ID:11111" ~/.local/state/cmk-werks/werk-ids.log
```

## development

```
./run -a
```
