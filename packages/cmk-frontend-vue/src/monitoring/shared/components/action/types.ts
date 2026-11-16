/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import type { Component, ComputedRef, InjectionKey } from 'vue'

import type { HostRef } from '@/monitoring/shared/api/types'

export interface ActionOutcome {
  /** A warning tells of an action that did not fail, but whose outcome is not known yet. */
  variant: 'success' | 'warning' | 'error'
  message: TranslatedString
  heading?: TranslatedString
}

/** What a feedback alert tells: an action still running, or how one went. */
export type ActionFeedbackEntry = { variant: 'loading'; message: TranslatedString } | ActionOutcome

/** Number of hosts the open action applies to, for forms that adapt their wording or hints. */
export const ACTION_TARGET_COUNT: InjectionKey<ComputedRef<number>> = Symbol(
  'monitoringActionTargetCount'
)

/** The kind of object an action applies to, for forms shared between several pages. */
export type ActionTargetKind = 'host' | 'service'

export interface MonitoringAction<Values = unknown, Target = HostRef> {
  id: string
  title: TranslatedString
  submitLabel: TranslatedString
  /** Explanation paragraphs shown between the headline and the submit buttons. */
  description?: readonly TranslatedString[]
  form?: Component
  formProps?: Record<string, unknown>
  /**
   * Makes an action without input ask for confirmation in an alert above the table instead of
   * opening the side pane. Both get the number of targets, the detail also the targets.
   */
  confirm?: {
    /** What the targets carry, e.g. "Downtimes: 2". */
    detail(count: number, targets: readonly Target[]): TranslatedString
    submitLabel(count: number): TranslatedString
  }
  defaultValues(): Values
  /**
   * What to tell while the action runs on the targets, for an action that may take a while, e.g.
   * a reschedule waiting for its check. Without it, or without a text for the targets, nothing is
   * told until the action has settled.
   */
  pending?(targets: readonly Target[]): TranslatedString | undefined
  /** The signal aborts once no one waits for the outcome any more, e.g. its pane has closed. */
  perform(targets: Target[], values: Values, signal?: AbortSignal): Promise<ActionOutcome>
}
