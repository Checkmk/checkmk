/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * The monitoring pages' acknowledge and downtime forms, set up the way the site
 * has them, for every Maps dialog that sends one of the two commands: about one
 * object or about many, the operator is asked the same.
 */
import { getLocalTimeZone, now } from '@internationalized/date'

import type { AcknowledgeOptions, CommandsApi } from '@/maps/api/commands'
import type { CommandTarget } from '@/maps/types/api'
import type { ScheduleDowntimeOptions } from '@/monitoring/shared/api/actions/downtime'
import type { AcknowledgeValues } from '@/monitoring/shared/components/action/actions/AcknowledgeForm.vue'
import {
  type ScheduleDowntimeFormValues,
  defaultScheduleDowntimeValues
} from '@/monitoring/shared/components/action/actions/ScheduleDowntimeForm.vue'
import { acknowledgeDefaults } from '@/monitoring/shared/components/action/actions/acknowledge'
import {
  downtimePresets,
  scheduleDowntimeOptions
} from '@/monitoring/shared/components/action/actions/scheduleDowntime'
import type { ActionTargetKind } from '@/monitoring/shared/components/action/types'

import { useMapsCommandSettings } from './commandSettings'

export function useCommandForms() {
  const settings = useMapsCommandSettings()
  const ackDefaults = acknowledgeDefaults(settings.acknowledge_defaults)
  const presets = downtimePresets(settings.downtime_presets)

  return {
    acknowledgeProps: (targetKind: ActionTargetKind) => ({
      targetKind,
      presetsUrl: settings.acknowledge_presets_url,
      notificationRulesUrl: settings.notification_rules_url
    }),
    // Read per open: the expiry is an offset from the moment the dialog opens.
    acknowledgeValues: (): AcknowledgeValues => ({
      comment: '',
      expireOnEnabled: false,
      expireOn: now(getLocalTimeZone()).add({ seconds: ackDefaults.expireSeconds }),
      sticky: ackDefaults.sticky,
      persistent: ackDefaults.persistent,
      notify: ackDefaults.notify
    }),
    downtimeProps: (targetKind: ActionTargetKind) => ({
      targetKind,
      recurrences: settings.downtime_recurrences,
      presets,
      presetsUrl: settings.downtime_presets_url
    }),
    downtimeValues: (): ScheduleDowntimeFormValues => defaultScheduleDowntimeValues(presets),
    downtimeOptions: (values: ScheduleDowntimeFormValues): ScheduleDowntimeOptions | null =>
      scheduleDowntimeOptions(values, presets)
  }
}

export function acknowledgeOptions(values: AcknowledgeValues): AcknowledgeOptions {
  return {
    comment: values.comment,
    sticky: values.sticky,
    notify: values.notify,
    persistent: values.persistent,
    ...(values.expireOnEnabled && values.expireOn
      ? { expire_on: values.expireOn.toDate().toISOString() }
      : {})
  }
}

/** The forms word a command about services as such only where every target is one. */
export function targetKindOf(targets: readonly CommandTarget[]): ActionTargetKind {
  return targets.length > 0 && targets.every(({ service }) => service !== null) ? 'service' : 'host'
}

/** The child hosts of the targeted hosts that are not targeted themselves, as targets. */
export async function childHostTargets(
  commands: CommandsApi,
  targets: readonly CommandTarget[]
): Promise<CommandTarget[]> {
  const hosts = new Set(targets.flatMap(({ host, service }) => (service === null ? [host] : [])))
  const children = await commands.childHosts(null, [...hosts])
  return children.map((host) => ({ host, service: null, site: null }))
}
