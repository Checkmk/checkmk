/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import type { ActionOutcome, MonitoringAction } from './types'

/** An action bound to its targets and default values, ready to run. */
export interface ActionRun {
  /** What to tell while it runs, if anything. */
  pending: TranslatedString | undefined
  /** The signal aborts once no one waits for the outcome any more. */
  perform: (signal?: AbortSignal) => Promise<ActionOutcome>
  /** The same for every run of the same command on the same object, if told apart at all. */
  key?: string
}

/** Bind an action to its targets, to run with its default values. */
export function prepareRun<Target>(
  action: MonitoringAction<unknown, Target>,
  targets: Target[]
): ActionRun {
  return {
    pending: action.pending?.(targets),
    perform: (signal) => action.perform(targets, action.defaultValues(), signal)
  }
}
