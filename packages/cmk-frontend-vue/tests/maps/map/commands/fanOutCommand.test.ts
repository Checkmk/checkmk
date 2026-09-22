/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { describe, expect, it, vi } from 'vitest'

import {
  commandTargetsOf,
  describeTarget,
  fanOutCommand,
  targetKey
} from '@/maps/map/commands/fanOutCommand'
import type { CommandTarget, MapElement } from '@/maps/types/api'

function target(host: string, service: string | null = null, site: string | null = null) {
  return { host, service, site }
}

function object(overrides: Partial<MapElement>): MapElement {
  return { id: 'x', type: 'host', x: 0, y: 0, ...overrides } as MapElement
}

describe('commandTargetsOf', () => {
  it('takes a host as itself and a service as its host plus its description', () => {
    expect(
      commandTargetsOf([
        object({ type: 'host', host_name: 'web-01' }),
        object({ type: 'service', host_name: 'web-01', service_description: 'CPU' })
      ])
    ).toEqual([target('web-01'), target('web-01', 'CPU')])
  })

  it('carries the site along, which a federated command needs', () => {
    expect(commandTargetsOf([object({ host_name: 'web-01', site_id: 'remote' })])).toEqual([
      target('web-01', null, 'remote')
    ])
  })

  it('skips an object that names no host, since there is nothing to command', () => {
    expect(commandTargetsOf([object({ type: 'textbox' })])).toEqual([])
  })

  it('commands a host once when two selected objects stand for it', () => {
    // A flow map's "+N more" bubble resolves to the host it hangs off, so
    // picking it alongside that host would otherwise ack the host twice.
    expect(
      commandTargetsOf([
        object({ id: 'web-01', type: 'host', host_name: 'web-01' }),
        object({ id: 'web-01/more', type: 'host', host_name: 'web-01' })
      ])
    ).toEqual([target('web-01')])
  })

  it('keeps two hosts of one name apart when they are on different sites', () => {
    expect(
      commandTargetsOf([
        object({ id: 'a', host_name: 'web-01', site_id: 'here' }),
        object({ id: 'b', host_name: 'web-01', site_id: 'there' })
      ])
    ).toEqual([target('web-01', null, 'here'), target('web-01', null, 'there')])
  })
})

describe('targetKey', () => {
  it('separates what describeTarget cannot, so it can key a list', () => {
    const here = target('web-01', null, 'here')
    const there = target('web-01', null, 'there')
    expect(describeTarget(here)).toBe(describeTarget(there))
    expect(targetKey(here)).not.toBe(targetKey(there))
  })
})

describe('describeTarget', () => {
  it('names a service by its host and description', () => {
    expect(describeTarget(target('web-01', 'CPU'))).toBe('web-01/CPU')
    expect(describeTarget(target('web-01'))).toBe('web-01')
  })
})

describe('fanOutCommand', () => {
  const many = (count: number): CommandTarget[] =>
    Array.from({ length: count }, (_unused, index) => target(`host-${index}`))

  it('sends the command about every target', async () => {
    const send = vi.fn().mockResolvedValue(undefined)
    const result = await fanOutCommand(many(12), send, { what: 'test' })

    expect(send).toHaveBeenCalledTimes(12)
    expect(result).toEqual({ total: 12, succeeded: 12, failed: [] })
  })

  it('keeps going past a refusal, and reports what refused', async () => {
    // The operator wants the command on as much of the selection as can take
    // it; a single rejection must not swallow the rest.
    const send = vi.fn(async (tgt: CommandTarget) => {
      if (tgt.host === 'host-1' || tgt.host === 'host-3') {
        throw new Error('nope')
      }
    })
    vi.spyOn(console, 'warn').mockImplementation(() => {})

    const result = await fanOutCommand(many(5), send, { what: 'test' })

    expect(send).toHaveBeenCalledTimes(5)
    expect(result.succeeded).toBe(3)
    // The targets themselves, not their names: a retry has to be narrowed to
    // exactly these, or it would command the ones that took it a second time.
    expect(result.failed).toEqual([target('host-1'), target('host-3')])
  })

  it('reports progress once per target, refusals included', async () => {
    vi.spyOn(console, 'warn').mockImplementation(() => {})
    const seen: number[] = []
    await fanOutCommand(
      many(4),
      async (tgt) => {
        if (tgt.host === 'host-0') {
          throw new Error('nope')
        }
      },
      { what: 'test', onProgress: (done) => seen.push(done) }
    )
    expect(seen).toEqual([1, 2, 3, 4])
  })

  it('keeps only a few requests in flight, so the command pipe is not flooded', async () => {
    let inFlight = 0
    let highWater = 0
    await fanOutCommand(
      many(20),
      async () => {
        inFlight += 1
        highWater = Math.max(highWater, inFlight)
        await Promise.resolve()
        inFlight -= 1
      },
      { what: 'test' }
    )
    expect(highWater).toBeLessThanOrEqual(5)
  })

  it('does nothing at all when there is nothing selected', async () => {
    const send = vi.fn()
    expect(await fanOutCommand([], send, { what: 'test' })).toEqual({
      total: 0,
      succeeded: 0,
      failed: []
    })
    expect(send).not.toHaveBeenCalled()
  })
})
