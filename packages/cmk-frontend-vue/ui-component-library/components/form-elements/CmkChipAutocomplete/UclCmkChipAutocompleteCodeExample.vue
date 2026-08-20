<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkChipAutocomplete from 'cmk-ui-library/components/CmkChipAutocomplete.vue'
import { ref } from 'vue'

const selected = ref<string[]>([])

async function suggestLabels(query: string): Promise<string[]> {
  const response = await fetch(
    `ajax_autocomplete.py?ident=label&value=${encodeURIComponent(query)}`
  )
  const body = (await response.json()) as { result: { choices: [string, string][] } }
  return body.result.choices.map(([value]) => value)
}
</script>

<template>
  <CmkChipAutocomplete v-model="selected" :suggest="suggestLabels" suggest-when-empty />
</template>
