import { default as eslint, default as js } from '@eslint/js'
import skipFormatting from '@vue/eslint-config-prettier/skip-formatting'
import vueTsEslintConfig from '@vue/eslint-config-typescript'
import pluginVue from 'eslint-plugin-vue'
import tseslint from 'typescript-eslint'

export default [
  {
    name: 'app/files-to-lint',
    files: ['**/*.{ts,mts,tsx,vue,js,jsx,cjs,mjs,cts}']
  },

  {
    name: 'app/files-to-ignore',
    ignores: [
      '*.config.js',
      'vite.config.*',
      '**/dist/**',
      '**/dist-dev/**',
      '**/dist-ssr/**',
      '**/coverage/**',
      'demo/public/mockServiceWorker.js',
      '.stylelintrc.js',
      'scripts/stylelint-vue-bem-naming-convention.js'
    ]
  },

  js.configs.recommended,
  ...pluginVue.configs['flat/recommended'],
  eslint.configs.recommended,
  ...tseslint.configs.recommended,
  ...vueTsEslintConfig(),
  skipFormatting,

  {
    languageOptions: {
      parserOptions: {
        project: [
          './tsconfig.test.json',
          './tsconfig.demo.json',
          './tsconfig.app.json',
          './prettier.config.cjs'
        ],
        tsconfigRootDir: import.meta.dirname,
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
  },

  {
    files: ['demo/**/*'],
    rules: {
      'vue/no-bare-strings-in-template': 'off'
    }
  },

  {
    files: ['tests/**/*'],
    rules: {
      'vue/one-component-per-file': 'off'
    }
  }
]
