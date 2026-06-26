<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import CmkChipSelect from '@/components/CmkChipSelect.vue'
import type { Suggestions } from '@/components/CmkSuggestions'

defineProps<{ screenshotMode: boolean }>()

const empty = ref<string | null>(null)
const preselected = ref<string | null>('3h')
const customOption = ref<string | null>(null)

const ranges: Suggestions = {
  type: 'fixed',
  suggestions: [
    { name: '1h', title: 'Last hour' },
    { name: '3h', title: 'Last 3 hours' },
    { name: '1d', title: 'Last day' },
    { name: '1w', title: 'Last week' }
  ]
}
</script>

<template>
  <h2>Empty selection</h2>
  <CmkChipSelect v-model="empty" :options="ranges" input-hint="More ranges" label="time range" />

  <h2>With selection (checkmark)</h2>
  <CmkChipSelect
    v-model="preselected"
    :options="ranges"
    input-hint="More ranges"
    label="time range"
  />

  <h2>Disabled</h2>
  <CmkChipSelect
    v-model="empty"
    :options="ranges"
    input-hint="More ranges"
    label="time range"
    disabled
  />

  <h2>Custom option content (#option slot)</h2>
  <CmkChipSelect
    v-model="customOption"
    :options="ranges"
    input-hint="More ranges"
    label="time range"
  >
    <template #option="{ suggestion }"> {{ suggestion.title }} ({{ suggestion.name }}) </template>
  </CmkChipSelect>
</template>
