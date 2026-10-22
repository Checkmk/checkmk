/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { DowntimeRecurrenceOption } from './actions/ScheduleDowntimeForm.vue'

/**
 * What a page sends about the commands it offers, structurally typed so this stays independent of
 * which page's generated module it arrived in.
 */
export interface MonitoringCommandsPayload {
  actions?: { ident: string; title: string; icon: string }[] | undefined
  acknowledge_presets_url?: string | null | undefined
  notification_rules_url?: string | null | undefined
  acknowledge_defaults?:
    | { sticky: boolean; persistent: boolean; notify: boolean; expire_seconds: number }
    | undefined
  downtime_recurrences?: DowntimeRecurrenceOption[] | undefined
  downtime_presets?: { title: string; end: number | string }[] | undefined
  downtime_presets_url?: string | null | undefined
}
