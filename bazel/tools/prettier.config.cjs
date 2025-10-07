/**
 * @see https://prettier.io/docs/configuration
 * @type {import("prettier").Config}
 */
const config = {
  semi: false,
  tabWidth: 2,
  singleQuote: true,
  printWidth: 100,
  trailingComma: 'none',
  plugins: [require('@trivago/prettier-plugin-sort-imports')],
  importOrder: [
    '^[a-zA-z1-9@]{2, }$',
    '^@\/lib.*$',
    '^@\/components.*$',
    '^@\/form.*$',
    '^@\/.*$',
    '^[./]'
  ],
  importOrderSeparation: true,
  importOrderSortSpecifiers: true
}

module.exports = config
