/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import {
  ScheduleDowntimeApi,
  type ScheduleDowntimeOptions
} from '@/monitoring/shared/api/actions/downtime'

import type { ActionTargetKind, MonitoringAction } from '../types'
import ScheduleDowntimeForm, {
  type DowntimeRecurrenceOption,
  type ScheduleDowntimeFormValues,
  defaultScheduleDowntimeValues,
  downtimeWindow
} from './ScheduleDowntimeForm.vue'

export const SCHEDULE_DOWNTIME_ACTION_ID = 'schedule_downtimes'

export interface ScheduleDowntimeKindConfig<Target> {
  submitLabel: TranslatedString
  description: readonly TranslatedString[]
  targetKind: ActionTargetKind
  /** Perform the API call for the resolved targets and return the count actually acted on. */
  schedule(
    api: ScheduleDowntimeApi,
    targets: Target[],
    values: ScheduleDowntimeFormValues,
    options: ScheduleDowntimeOptions
  ): Promise<number>
  successMessage(count: number): TranslatedString
  errorMessage: TranslatedString
  /** The intervals the site offers to repeat the downtime on. */
  recurrences: DowntimeRecurrenceOption[]
  /** Where the duration presets are edited. */
  presetsUrl: string | null
}

/** Shared downtime-scheduling flow for hosts and services: only the API call and wording differ. */
export function createScheduleDowntimeAction<Target>(
  config: ScheduleDowntimeKindConfig<Target>
): MonitoringAction<ScheduleDowntimeFormValues, Target> {
  const { _t } = usei18n()
  const api = new ScheduleDowntimeApi()

  return {
    id: SCHEDULE_DOWNTIME_ACTION_ID,
    title: _t('Schedule downtimes'),
    submitLabel: config.submitLabel,
    description: config.description,
    form: ScheduleDowntimeForm,
    formProps: {
      targetKind: config.targetKind,
      recurrences: config.recurrences,
      presetsUrl: config.presetsUrl
    },
    defaultValues: defaultScheduleDowntimeValues,
    perform: async (targets: Target[], values: ScheduleDowntimeFormValues) => {
      const window = downtimeWindow(values)
      if (window === null) {
        return {
          variant: 'error',
          message: _t('Please choose a downtime duration greater than zero.')
        }
      }
      try {
        const durationMinutes = values.flexible
          ? Math.round((new Date(window.end).getTime() - new Date(window.start).getTime()) / 60_000)
          : 0
        const count = await config.schedule(api, targets, values, {
          comment: values.comment.trim(),
          startTime: window.start,
          endTime: window.end,
          durationMinutes,
          recur: values.recur
        })
        return { variant: 'success', message: config.successMessage(count) }
      } catch {
        return { variant: 'error', message: config.errorMessage }
      }
    }
  }
}
