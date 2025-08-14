export default {
  input: {
    path: './',
    include: ['{src,demo}/**/*.js', '{src,demo}/**/*.ts', '{src,demo}/**/*.vue'],
    exclude: ['./src/lib/i18n.ts'],
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
    locales: ['en', 'de'],
    flat: true, // don't create subdirectories for locales
    linguas: false, // create a LINGUAS file
    splitJson: true // create separate json files for each locale. If used, jsonPath must end with a directory, not a file
  }
}
