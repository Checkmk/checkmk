<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { fromDate as instantToZoned } from '@internationalized/date'
import CmkLabel from 'cmk-ui-library/components/CmkLabel.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import { formatDate, formatTime, timeZoneRegionLabel, zonedToParts } from '../../dateTimeUtils'
import type { ResolvedDateTimeSettings } from '../../types'
import { useNowTicker } from '../../useNowTicker'
import TimeZoneTag from './TimeZoneTag.vue'

const props = defineProps<{
  /** Resolved display settings; supplies the displayed timezone and the readout's formats. */
  settings: ResolvedDateTimeSettings
  /** IANA timezone of the server; without it the server readout stays an em dash. */
  serverTimeZone?: string | undefined
}>()

const { _t } = usei18n()

const now = useNowTicker()

const regionLabel = computed(() => timeZoneRegionLabel(props.settings.timeZone))

const serverTimeText = computed(() => {
  if (!props.serverTimeZone) {
    return null
  }
  const parts = zonedToParts(instantToZoned(now.value, props.serverTimeZone))
  return `${formatDate(parts.date, props.settings.dateFormat)}, ${formatTime(parts.time, props.settings.hourCycle)}`
})
</script>

<template>
  <div class="cmk-time-zone-info">
    <div class="cmk-time-zone-info__entry">
      <CmkLabel>{{ _t('Timezone:') }}</CmkLabel>
      <TimeZoneTag :time-zone="settings.timeZone" :at="now" />
      <CmkParagraph aria-hidden="true">{{ untranslated(regionLabel) }}</CmkParagraph>
    </div>
    <div class="cmk-time-zone-info__entry">
      <CmkLabel>{{ _t('Current server time:') }}</CmkLabel>
      <TimeZoneTag v-if="serverTimeZone" :time-zone="serverTimeZone" :at="now" />
      <CmkParagraph>{{
        serverTimeText !== null ? untranslated(serverTimeText) : untranslated('—')
      }}</CmkParagraph>
    </div>
  </div>
</template>

<style scoped>
.cmk-time-zone-info {
  display: grid;
  grid-auto-flow: column;
  grid-template-rows: auto auto auto;
  justify-content: start;
  align-items: center;
  gap: var(--dimension-4) var(--dimension-6);
}

.cmk-time-zone-info__entry {
  display: grid;
  grid-template-rows: subgrid;
  grid-row: span 3;
  place-items: center start;
}

.cmk-time-zone-info__entry > :last-child {
  grid-row: 3;
}
</style>
