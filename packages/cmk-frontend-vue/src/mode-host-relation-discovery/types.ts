/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'

/** The wire shapes, as the internal API declares them - not restated here. */
export type RelationRow = components['schemas']['RelationRowModel']
export type RelationGroup = components['schemas']['RelationGroupModel']
export type RelationConflict = components['schemas']['RelationConflictModel']
export type RelationReason = components['schemas']['RelationReasonModel']
export type RowsPage = components['schemas']['RowsPageModel']
export type JobStatus = components['schemas']['RelationJobStatusModel']
export type ScanSummary = components['schemas']['ScanSummaryModel']
export type RunSummary = components['schemas']['RunSummaryModel']
export type FindingSummary = components['schemas']['FindingSummaryModel']
export type Suggestions = components['schemas']['SuggestionsModel']
export type WordFinding = components['schemas']['WordFindingModel']
export type ValueFinding = components['schemas']['ValueFindingModel']
export type ValueExample = components['schemas']['ValueExampleModel']
export type FindingRequest = components['schemas']['FindingModel']
export type AcceptRequest = components['schemas']['AcceptRequestModel']
/** A host label or custom host attribute, by name. */
export type SharedValue = components['schemas']['HostValueModel']
/** The folder and site a scan looks for relations in; empty is all of Setup. */
export type ScanScope = components['schemas']['ScopeModel']
/** Where a suggestion looks: in the host names, or in the labels and attributes hosts share. */
export type LookIn = NonNullable<
  components['schemas']['SuggestEvidenceRequestModel']['look_in']
>[number]

/** What storing a proposed relation does. */
export type Outcome = RelationRow['outcome']

/** Which list of a scan - or, for a run, of what it could not store - a page is read from. */
export type RowsPart = 'relations' | 'groups' | 'conflicts' | 'failed'

/** The meaning of a finding the user says is no relation at all. */
export const NOT_RELATED = ''

/**
 * How the host at the deciding end of a value finding is told apart from the others:
 * the way Checkmk found in the hosts, or one the user picked instead.
 */
export type Marker = 'detected' | 'words' | 'label' | 'attribute' | 'ask'

const MARKERS: readonly Marker[] = ['detected', 'words', 'label', 'attribute', 'ask']

export function isMarker(value: string): value is Marker {
  return (MARKERS as readonly string[]).includes(value)
}

/** What the user says one word stands for: a kind of relation, or none. */
export interface WordChoice {
  meaning: string
}

/** What the user says a label or attribute the hosts share stands for, and how to tell them apart. */
export interface ValueChoice {
  meaning: string
  marker: Marker
  /** The label or attribute that marks the deciding end, for a marker the user picked. */
  markName: string
  /** The value it carries there - for the detected value as well. */
  markValue: string
}

export function wordFindingId(finding: Pick<WordFinding, 'word'>): string {
  return `word:${finding.word}`
}

export function valueKey(finding: Pick<ValueFinding, 'source' | 'name'>): string {
  return `${finding.source}:${finding.name}`
}

/** The words the user said stand for a kind, in the order the findings are listed. */
export function wordsOf(
  kind: string,
  findings: WordFinding[],
  choices: Record<string, WordChoice>
): string[] {
  return findings
    .filter((finding) => finding.pairs > 0 && choices[finding.word]?.meaning === kind)
    .map((finding) => finding.word)
}

/** Whether a label or attribute value is what tells the hosts apart. */
export function isMarkedByValue(marker: Marker): marker is 'label' | 'attribute' {
  return marker === 'label' || marker === 'attribute'
}

/**
 * The marker a value choice goes by once "detected" is resolved: the words Checkmk found, the
 * value Checkmk found - or asking, where Checkmk found nothing.
 */
export function resolvedMarker(finding: ValueFinding, choice: ValueChoice): Marker {
  if (choice.marker !== 'detected') {
    return choice.marker
  }
  switch (finding.told_apart?.by) {
    case 'names':
      return 'words'
    case 'value':
      return finding.told_apart.source === 'label' ? 'label' : 'attribute'
    default:
      return 'ask'
  }
}

/** Whether a value choice says everything the scan needs to read it. */
export function isComplete(finding: ValueFinding, choice: ValueChoice): boolean {
  if (choice.meaning === NOT_RELATED) {
    return true
  }
  const marker = resolvedMarker(finding, choice)
  if (!isMarkedByValue(marker)) {
    return true
  }
  const name = choice.marker === 'detected' ? (finding.told_apart?.name ?? '') : choice.markName
  return name !== '' && choice.markValue !== ''
}

/**
 * What the scan is asked for: every finding the user gave a meaning, one each, so that every
 * relation it proposes can be traced back to the finding it came from.
 */
export function findingsToScan(
  words: WordFinding[],
  wordChoices: Record<string, WordChoice>,
  values: ValueFinding[],
  valueChoices: Record<string, ValueChoice>
): FindingRequest[] {
  const named: FindingRequest[] = words.flatMap((finding) => {
    const meaning = wordChoices[finding.word]?.meaning ?? NOT_RELATED
    return finding.pairs > 0 && meaning !== NOT_RELATED
      ? [{ id: wordFindingId(finding), kind: meaning, words: [finding.word] }]
      : []
  })
  const shared: FindingRequest[] = values.flatMap((finding) => {
    const choice = valueChoices[valueKey(finding)]
    if (!choice || choice.meaning === NOT_RELATED || finding.groups === 0) {
      return []
    }
    const found: FindingRequest = {
      id: valueKey(finding),
      kind: choice.meaning,
      paired_by: { source: finding.source, name: finding.name }
    }
    const marker = resolvedMarker(finding, choice)
    switch (marker) {
      case 'words': {
        const markingWords =
          choice.marker === 'detected'
            ? (finding.told_apart?.words ?? [])
            : wordsOf(choice.meaning, words, wordChoices)
        return markingWords.length > 0 ? [{ ...found, words: markingWords }] : [found]
      }
      case 'label':
      case 'attribute':
        return [
          {
            ...found,
            marked_by: {
              source: marker,
              name:
                choice.marker === 'detected' ? (finding.told_apart?.name ?? '') : choice.markName,
              value: choice.markValue
            }
          }
        ]
      case 'ask':
      case 'detected':
        return [found]
    }
  })
  return [...named, ...shared]
}

/**
 * The choices for what a suggestion found, keeping every answer already given. A word the kind
 * looked for declares starts out meaning it; anything else means nothing until the user says so.
 */
export function withNewChoices(
  found: Suggestions,
  words: Record<string, WordChoice>,
  values: Record<string, ValueChoice>,
  kind: string,
  added: { word?: string } = {}
): { words: Record<string, WordChoice>; values: Record<string, ValueChoice> } {
  const nextWords = { ...words }
  for (const finding of found.words) {
    // A word the user typed that the page did not list yet is one they mean - unless it finds
    // nothing. One it listed already keeps the answer it has: typing it again says nothing new.
    // A value the user adds is never meant on its own: how widely it is shared decides whether
    // it pairs anything, and that is what the user has to see first.
    const meant = finding.pairs > 0 && (finding.kind === kind || finding.word === added.word)
    nextWords[finding.word] = nextWords[finding.word] ?? { meaning: meant ? kind : NOT_RELATED }
  }
  const nextValues = { ...values }
  for (const finding of found.values) {
    const key = valueKey(finding)
    nextValues[key] = nextValues[key] ?? newValueChoice(finding)
  }
  return { words: nextWords, values: nextValues }
}

export function withoutKey<T>(record: Record<string, T>, key: string): Record<string, T> {
  return Object.fromEntries(Object.entries(record).filter(([other]) => other !== key))
}

export function newValueChoice(finding: ValueFinding): ValueChoice {
  return {
    meaning: NOT_RELATED,
    marker: 'detected',
    markName: '',
    markValue: finding.told_apart?.suggested ?? ''
  }
}

/** Whether a word can be read out of a host name at all - the rule the backend applies. */
export function isNameWord(word: string): boolean {
  return word !== '' && !/[-_.]/.test(word)
}

/** The members a group can be answered with - the ones that can be written. */
export function candidates(group: RelationGroup): string[] {
  return group.members.filter((member) => !(member in group.refusals))
}

/** The hosts the named one would be related to, as the server stores them. */
export function partnersOf(group: RelationGroup, host: string): string[] {
  return group.partners[host] ?? []
}

/**
 * What the user made of a scan in step 3: every finding is stored or not as a whole, single
 * relations of a stored one can be taken out, and questions and conflicts are answered.
 */
export interface Decisions {
  findings: Set<string>
  /** Taken-out relations, by key, with the finding each belongs to. */
  excluded: Map<string, string>
  /** Per group, by key, the host named - with the number of relations that makes. */
  answers: Map<string, { host: string; finding: string; relations: number }>
  /** Per conflict, by key, the claim to store - with its finding and whether storing it
   * stores anything. */
  resolutions: Map<string, { claim: string; finding: string; stores: boolean }>
}

export function noDecisions(): Decisions {
  return { findings: new Set(), excluded: new Map(), answers: new Map(), resolutions: new Map() }
}

/** How many relations storing these decisions stores, per finding they come from. */
export function relationsToStorePerFinding(
  summaries: FindingSummary[],
  decisions: Decisions
): Map<string, number> {
  const count = new Map<string, number>()
  const add = (finding: string, relations: number) =>
    count.set(finding, (count.get(finding) ?? 0) + relations)
  for (const summary of summaries) {
    if (decisions.findings.has(summary.id)) {
      add(summary.id, summary.counts.link ?? 0)
    }
  }
  for (const finding of decisions.excluded.values()) {
    if (decisions.findings.has(finding)) {
      add(finding, -1)
    }
  }
  for (const answer of decisions.answers.values()) {
    if (decisions.findings.has(answer.finding)) {
      add(answer.finding, answer.relations)
    }
  }
  for (const resolution of decisions.resolutions.values()) {
    if (resolution.stores) {
      add(resolution.finding, 1)
    }
  }
  return count
}

/** The decisions as the accept endpoint takes them. */
export function acceptRequest(scanId: string, decisions: Decisions): AcceptRequest {
  return {
    scan_id: scanId,
    findings: [...decisions.findings],
    excluded: [...decisions.excluded.keys()],
    answers: Object.fromEntries(
      [...decisions.answers].map(([key, answer]) => [key, answer.host] as const)
    ),
    resolutions: Object.fromEntries(
      [...decisions.resolutions].map(([key, resolution]) => [key, resolution.claim] as const)
    )
  }
}
