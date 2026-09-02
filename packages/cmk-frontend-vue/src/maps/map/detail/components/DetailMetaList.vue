<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Label/value facts about an object, as a definition list.

Both the status and the context tab state facts this way, so the two-column
grid lives here once. A value that needs attention (a soft attempt, a check
outside its notification period) is toned rather than badged -- it is still a
fact, not an alert.
-->
<script setup lang="ts">
import type { MetaRow } from '../statusFacts'

defineProps<{
  rows: MetaRow[]
  /** Stack label above value, for long labels with wide values (topology). */
  stacked?: boolean
}>()
</script>

<template>
  <dl
    v-if="rows.length"
    class="maps-detail-meta-list"
    :class="stacked ? 'maps-detail-meta-list--stacked' : ''"
  >
    <template v-for="row in rows" :key="row.label">
      <dt>{{ row.label }}</dt>
      <dd :class="row.tone ? `maps-detail-meta-list__value--${row.tone}` : ''">
        <a
          v-if="row.href"
          :href="row.href"
          target="_blank"
          rel="noopener noreferrer"
          class="maps-detail-meta-list__link"
          >{{ row.value }}</a
        >
        <template v-else>{{ row.value }}</template>
      </dd>
    </template>
  </dl>
</template>

<style scoped>
.maps-detail-meta-list {
  display: grid;
  grid-template-columns: 90px 1fr;
  gap: 4px 12px;
  margin: 0;
  font-size: 11px;
}

.maps-detail-meta-list dt {
  color: var(--font-color-dimmed);
  text-transform: uppercase;
  font-size: var(--font-size-small);
  letter-spacing: 0.04em;
  align-self: center;
}

.maps-detail-meta-list dd {
  color: var(--font-color);
  margin: 0;
  overflow-wrap: anywhere;
}

/* Topology labels ("Contact groups") do not fit the 90px first column, and
   their values are rows of chips -- so the label gets its own line. */
.maps-detail-meta-list--stacked {
  grid-template-columns: 1fr;
  gap: 6px;
}

.maps-detail-meta-list--stacked dt {
  margin-top: var(--dimension-3);
}

.maps-detail-meta-list__value--warn {
  color: var(--maps-map-view-acknowledged);
}

.maps-detail-meta-list__link {
  color: inherit;
  text-decoration: none;
}

.maps-detail-meta-list__link:hover,
.maps-detail-meta-list__link:focus-visible {
  color: var(--color-corporate-green-50);
  text-decoration: underline;
}
</style>
