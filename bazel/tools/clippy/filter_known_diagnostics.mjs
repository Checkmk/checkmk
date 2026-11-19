/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
// Drops the findings of a crate's own clippy run from those of a rust_test with `crate`,
// which compiles the sources of that crate again, with cfg(test).
//
// Usage: filter_known_diagnostics.mjs OUTPUT DIAGNOSTICS KNOWN_DIAGNOSTICS NEW_OUTPUT NEW_DIAGNOSTICS
//
// OUTPUT is clippy's exit code followed by its human-readable output, as written by
// process_wrapper_wrapper.bash. DIAGNOSTICS and KNOWN_DIAGNOSTICS are rustc's JSON
// diagnostics. NEW_OUTPUT and NEW_DIAGNOSTICS get the errors and warnings of DIAGNOSTICS
// which KNOWN_DIAGNOSTICS doesn't have, in the same formats.
import { readFileSync, writeFileSync } from 'node:fs'
import process from 'node:process'

// rustc's closing summaries count the known findings, too.
const SUMMARY = /^(aborting due to |\d+ warnings? emitted)/

function readJsonLines(path) {
  return readFileSync(path, 'utf8')
    .split('\n')
    .filter((line) => line.startsWith('{'))
    .map((line) => ({ line, json: JSON.parse(line) }))
}

function isFinding(diagnostic) {
  return (
    diagnostic.$message_type === 'diagnostic' &&
    (diagnostic.level === 'warning' || diagnostic.level.startsWith('error')) &&
    !(diagnostic.spans.length === 0 && SUMMARY.test(diagnostic.message))
  )
}

function key(diagnostic) {
  return JSON.stringify([
    diagnostic.level,
    diagnostic.code?.code ?? null,
    diagnostic.message,
    diagnostic.spans.map((span) => [span.file_name, span.byte_start, span.byte_end])
  ])
}

const [outputPath, diagnosticsPath, knownDiagnosticsPath, newOutputPath, newDiagnosticsPath] =
  process.argv.slice(2)

const known = new Set(
  readJsonLines(knownDiagnosticsPath)
    .map(({ json }) => json)
    .filter(isFinding)
    .map(key)
)
const diagnostics = readJsonLines(diagnosticsPath)
const findings = diagnostics.filter(({ json }) => isFinding(json) && !known.has(key(json)))
writeFileSync(newDiagnosticsPath, findings.map(({ line }) => `${line}\n`).join(''))

const output = readFileSync(outputPath, 'utf8')
if (findings.length > 0) {
  writeFileSync(newOutputPath, ['1', ...findings.map(({ json }) => json.rendered)].join('\n'))
} else if (
  Number.parseInt(output, 10) !== 0 &&
  !diagnostics.some(({ json }) => json.$message_type === 'diagnostic')
) {
  // clippy failed without any diagnostics, so keep what it said.
  writeFileSync(newOutputPath, output)
} else {
  writeFileSync(newOutputPath, '0\n')
}
