# cmk-ui-library

Shared Vue UI library for base components (`components/`) and framework utilities (`lib/`).

Consumers import via the package name:

```ts
import CmkButton from 'cmk-ui-library/components/CmkButton.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
```

## Development

```sh
# everything (cmk-ui-library_type_check_test, tests_type_check_test, unit-test)
bazel test //packages/cmk-ui-library:all

# individually
bazel build //packages/cmk-ui-library:cmk-ui-library_type_check  # vue-tsc over the sources
bazel build //packages/cmk-ui-library:tests_type_check           # vue-tsc over tests/
bazel test //packages/cmk-ui-library:unit-test                   # vitest

# format and lint
bazel run //:format packages/cmk-ui-library
bazel lint //packages/cmk-ui-library/...
```

Unit tests live in `tests/`, mirroring the source layout, and run with vitest configured by `vite.config.ts` (jsdom, `tests/setup-tests.ts`).
To reproduce an order-dependent test failure:

```sh
bazel test //packages/cmk-ui-library:unit-test --test_arg=--project=shared --test_arg=--maxWorkers=1 --test_arg=--sequence.shuffle --test_arg=--sequence.seed=<n> --test_arg=--bail=1
```

License headers and UCL showcase parity are checked by `//packages/cmk-frontend-vue:test-code-integrity`.

## Adding the next Vue workspace package

This package is the template; a new package `packages/<name>` needs:

1. `package.json` (real `dependencies`/`peerDependencies`), `tsconfig.json` + `tsconfig.test.json` extending `../cmk-ui-library/tsconfig.vue-base.json` (by relative path, as `extends` ignores `paths`), `env.d.ts`, `vite.config.ts` with `testProjects` from `cmk-ui-library/vitest.shared.ts` and `cmk-ui-library/vitest.shared-setup.ts` in `setupFiles`, `eslint.config.mjs` built from `cmk-ui-library/eslint.shared.mjs`, `tests/setup-tests.ts` with only the package's own setup.
2. A `BUILD` modelled on this one, with its sources listed explicitly and the library named after the package directory: rules_js links `//packages/<name>:<name>` into consumers (`npm_package_target_name` in `bazel/module/js.MODULE.bazel`).
3. Registration in: `pnpm-workspace.yaml`, `bazel/module/js.MODULE.bazel` (`npm_translate_lock` data), `.bazelignore` (`packages/<name>/node_modules`), the root `BUILD` `eslintrc` deps, and the consumer's `package.json` (`"<name>": "workspace:*"`).
4. `bazel run @pnpm//:pnpm -- --dir "$(pwd)" install --lockfile-only` to update the lockfile.

CI needs no registration: the test targets are picked up by wildcard patterns.
