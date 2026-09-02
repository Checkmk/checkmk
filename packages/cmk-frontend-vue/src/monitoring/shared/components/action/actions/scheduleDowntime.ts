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
  type DowntimePresetOption,
  type DowntimeRecurrenceOption,
  type ScheduleDowntimeFormValues,
  defaultScheduleDowntimeValues,
  downtimeWindow,
  isUntilKeyword
} from './ScheduleDowntimeForm.vue'

export const SCHEDULE_DOWNTIME_ACTION_ID = 'schedule_downtimes'

/**
 * The payload's durations, structurally typed so this stays free of the generated modules.
 *
 * An end the form cannot resolve to a time drops the whole duration, the way the classic form
 * skips such a preset rather than offering a chip that leads nowhere. The backend already
 * leaves those out, so this is the second line of defence rather than a live path.
 */
export function downtimePresets(
  payload: { title: string; end: number | string }[] | undefined
): DowntimePresetOption[] {
  const presets: DowntimePresetOption[] = []
  for (const preset of payload ?? []) {
    if (typeof preset.end === 'number' || isUntilKeyword(preset.end)) {
      presets.push({ title: preset.title, end: preset.end })
    }
  }
  return presets
}

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
  /** The durations the site offers; the first one is where the dialog starts. */
  presets: DowntimePresetOption[]
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
      presets: config.presets,
      presetsUrl: config.presetsUrl
    },
    defaultValues: () => defaultScheduleDowntimeValues(config.presets),
    perform: async (targets: Target[], values: ScheduleDowntimeFormValues) => {
      const window = downtimeWindow(values, config.presets)
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
