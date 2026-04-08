import { globalIgnores } from 'eslint/config'

export default [
  {
    files: ['packages/cmk-frontend-vue/**/*.{ts,tsx,vue,js,mjs}'],
    languageOptions: {
      parserOptions: {
        project: ['**/tsconfig.test.json', '**/tsconfig.ucl.json', '**/tsconfig.app.json'],
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

  globalIgnores(['packages/cmk-frontend-vue/src/components/graphics/RnbwCursor.vue']),

  {
    files: ['packages/cmk-frontend-vue/src/**/*'],
    rules: {
      'no-restricted-imports': [
        'error',
        {
          patterns: [
            {
              group: ['@ucl', '@ucl/*'],
              message: 'Production code must not import from the UI Component Library (@ucl).'
            }
          ]
        }
      ]
    }
  },

  {
    files: ['packages/cmk-frontend-vue/ui-component-library/**/*'],
    rules: {
      'vue/no-bare-strings-in-template': 'off'
    }
  },

  {
    files: ['packages/cmk-frontend-vue/tests/**/*'],
    rules: {
      'vue/one-component-per-file': 'off'
    }
  }
]
