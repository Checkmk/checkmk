/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as path from 'path'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

// In-memory set of paths the mocked fs reports as existing. Tests add the
// per-command sentinel files to it to "complete" a bridged command.
const existing = new Set<string>()
const fileContents = new Map<string, string>()

vi.mock('fs', () => ({
  existsSync: (p: string) => existing.has(p),
  mkdirSync: () => undefined,
  readFileSync: (p: string) => fileContents.get(p) ?? '',
  unlinkSync: (p: string) => {
    existing.delete(p)
    fileContents.delete(p)
  }
}))

function extractId(wrapped: string): string {
  const m = wrapped.match(/> (\S+\.out) 2>&1/)
  if (!m) throw new Error(`could not parse out-path from: ${wrapped}`)
  return path.basename(m[1], '.out')
}

/** Mark a bridged command's sentinel files present so its poll loop completes. */
function completeCommand(bridgeDir: string, id: string, rc: number, output = ''): void {
  const outPath = path.join(bridgeDir, `${id}.out`)
  const rcPath = path.join(bridgeDir, `${id}.rc`)
  const donePath = path.join(bridgeDir, `${id}.done`)
  fileContents.set(outPath, output)
  fileContents.set(rcPath, String(rc))
  existing.add(outPath)
  existing.add(rcPath)
  existing.add(donePath)
}

const tick = () => new Promise((r) => setTimeout(r, 200))

describe('runInKeepaliveTerminal serialization', () => {
  let bridge: typeof import('../../src/omd/sudoBridge')
  let sent: string[]

  beforeEach(async () => {
    existing.clear()
    fileContents.clear()
    vi.resetModules()
    bridge = await import('../../src/omd/sudoBridge')
    existing.add(bridge.KEEPALIVE_READY)
    sent = []
    bridge.setKeepaliveTerminal({
      sendText: (t: string) => sent.push(t),
      show: () => {},
      dispose: () => {}
    } as never)
  })

  afterEach(() => {
    bridge.setKeepaliveTerminal(null)
  })

  it('does not dispatch a second command until the first completes', async () => {
    const p1 = bridge.runInKeepaliveTerminal('omd start mysite', 5000)
    const p2 = bridge.runInKeepaliveTerminal('omd status mysite', 5000)

    // Let both promises get a chance to run; only the first should have been
    // sent to the shared shell.
    await tick()
    expect(sent).toHaveLength(1)

    // Completing the first lets the chain advance to the second.
    completeCommand(bridge.BRIDGE_DIR, extractId(sent[0]), 0, 'started')
    const r1 = await p1
    expect(r1).toEqual({ output: 'started', exitCode: 0 })

    await tick()
    expect(sent).toHaveLength(2)

    completeCommand(bridge.BRIDGE_DIR, extractId(sent[1]), 0, 'running')
    const r2 = await p2
    expect(r2).toEqual({ output: 'running', exitCode: 0 })
  })

  it('advances the chain even when a command times out', async () => {
    const p1 = bridge.runInKeepaliveTerminal('hangs forever', 300)
    const p2 = bridge.runInKeepaliveTerminal('omd status mysite', 5000)

    // First command never gets its sentinel → times out and resolves null.
    const r1 = await p1
    expect(r1).toBeNull()

    await tick()
    expect(sent).toHaveLength(2)
    completeCommand(bridge.BRIDGE_DIR, extractId(sent[1]), 0, 'ok')
    expect(await p2).toEqual({ output: 'ok', exitCode: 0 })
  })

  it('returns null without dispatching when no keepalive terminal is set', async () => {
    bridge.setKeepaliveTerminal(null)
    const r = await bridge.runInKeepaliveTerminal('omd status mysite', 5000)
    expect(r).toBeNull()
    expect(sent).toHaveLength(0)
  })
})
