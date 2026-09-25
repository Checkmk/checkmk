/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import type { Outcome } from './types'

const { _t, _tn } = usei18n()

/**
 * What an outcome is called wherever it is shown. In one place, because the rows, the counts
 * and the filters have to agree - and because the wire names ("already_linked") are not
 * something a user should ever be shown.
 */
export function outcomeLabel(outcome: Outcome, done = false): TranslatedString {
  switch (outcome) {
    case 'link':
      // The one outcome a relation is actually stored for reads differently once it happened.
      return done ? _t('Stored') : _t('New')
    case 'already_linked':
      return _t('Already related')
    case 'stored_otherwise':
      return _t('Related in another way')
    case 'not_writable':
      return _t('Cannot be stored')
    case 'undecided':
      return _t('Needs your answer')
  }
}

/** The outcomes a list is filtered by, in the order the backend lists the rows. */
export const LISTED_OUTCOMES: readonly Outcome[] = [
  'link',
  'stored_otherwise',
  'not_writable',
  'already_linked'
]

export function outcomeColor(outcome: Outcome): 'success' | 'default' | 'warning' | 'unknown' {
  switch (outcome) {
    case 'link':
      return 'success'
    case 'already_linked':
      return 'default'
    case 'stored_otherwise':
    case 'not_writable':
      return 'warning'
    case 'undecided':
      return 'unknown'
  }
}

/** "8120 new", "1 question to answer" - an outcome with how many rows have it. */
export function countedOutcome(outcome: Outcome, count: number, done = false): TranslatedString {
  switch (outcome) {
    case 'link':
      return done
        ? _tn('%{count} stored', '%{count} stored', count, { count })
        : _tn('%{count} new', '%{count} new', count, { count })
    case 'already_linked':
      return _tn('%{count} already related', '%{count} already related', count, { count })
    case 'stored_otherwise':
      return _tn('%{count} related in another way', '%{count} related in another way', count, {
        count
      })
    case 'not_writable':
      return done
        ? _tn('%{count} could not be stored', '%{count} could not be stored', count, { count })
        : _tn('%{count} cannot be stored', '%{count} cannot be stored', count, { count })
    case 'undecided':
      return _tn('1 question to answer', '%{count} questions to answer', count, { count })
  }
}

/** The outcomes a finding's relations have, counted, in the order its rows are listed. */
export function countedOutcomes(counts: Record<string, number>, done = false): string {
  return LISTED_OUTCOMES.filter((outcome) => (counts[outcome] ?? 0) > 0)
    .map((outcome) => countedOutcome(outcome, counts[outcome] ?? 0, done))
    .join(' \u00b7 ')
}
