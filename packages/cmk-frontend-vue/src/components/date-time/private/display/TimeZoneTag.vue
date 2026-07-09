<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import { untranslated } from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import CmkTag from '@/components/CmkTag.vue'
import CmkVisuallyHidden from '@/components/CmkVisuallyHidden.vue'

import { timeZoneRegionLabel, timeZoneShortLabel } from '../../dateTimeUtils'

const props = defineProps<{
  /** IANA timezone id (e.g. `"Europe/Berlin"`). */
  timeZone: string
  /** Instant the offset is read at (offsets are DST-dependent); defaults to now. */
  at?: Date
  /** Accessible prefix, e.g. "Timezone" → "Timezone: Europe, Berlin, CEST (UTC+2)". Omit when an
   *  adjacent visible label already names the badge. */
  accessibleLabel?: TranslatedString
}>()

const shortLabel = computed(() => timeZoneShortLabel(props.timeZone, props.at ?? new Date()))
const regionLabel = computed(() => timeZoneRegionLabel(props.timeZone))

// Region + offset, both already localized, so this is assembled (not a translatable template).
const accessibleText = computed<TranslatedString>(() => {
  const zone = `${regionLabel.value}, ${shortLabel.value}`
  return untranslated(props.accessibleLabel ? `${props.accessibleLabel}: ${zone}` : zone)
})
</script>

<template>
  <span>
    <CmkTag
      class="cmk-time-zone-tag"
      variant="fill"
      aria-hidden="true"
      :content="untranslated(shortLabel)"
    />
    <CmkVisuallyHidden :text="accessibleText" />
  </span>
</template>

<style scoped>
.cmk-time-zone-tag {
  margin: 0;
}
</style>
