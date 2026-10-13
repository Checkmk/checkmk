/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { writeFileSync } from 'node:fs'
import process from 'node:process'
import { parseCLI, startVitest } from 'vitest/node'

const { filter, options } = parseCLI(['vitest', 'run', ...process.argv.slice(2)])
options.maxWorkers ??= 1
if (options.exclude) {
  options.cliExclude = [options.exclude].flat()
  delete options.exclude
}
if (filter.some((f) => f.includes(':'))) {
  options.includeTaskLocation ??= true
}

const { TEST_SHARD_INDEX, TEST_TOTAL_SHARDS, TEST_SHARD_STATUS_FILE } = process.env
if (TEST_TOTAL_SHARDS) {
  options.shard = `${Number(TEST_SHARD_INDEX) + 1}/${TEST_TOTAL_SHARDS}`
  options.passWithNoTests = true
  writeFileSync(TEST_SHARD_STATUS_FILE, '')
}

const vitest = await startVitest('test', filter, options)
await vitest.exit()
