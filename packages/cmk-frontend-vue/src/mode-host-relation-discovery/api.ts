/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'

import type {
  AcceptRequest,
  FindingRequest,
  JobStatus,
  LookIn,
  Outcome,
  RowsPage,
  RowsPart,
  SharedValue,
  Suggestions
} from './types'

export async function suggestEvidence(
  words: string[],
  values: SharedValue[],
  lookIn: LookIn[]
): Promise<Suggestions> {
  return unwrap(
    await client.POST('/domain-types/host_relation_discovery/actions/suggest/invoke', {
      params: { header: { 'Content-Type': 'application/json' } },
      body: { words, values, look_in: lookIn }
    })
  )
}

/** Starts a scan and answers with its job, which the status is then asked for. */
export async function startScan(findings: FindingRequest[]): Promise<string> {
  const result = await client.POST('/domain-types/host_relation_discovery/actions/scan/invoke', {
    params: { header: { 'Content-Type': 'application/json' } },
    body: { findings }
  })
  return unwrap(result).job_id
}

export async function acceptRelations(accepted: AcceptRequest): Promise<string> {
  const result = await client.POST('/domain-types/host_relation_discovery/actions/accept/invoke', {
    params: { header: { 'Content-Type': 'application/json' } },
    body: accepted
  })
  return unwrap(result).job_id
}

export async function fetchStatus(jobId: string): Promise<JobStatus> {
  return unwrap(
    await client.GET('/objects/host_relation_discovery/{job_id}', {
      params: { path: { job_id: jobId } }
    })
  )
}

/** What narrows a list of a scan down. Empty fields leave it be. */
export interface RowQuery {
  part: RowsPart
  finding?: string
  outcome?: Outcome | undefined
  search?: string
  folder?: string
  offset: number
  limit: number
  /** Also answer with the key of every matching relation, on all pages. */
  allKeys?: boolean
}

export async function fetchRows(jobId: string, query: RowQuery): Promise<RowsPage> {
  return unwrap(
    await client.GET('/objects/host_relation_discovery/{job_id}/collections/rows', {
      params: {
        path: { job_id: jobId },
        query: {
          part: query.part,
          finding: query.finding ?? '',
          ...(query.outcome ? { outcome: query.outcome } : {}),
          search: query.search ?? '',
          folder: query.folder ?? '',
          // The spec declares every query parameter a string; the server reads the number.
          offset: String(query.offset),
          limit: String(query.limit),
          all_keys: query.allKeys ? 'true' : 'false'
        }
      }
    })
  )
}
