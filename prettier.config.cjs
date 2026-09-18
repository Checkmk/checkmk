/**
 * Root config so editors and plain `prettier` invocations agree with what
 * `bazel run //:format` produces. Bazel passes `--config` explicitly and does
 * not rely on this file.
 *
 * @see https://prettier.io/docs/configuration
 * @type {import("prettier").Config}
 */
module.exports = require('./bazel/tools/prettier.config.cjs')
