/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * What a raw perfdata string means: titles, units, Perf-O-Meter, graphs.
 *
 * Resolved by the GUI through Checkmk's own graphing pipeline. The daemon streams
 * only the raw ``perf_data`` and ``check_command`` inputs with each state tick,
 * so this is where they become something renderable.
 */
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'

import type { MetricInfoResult } from '@/maps/types/api'

/** The object a graph is evaluated for; asking for graphs needs its identity. */
export interface MetricInfoGraphContext {
  hostName: string
  serviceDescription?: string | null
  siteId?: string | null
}

/** One lookup, as several callers ask the same question. */
export interface SharedMetricInfoRequest {
  /** What makes two lookups the same question: the object, and whether graphs are asked for. */
  identity: string
  /** The inputs behind the answer; a change invalidates the shared result. */
  snapshot: string
  perfData: string
  checkCommand: string
  graphContext?: MetricInfoGraphContext | undefined
}

interface SharedEntry {
  snapshot: string
  result: Promise<MetricInfoResult | null>
}

interface QueuedLookup {
  entry: { perf_data: string; check_command: string }
  resolve: (result: MetricInfoResult) => void
  reject: (error: unknown) => void
}

/** The most entries the server takes in one request. */
const MAX_BULK_ENTRIES = 1000

export class MetricInfoApi {
  /**
   * In-flight and settled lookups, so a wall with a dozen gadgets bound to the
   * same service fires one request per state tick. On the instance, which the
   * app builds and takes down with it -- a cache outliving the app would hand a
   * reconnected element the previous one's answers.
   */
  private readonly shared = new Map<string, SharedEntry>()

  /** Lookups waiting for the end of the current task, sent as one request. */
  private queued: QueuedLookup[] = []

  /**
   * {@link resolve}, answered once for everyone asking the same question, and
   * null where the lookup failed.
   */
  public resolveShared(request: SharedMetricInfoRequest): Promise<MetricInfoResult | null> {
    const existing = this.shared.get(request.identity)
    if (existing && existing.snapshot === request.snapshot) {
      return existing.result
    }
    const lookup = request.graphContext
      ? this.resolve(request.perfData, request.checkCommand, request.graphContext)
      : this.resolveQueued(request.perfData, request.checkCommand)
    const entry: SharedEntry = {
      snapshot: request.snapshot,
      result: lookup.catch(() => {
        // Don't pin a transient failure (deploy restart, session refresh gap)
        // for the session — drop the entry so the next tick retries.
        if (this.shared.get(request.identity) === entry) {
          this.shared.delete(request.identity)
        }
        return null
      })
    }
    this.shared.set(request.identity, entry)
    return entry.result
  }

  /**
   * {@link resolve} without graphs, sent together with every other lookup of the
   * same task: a state tick changes the perfdata of many objects at once.
   */
  private resolveQueued(perfData: string, checkCommand: string): Promise<MetricInfoResult> {
    return new Promise((resolve, reject) => {
      if (this.queued.length === 0) {
        setTimeout(() => void this.flushQueued(), 0)
      }
      this.queued.push({
        entry: { perf_data: perfData, check_command: checkCommand },
        resolve,
        reject
      })
    })
  }

  private async flushQueued(): Promise<void> {
    const queued = this.queued
    this.queued = []
    const chunks = []
    for (let start = 0; start < queued.length; start += MAX_BULK_ENTRIES) {
      chunks.push(queued.slice(start, start + MAX_BULK_ENTRIES))
    }
    await Promise.all(chunks.map((chunk) => this.sendChunk(chunk)))
  }

  private async sendChunk(chunk: QueuedLookup[]): Promise<void> {
    try {
      const { results } = unwrap(
        await client.POST('/domain-types/maps_metric_info/actions/bulk-resolve/invoke', {
          params: { header: { 'Content-Type': 'application/json' } },
          body: { entries: chunk.map((lookup) => lookup.entry) }
        })
      )
      if (results.length !== chunk.length) {
        throw new Error('bulk-resolve answered a different number of entries')
      }
      chunk.forEach((lookup, index) => lookup.resolve(results[index]!))
    } catch (error) {
      chunk.forEach((lookup) => lookup.reject(error))
    }
  }

  /**
   * A POST on a read: a perfdata string runs to several kilobytes on a wide
   * check, which does not belong in a query string.
   */
  public async resolve(
    perfData: string,
    checkCommand: string,
    graphContext?: MetricInfoGraphContext
  ): Promise<MetricInfoResult> {
    return unwrap(
      await client.POST('/domain-types/maps_metric_info/actions/resolve/invoke', {
        params: { header: { 'Content-Type': 'application/json' } },
        // Every field is spelled out: the server defaults them, but they are
        // still required in the request schema, and the object context is only
        // read when ``graphs`` is set.
        body: {
          perf_data: perfData,
          check_command: checkCommand,
          graphs: graphContext !== undefined,
          host_name: graphContext?.hostName ?? '',
          service_description: graphContext?.serviceDescription ?? '',
          site_id: graphContext?.siteId ?? ''
        }
      })
    )
  }
}
