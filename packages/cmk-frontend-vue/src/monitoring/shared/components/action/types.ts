/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Component } from 'vue'

import type { TranslatedString } from '@/lib/i18nString'

import type { HostRef } from '@/monitoring/shared/api/types'

import type { ActionFeedback } from './ActionFeedback.vue'

export interface MonitoringAction<Values = unknown> {
  id: string
  title: TranslatedString
  submitLabel: TranslatedString
  subtitle(count: number): TranslatedString
  form?: Component
  defaultValues(): Values
  perform(targets: HostRef[], values: Values): Promise<ActionFeedback>
}
