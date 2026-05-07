/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { spawn } from 'child_process'
import * as path from 'path'

import { getExtendedPath } from '../core/tasks'

export function spawnEnv(): NodeJS.ProcessEnv {
  return { ...process.env, PATH: getExtendedPath() }
}

export function targetBinaryPath(wsPath: string, target: string): string {
  const without = target.replace(/^\/\//, '')
  const colon = without.indexOf(':')
  const pkg = without.slice(0, colon)
  const name = without.slice(colon + 1)
  return path.join(wsPath, 'bazel-bin', pkg, name)
}

export function targetToTestXmlPath(wsPath: string, target: string): string {
  const without = target.replace(/^\/\//, '')
  const idx = without.indexOf(':')
  const pkg = idx >= 0 ? without.slice(0, idx) : without
  const name = idx >= 0 ? without.slice(idx + 1) : ''
  return path.join(wsPath, 'bazel-testlogs', pkg, name, 'test.xml')
}

export async function spawnAndCollect(
  command: string,
  args: string[],
  wsPath: string
): Promise<string> {
  return new Promise((resolve) => {
    const child = spawn(command, args, { cwd: wsPath, env: spawnEnv() })
    let buf = ''
    child.stdout.on('data', (d) => (buf += d.toString()))
    child.stderr.on('data', (d) => (buf += d.toString()))
    child.on('error', () => resolve(buf))
    child.on('close', () => resolve(buf))
  })
}
