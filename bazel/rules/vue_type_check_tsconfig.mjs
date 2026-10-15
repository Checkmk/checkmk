/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { writeFileSync } from 'node:fs'
import path from 'node:path'
import process from 'node:process'
import ts from 'typescript'

const [tsconfig, out, packagesJson] = process.argv.slice(2)
const packages = Object.entries(JSON.parse(packagesJson))
const outDir = path.dirname(out)

function fail(message) {
  process.stderr.write(`${message}\n`)
  process.exit(1)
}

function relativeTo(dir, target) {
  const relative = path.relative(dir, target)
  return relative.startsWith('.') ? relative : `./${relative}`
}

function readConfig(file) {
  const { config, error } = ts.readConfigFile(file, ts.sys.readFile)
  if (error) {
    fail(ts.flattenDiagnosticMessageText(error.messageText, '\n'))
  }
  return config
}

function checkExtends(file, specifier) {
  for (const [name, [, packageDir]] of packages) {
    if (specifier === name || specifier.startsWith(`${name}/`)) {
      const target = path.join(packageDir, specifier.slice(name.length))
      fail(
        `${file}: "extends": "${specifier}" resolves through the ${name} link, ` +
          `which puts its sources into the sandbox. ` +
          `Extend "${relativeTo(path.dirname(file), target)}" instead.`
      )
    }
  }
}

function effectivePaths(file) {
  const config = readConfig(file)
  const parents = [config.extends ?? []].flat()
  parents.forEach((parent) => checkExtends(file, parent))
  const inherited = parents
    .filter((parent) => parent.startsWith('.'))
    .map((parent) => effectivePaths(path.join(path.dirname(file), parent)))
    .findLast(Boolean)
  const own = config.compilerOptions?.paths
  return own ? { base: path.dirname(file), paths: own } : inherited
}

const { base, paths } = effectivePaths(tsconfig) ?? { base: outDir, paths: {} }
const rebased = Object.fromEntries(
  Object.entries(paths).map(([key, targets]) => [
    key,
    targets.map((target) => relativeTo(outDir, path.join(base, target)))
  ])
)
for (const [name, [declarationsDir, packageDir]] of packages) {
  const key = `${name}/*`
  if (key in rebased) {
    fail(`${tsconfig}: "paths" key "${key}" collides with the one generated for ${name}.`)
  }
  rebased[key] = [`${relativeTo(outDir, declarationsDir)}/*`, `${relativeTo(outDir, packageDir)}/*`]
}

writeFileSync(
  out,
  `${JSON.stringify(
    { extends: relativeTo(outDir, tsconfig), compilerOptions: { paths: rebased } },
    null,
    2
  )}\n`
)
