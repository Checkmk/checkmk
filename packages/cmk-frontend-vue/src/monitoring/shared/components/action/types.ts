/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import type { Component, ComputedRef, InjectionKey } from 'vue'

import type { HostRef } from '@/monitoring/shared/api/types'

import type { ActionFeedback } from './ActionFeedback.vue'

/** Number of hosts the open action applies to, for forms that adapt their wording or hints. */
export const ACTION_TARGET_COUNT: InjectionKey<ComputedRef<number>> = Symbol(
  'monitoringActionTargetCount'
)

export interface MonitoringAction<Values = unknown> {
  id: string
  title: TranslatedString
  submitLabel: TranslatedString
  /** Explanation paragraphs shown between the headline and the submit buttons. */
  description?: readonly TranslatedString[]
  form?: Component
  defaultValues(): Values
  perform(targets: HostRef[], values: Values): Promise<ActionFeedback>
}
