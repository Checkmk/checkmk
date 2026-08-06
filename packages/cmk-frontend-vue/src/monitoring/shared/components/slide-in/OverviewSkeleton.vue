<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkSkeleton from 'cmk-ui-library/components/CmkSkeleton.vue'

const CHIPS_PER_ROW = 5

withDefaults(defineProps<{ groups: { rows: number; chips?: boolean }[]; valueWidth?: string }>(), {
  valueWidth: '60%'
})
</script>

<template>
  <div class="monitoring-overview-skeleton" aria-hidden="true">
    <slot name="before" />
    <div
      v-for="(group, groupIndex) in groups"
      :key="groupIndex"
      class="monitoring-overview-skeleton__grid"
    >
      <template v-for="row in group.rows" :key="row">
        <CmkSkeleton type="text" width="90px" />
        <div v-if="group.chips" class="monitoring-overview-skeleton__chips">
          <CmkSkeleton v-for="chip in CHIPS_PER_ROW" :key="chip" type="box" width="72px" />
        </div>
        <CmkSkeleton v-else type="text" :width="valueWidth" />
      </template>
    </div>
  </div>
</template>

<style scoped>
.monitoring-overview-skeleton {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-double);
}

.monitoring-overview-skeleton__grid {
  display: grid;
  grid-template-columns: minmax(120px, max-content) 1fr;
  gap: var(--dimension-4) var(--spacing);
  align-items: center;
}

.monitoring-overview-skeleton__chips {
  display: flex;
  flex-flow: row wrap;
  gap: var(--dimension-3);
}
</style>
