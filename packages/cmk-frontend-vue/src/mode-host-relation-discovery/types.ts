/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'

/** The wire shapes, as the internal API declares them - not restated here. */
export type RelationRow = components['schemas']['RelationRowModel']
export type RelationReason = components['schemas']['RelationReasonModel']
export type RowsPage = components['schemas']['RowsPageModel']
export type JobStatus = components['schemas']['RelationJobStatusModel']
export type ScanSummary = components['schemas']['ScanSummaryModel']
export type RunSummary = components['schemas']['RunSummaryModel']
export type FindingSummary = components['schemas']['FindingSummaryModel']
export type Suggestions = components['schemas']['SuggestionsModel']
export type WordFinding = components['schemas']['WordFindingModel']
export type FindingRequest = components['schemas']['FindingModel']
export type AcceptRequest = components['schemas']['AcceptRequestModel']

/** What storing a proposed relation does. */
export type Outcome = RelationRow['outcome']

/** Which list of a scan - or, for a run, of what it could not store - a page is read from. */
export type RowsPart = 'relations' | 'failed'

/** The meaning of a finding the user says is no relation at all. */
export const NOT_RELATED = ''

/** What the user says one word stands for: a kind of relation, or none. */
export interface WordChoice {
  meaning: string
}

export function wordFindingId(finding: Pick<WordFinding, 'word'>): string {
  return `word:${finding.word}`
}

/**
 * What the scan is asked for: every finding the user gave a meaning, one each, so that every
 * relation it proposes can be traced back to the finding it came from.
 */
export function findingsToScan(
  words: WordFinding[],
  wordChoices: Record<string, WordChoice>
): FindingRequest[] {
  return words.flatMap((finding) => {
    const meaning = wordChoices[finding.word]?.meaning ?? NOT_RELATED
    return finding.pairs > 0 && meaning !== NOT_RELATED
      ? [{ id: wordFindingId(finding), kind: meaning, words: [finding.word] }]
      : []
  })
}

/**
 * The choices for what a suggestion found, keeping every answer already given. A word the kind
 * looked for declares starts out meaning it; anything else means nothing until the user says so.
 */
export function withNewChoices(
  found: Suggestions,
  words: Record<string, WordChoice>,
  kind: string,
  added: { word?: string } = {}
): Record<string, WordChoice> {
  const nextWords = { ...words }
  for (const finding of found.words) {
    // A word the user typed that the page did not list yet is one they mean - unless it finds
    // nothing. One it listed already keeps the answer it has: typing it again says nothing new.
    const meant = finding.pairs > 0 && (finding.kind === kind || finding.word === added.word)
    nextWords[finding.word] = nextWords[finding.word] ?? { meaning: meant ? kind : NOT_RELATED }
  }
  return nextWords
}

export function withoutKey<T>(record: Record<string, T>, key: string): Record<string, T> {
  return Object.fromEntries(Object.entries(record).filter(([other]) => other !== key))
}

/** Whether a word can be read out of a host name at all - the rule the backend applies. */
export function isNameWord(word: string): boolean {
  return word !== '' && !/[-_.]/.test(word)
}

/**
 * What the user made of a scan in step 3: every finding is stored or not as a whole, and single
 * relations of a stored one can be taken out.
 */
export interface Decisions {
  findings: Set<string>
  /** Taken-out relations, by key, with the finding each belongs to. */
  excluded: Map<string, string>
}

export function noDecisions(): Decisions {
  return { findings: new Set(), excluded: new Map() }
}

/** How many relations storing these decisions stores. */
export function relationsToStore(summaries: FindingSummary[], decisions: Decisions): number {
  let count = 0
  for (const summary of summaries) {
    if (decisions.findings.has(summary.id)) {
      count += summary.counts.link ?? 0
    }
  }
  for (const finding of decisions.excluded.values()) {
    if (decisions.findings.has(finding)) {
      count -= 1
    }
  }
  return count
}

/** The decisions as the accept endpoint takes them. */
export function acceptRequest(scanId: string, decisions: Decisions): AcceptRequest {
  return {
    scan_id: scanId,
    findings: [...decisions.findings],
    excluded: [...decisions.excluded.keys()]
  }
}
