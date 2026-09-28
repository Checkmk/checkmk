export default {
  input: {
    path: './',
    include: [
      'src/**/*.js',
      'src/**/*.ts',
      'src/**/*.vue',
      // cmk-ui-library strings land in this package's catalog (single messages.pot);
      // the package registers no catalogs of its own.
      '../cmk-ui-library/{lib,components}/**/*.ts',
      '../cmk-ui-library/{lib,components}/**/*.vue'
    ],
    exclude: ['../cmk-ui-library/lib/i18n/**/*'],
    parserOptions: {
      overrideDefaultKeywords: true,
      mapping: {
        simple: ['_t'],
        plural: ['_tn'],
        ctx: ['_tp'],
        ctxPlural: ['_tnp']
      }
    }
  },
  output: {
    path: './locale',
    potPath: './messages.pot', // relative to output.path
    jsonPath: '../src/assets/locale/', // relative to output.path
    locales: ['de', 'es', 'fr', 'it', 'ja', 'nl', 'pt_PT', 'ro'],
    flat: true, // don't create subdirectories for locales
    linguas: false, // create a LINGUAS file
    splitJson: true // create separate json files for each locale. If used, jsonPath must end with a directory, not a file
  }
}
