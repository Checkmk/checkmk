/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

/**
 * Shared eslint configuration for Checkmk Vue packages.
 *
 * Every Vue workspace package builds its `eslint.config.mjs` from this
 * factory, so the rules stay identical across packages:
 *
 *     import { checkmkVueConfig } from '../cmk-ui-library/eslint.shared.mjs'
 *     export default [checkmkVueConfig({ packageDir: 'packages/<name>', importMetaDirname: import.meta.dirname }), ...]
 */
const NO_RANDOM_UUID = {
  selector: "MemberExpression[property.name='randomUUID']",
  message:
    "crypto.randomUUID() is not available in all environments. Use randomId from 'cmk-ui-library/lib/randomId' instead."
}

const NO_MODULE_SCOPE_TRANSLATION = {
  selector: 'CallExpression[callee.name=/^_t(n|p|np)?$/]:not(:function *)',
  message:
    'Translated text minted at module scope resolves before the translation catalog is ' +
    'loaded and freezes to English. Move the call into a function or composable so it ' +
    'runs once the app is mounted.'
}

// Flat config replaces a rule's options rather than merging them, so every
// config object that sets `no-restricted-syntax` has to spread this baseline in.
const RESTRICTED_SYNTAX = [NO_RANDOM_UUID]

export function checkmkVueConfig({
  packageDir,
  importMetaDirname,
  // The test config covers tests/ plus the sources; the source config picks
  // up files the test config deliberately excludes (e.g. lib/i18nString.ts,
  // whose weak test-only variant shadows it).
  project = ['tsconfig.test.json', 'tsconfig.json']
}) {
  return {
    files: [`${packageDir}/**/*.{ts,tsx,vue,js,mjs}`],
    languageOptions: {
      parserOptions: {
        project,
        tsconfigRootDir: importMetaDirname,
        parser: '@typescript-eslint/parser',
        ecmaVersion: 'latest'
      }
    },
    rules: {
      '@typescript-eslint/consistent-type-imports': 'error',
      '@typescript-eslint/no-misused-promises': 'error',
      '@typescript-eslint/no-floating-promises': 'error',
      '@typescript-eslint/naming-convention': [
        'error',
        {
          selector: 'import',
          format: ['camelCase', 'PascalCase']
        },
        {
          selector: 'variableLike',
          format: ['camelCase', 'UPPER_CASE'],
          leadingUnderscore: 'allow'
        },
        {
          selector: 'typeLike',
          format: ['PascalCase']
        },
        { selector: 'property', format: [] }
      ],
      'no-unused-vars': 'off',
      '@typescript-eslint/no-unused-vars': [
        'error',
        {
          argsIgnorePattern: '^_',
          varsIgnorePattern: '^_'
        }
      ],
      eqeqeq: 'error',
      'vue/eqeqeq': 'error',
      'no-var': 'error',
      'no-restricted-syntax': ['error', ...RESTRICTED_SYNTAX],
      curly: 'error',
      'prefer-template': 'error',
      'vue/prefer-template': 'error',
      'vue/prop-name-casing': 'off',
      'vue/require-default-prop': 'off',
      'vue/no-import-compiler-macros': 'error',
      'vue/no-undef-components': 'error',
      'vue/no-bare-strings-in-template': [
        'error',
        {
          allowlist: [
            'x',
            '(',
            ')',
            ',',
            '.',
            '&',
            '+',
            '-',
            '=',
            '*',
            '/',
            '#',
            '%',
            '!',
            '?',
            ':',
            '[',
            ']',
            '{',
            '}',
            '<',
            '>',
            '\u00b7',
            '\u2022',
            '\u2010',
            '\u2013',
            '\u2014',
            '\u2212',
            '|'
          ],
          attributes: {
            '/.+/': [
              'title',
              'aria-label',
              'aria-placeholder',
              'aria-roledescription',
              'aria-valuetext'
            ],
            input: ['placeholder'],
            img: ['alt']
          },
          directives: ['v-text']
        }
      ]
    }
  }
}

/**
 * Bans `_t()` / `_tn()` / `_tp()` / `_tnp()` calls at module scope of .ts files.
 *
 * Module scope evaluates at import time, before the translation catalog is
 * loaded, so text minted there is a frozen English snapshot. Top level of a
 * .vue `<script setup>` is per-instance setup code that only runs once CmkApp
 * has seen the catalog arrive, hence the rule covers .ts files only.
 */
export function checkmkVueModuleScopeTranslationConfig(packageDir) {
  return {
    files: [`${packageDir}/**/*.{ts,tsx}`],
    rules: {
      'no-restricted-syntax': ['error', ...RESTRICTED_SYNTAX, NO_MODULE_SCOPE_TRANSLATION]
    }
  }
}

/** Shared rules for a package's tests/ tree. */
export function checkmkVueTestConfig(packageDir) {
  return {
    files: [`${packageDir}/tests/**/*`],
    rules: {
      'vue/one-component-per-file': 'off',
      'no-restricted-imports': [
        'error',
        {
          paths: [
            {
              name: '@vue/test-utils',
              message:
                'Use @testing-library/vue instead of @vue/test-utils. ' +
                'See https://wiki.lan.checkmk.net/spaces/DEV/pages/149528812/All+things+Vue'
            }
          ]
        }
      ]
    }
  }
}
