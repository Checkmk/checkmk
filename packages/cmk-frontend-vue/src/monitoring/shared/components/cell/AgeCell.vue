<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { AgeEmphasis } from '@/monitoring/shared/ageEmphasis'

import StringCell, { type StringCellTone } from './StringCell.vue'

defineProps<{
  value: string | undefined
  /** Dims the age, unless it deserves attention. Colour only: bold would outgrow the fixed column width. */
  emphasis: AgeEmphasis
  columnId?: string | undefined
}>()

const TONES: Record<AgeEmphasis, StringCellTone | undefined> = {
  plain: 'secondary',
  recent: undefined,
  stale: 'error'
}
</script>

<template>
  <StringCell :column-id="columnId" :value="value" :tone="TONES[emphasis]" />
</template>
