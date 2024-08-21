/* eslint-env node */
require('@rushstack/eslint-patch/modern-module-resolution')

module.exports = {
  ignorePatterns: ['.eslintrc.cjs', 'vite.config.ts', 'tailwind.config.js'],
  root: true,
  extends: [
    'plugin:@typescript-eslint/recommended',
    'plugin:vue/vue3-recommended',
    'eslint:recommended',
    '@vue/eslint-config-typescript',
    '@vue/eslint-config-prettier/skip-formatting'
  ],
  parser: 'vue-eslint-parser',
  parserOptions: {
    project: ['tsconfig.test.json', 'tsconfig.app.json'],
    tsconfigRootDir: __dirname,
    parser: '@typescript-eslint/parser',
    ecmaVersion: 'latest'
  },
  rules: {
    '@typescript-eslint/consistent-type-imports': 'error',
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
    curly: 'error',
    'prefer-template': 'error',
    'vue/prefer-template': 'error',
    'vue/prop-name-casing': 'off'
  }
}
