import importX from 'eslint-plugin-import-x'
import noUnsanitized from 'eslint-plugin-no-unsanitized'

const PACKAGE = 'packages/cmk-frontend'
const SOURCES = `${PACKAGE}/src/js`

export default [
  {
    ignores: [
      `${PACKAGE}/src/jquery/**`,
      `${PACKAGE}/src/openapi/**`,
      `${SOURCES}/**/*_min.js`,
      `${SOURCES}/modules/cbor_ext.*s`,
      `${SOURCES}/modules/colorpicker.*s`
    ]
  },

  {
    files: [`${PACKAGE}/**/*.{js,mjs,cjs,ts,tsx}`],
    // The rules of the legacy .eslintrc.json are not ported yet (CMK-32715).
    // no-unsanitized is registered but left off so that the disable directives
    // written for it still resolve, and stale directives stay quiet until the
    // rules they belong to are actually switched on.
    linterOptions: { reportUnusedDisableDirectives: 'off' },
    plugins: { 'import-x': importX, 'no-unsanitized': noUnsanitized },
    settings: {
      'import-x/extensions': ['.js', '.ts'],
      // Bazel hands the linter a tree of symlinks. Resolving them would place an
      // import outside the tree the rule below walked, and every export would
      // then look unimported.
      'import-x/resolver': {
        typescript: { project: `${PACKAGE}/tsconfig.eslint.json`, symlinks: false }
      }
    },
    rules: {
      '@typescript-eslint/no-explicit-any': 'off',
      '@typescript-eslint/no-unused-vars': 'off',
      '@typescript-eslint/ban-ts-comment': 'off',
      '@typescript-eslint/no-require-imports': 'off',
      '@typescript-eslint/no-unused-expressions': 'off',
      'no-unsanitized/method': 'off',
      'no-unsanitized/property': 'off',
      // The rule walks src itself rather than the linted file list, through an
      // ESLint API that flat config no longer feeds, so it takes its ignore
      // patterns from the .eslintrc.json next to the sources. The entry points
      // are skipped because they hang their exports on window, and the modules
      // they pull in wholesale are guarded by tests/code_quality instead.
      'import-x/no-unused-modules': [
        'error',
        {
          unusedExports: true,
          src: [SOURCES],
          ignoreExports: [
            `${SOURCES}/index.ts`,
            `${SOURCES}/mobile.ts`,
            `${SOURCES}/tracking_entry.ts`
          ]
        }
      ]
    }
  },

  {
    files: [`${SOURCES}/tests/**`],
    languageOptions: { globals: { global: 'readonly' } }
  }
]
