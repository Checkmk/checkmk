<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { fromDate as instantToZoned } from '@internationalized/date'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import {
  formatDate,
  formatTime,
  timeZoneRegionLabel,
  timeZoneShortLabel,
  zonedToParts
} from '../../dateTimeUtils'
import type { ResolvedDateTimeSettings } from '../../types'
import { useNowTicker } from '../../useNowTicker'

const props = defineProps<{
  /** Resolved display settings; supplies the displayed timezone and the readout's formats. */
  settings: ResolvedDateTimeSettings
  /** IANA timezone of the server; without it the server readout stays an em dash. */
  serverTimeZone?: string | undefined
}>()

const { _t } = usei18n()

const now = useNowTicker()

const timeZoneText = computed(() =>
  _t('Timezone: %{region} (%{zone})', {
    region: timeZoneRegionLabel(props.settings.timeZone),
    zone: timeZoneShortLabel(props.settings.timeZone, now.value)
  })
)

const serverTimeText = computed(() => {
  if (!props.serverTimeZone) {
    return _t('Server time: %{time}', { time: '—' })
  }
  const parts = zonedToParts(instantToZoned(now.value, props.serverTimeZone))
  return _t('Server time: %{date}, %{time} (%{zone})', {
    date: formatDate(parts.date, props.settings.dateFormat),
    time: formatTime(parts.time, props.settings.hourCycle),
    zone: timeZoneShortLabel(props.serverTimeZone, now.value)
  })
})
</script>

<template>
  <div class="cmk-time-zone-info">
    <CmkParagraph class="cmk-time-zone-info__line">{{ timeZoneText }}</CmkParagraph>
    <CmkParagraph class="cmk-time-zone-info__line">{{ serverTimeText }}</CmkParagraph>
  </div>
</template>

<style scoped>
.cmk-time-zone-info {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
}

.cmk-time-zone-info .cmk-time-zone-info__line {
  color: var(--font-color-secondary);
}
</style>
