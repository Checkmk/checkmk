<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

export interface FigureTooltipRow {
  key: string
  count: number
  text: string
  color?: string
}

export interface FigureTooltipContent {
  title: string
  state: string | null
  rows: readonly FigureTooltipRow[]
}

const props = defineProps<FigureTooltipContent>()

const withColor = computed(() => props.rows.some((row) => row.color !== undefined))
</script>

<template>
  <h3 class="db-figure-tooltip__title">{{ title }}</h3>
  <span v-if="state">{{ state }}</span>
  <table v-if="rows.length > 0">
    <tr v-for="row in rows" :key="row.key">
      <td
        v-if="withColor"
        class="db-figure-tooltip__color"
        :style="{ backgroundColor: row.color }"
      />
      <td class="db-figure-tooltip__count">{{ row.count }}</td>
      <td>{{ row.text }}</td>
    </tr>
  </table>
</template>

<style scoped>
.db-figure-tooltip__title {
  margin: 2px 0;
}

.db-figure-tooltip__color {
  width: 10px;
}

.db-figure-tooltip__count {
  padding-left: 4px;
  text-align: right;
  vertical-align: top;
}
</style>
