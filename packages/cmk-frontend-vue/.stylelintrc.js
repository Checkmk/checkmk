/** @type {import('stylelint').Config} */
export default {
  extends: 'stylelint-config-standard',
  rules: {
    'selector-class-pattern': null
  },
  plugins: ['./scripts/stylelint-vue-bem-naming-convention.js'],
  overrides: [
    {
      files: ['*.css', '**/*.css'],
      rules: {
        'selector-class-pattern': [
          '^$',
          {
            message: 'Expected no selectors in css files, only variable definitions.'
          }
        ]
      }
    },
    // https://github.com/ota-meshi/stylelint-config-standard-vue/blob/main/lib/index.js
    // https://github.com/ota-meshi/stylelint-config-standard-vue/blob/main/lib/vue-specific-rules.js
    {
      files: ['*.vue', '**/*.vue'],
      customSyntax: 'postcss-html',
      extends: ['stylelint-config-standard'],
      rules: {
        'keyframes-name-pattern': ['^([a-z][a-z0-9]*)((-|_|--|__)[a-z0-9]+)*$'],
        // https://github.com/ota-meshi/stylelint-config-recommended-vue/blob/main/lib/vue-specific-rules.js
        'declaration-property-value-no-unknown': [
          true,
          {
            ignoreProperties: { '/.*/': '/v-bind\\(.+\\)/' }
          }
        ],
        'value-keyword-case': [
          'lower',
          {
            ignoreFunctions: ['v-bind']
          }
        ],
        'checkmk/vue-bem-naming-convention': true,
        // renaming the error message to make it more clear what happens:
        'no-empty-source': [true, { message: 'No empty <style> section allowed in vue files.' }]
      }
    }
  ]
}
