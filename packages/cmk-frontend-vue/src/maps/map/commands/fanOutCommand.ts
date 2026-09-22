/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Sending one monitoring command about many things.
 *
 * Checkmk has real bulk commands for a host group and for a service group, and
 * where one of those fits it is used instead — it either applies to all members
 * or to none. This is for the cases where no such command exists: the
 * contributing leaves of a BI aggregation, or the nodes an operator picked on a
 * flow map. Those are sent one at a time.
 *
 * Two things follow from that. The requests are sent a few at a time, because
 * they all land on the same site and livestatus serialises the command pipe
 * anyway, so flooding it only makes the GUI unresponsive. And one failure does
 * not abort the rest: the operator wants the command on as much of the
 * selection as can take it, and is told afterwards what did not take it.
 */
import type { CommandTarget, MapElement } from '@/maps/types/api'

/** How many are in flight at once. Five is what Checkmk's own bulk actions use. */
const CONCURRENCY = 5

export interface FanOutResult {
  total: number
  succeeded: number
  /** What refused the command, so a retry can be narrowed to just those. */
  failed: CommandTarget[]
}

/** A target as the operator knows it — for a list, or for a failure report. */
export function describeTarget(target: CommandTarget): string {
  return target.service ? `${target.host}/${target.service}` : target.host
}

/**
 * What makes two targets the same thing to command. The site belongs in it: in
 * a federated setup the same host name can be monitored on two of them, and
 * those are two hosts. ``describeTarget`` is the operator's name for a target
 * and does not distinguish them, so it must not be used as an identity.
 */
export function targetKey(target: CommandTarget): string {
  return JSON.stringify([target.site ?? '', target.host, target.service ?? ''])
}

/**
 * The hosts and services behind a set of map objects, ready to be commanded.
 *
 * Deduplicated, because a selection can hold two objects standing for one host
 * — a flow map's "+N more" bubble resolves to the host it hangs off, so picking
 * both it and that host would otherwise send the command to it twice.
 */
export function commandTargetsOf(objects: readonly MapElement[]): CommandTarget[] {
  const byKey = new Map<string, CommandTarget>()
  for (const object of objects) {
    if (!object.host_name) {
      continue
    }
    const target: CommandTarget = {
      host: object.host_name,
      service: object.type === 'service' ? (object.service_description ?? null) : null,
      site: object.site_id ?? null
    }
    const key = targetKey(target)
    if (!byKey.has(key)) {
      byKey.set(key, target)
    }
  }
  return [...byKey.values()]
}

export async function fanOutCommand(
  targets: readonly CommandTarget[],
  send: (target: CommandTarget) => Promise<void>,
  options: {
    /** Called after each target, whether it took the command or not. */
    onProgress?: (done: number) => void
    /** What to log a failure under. */
    what: string
  }
): Promise<FanOutResult> {
  const queue = [...targets]
  const failed: CommandTarget[] = []
  let done = 0
  let succeeded = 0

  const worker = async (): Promise<void> => {
    for (let target = queue.shift(); target; target = queue.shift()) {
      try {
        await send(target)
        succeeded += 1
      } catch (caught) {
        failed.push(target)
        console.warn(`[Maps] ${options.what} failed for`, target, caught)
      } finally {
        done += 1
        options.onProgress?.(done)
      }
    }
  }
  await Promise.all(Array.from({ length: Math.min(CONCURRENCY, queue.length) }, () => worker()))
  return { total: targets.length, succeeded, failed }
}
