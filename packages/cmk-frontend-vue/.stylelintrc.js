/** @type {import('stylelint').Config} */
export default {
  extends: 'stylelint-config-standard',
  rules: {},
  overrides: [
    // https://github.com/ota-meshi/stylelint-config-standard-vue/blob/main/lib/index.js
    // https://github.com/ota-meshi/stylelint-config-standard-vue/blob/main/lib/vue-specific-rules.js
    {
      files: ['*.vue', '**/*.vue'],
      customSyntax: 'postcss-html',
      extends: ['stylelint-config-standard'],
      rules: {
        'selector-class-pattern': ['^([a-z][a-z0-9]*)((-|_|--|__)[a-z0-9]+)*$'],
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
        ]
      }
    }
  ]
}
