<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
export type SummaryRow = { label: string; value: string }

export type SummaryEntry =
  | { kind: 'row'; label: string; value: string }
  | { kind: 'section'; title: string }

type SummaryGroup = { kind: 'rows'; rows: SummaryRow[] } | { kind: 'section'; title: string }
</script>

<script setup lang="ts">
import { computed } from 'vue'

import usei18n from '@/lib/i18n'

import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

const { _t } = usei18n()

const props = defineProps<{
  entries: ReadonlyArray<SummaryEntry>
  heading?: string
  footnote?: string
}>()

// Collapse consecutive `row` entries into a single `rows` group so each
// section's rows render in their own <ul>, and section headings sit between
// lists rather than inside one. Keeps the DOM semantically tidy without
// pushing grouping responsibility onto every consumer.
const groups = computed<SummaryGroup[]>(() => {
  const result: SummaryGroup[] = []
  let pending: SummaryRow[] = []
  for (const entry of props.entries) {
    if (entry.kind === 'section') {
      if (pending.length > 0) {
        result.push({ kind: 'rows', rows: pending })
        pending = []
      }
      result.push({ kind: 'section', title: entry.title })
    } else {
      pending.push({ label: entry.label, value: entry.value })
    }
  }
  if (pending.length > 0) {
    result.push({ kind: 'rows', rows: pending })
  }
  return result
})
</script>

<template>
  <div class="mode-otel-configuration-summary">
    <CmkHeading type="h4">{{ heading ?? _t('Configuration details:') }}</CmkHeading>
    <template v-for="(group, idx) in groups" :key="idx">
      <CmkHeading
        v-if="group.kind === 'section'"
        type="h4"
        class="mode-otel-configuration-summary__section-heading"
      >
        {{ group.title }}
      </CmkHeading>
      <ul v-else class="mode-otel-configuration-summary__rows">
        <li
          v-for="(row, rIdx) in group.rows"
          :key="rIdx"
          class="mode-otel-configuration-summary__row"
        >
          <strong>{{ row.label }}:</strong> {{ row.value }}
        </li>
      </ul>
    </template>
    <CmkParagraph v-if="footnote" class="mode-otel-configuration-summary__footnote">{{
      footnote
    }}</CmkParagraph>
  </div>
</template>

<style scoped>
.mode-otel-configuration-summary {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
}

.mode-otel-configuration-summary__rows {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--dimension-2);
}

.mode-otel-configuration-summary__row {
  list-style: disc inside;
  display: list-item;
}

.mode-otel-configuration-summary__section-heading {
  margin-top: var(--dimension-2);
}

.mode-otel-configuration-summary__footnote {
  margin: 0;
}
</style>
