<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkSkeleton from '@/components/CmkSkeleton.vue'

const DETAIL_ROWS = 4
const SITE_ROWS = 3
const CHIP_ROWS = 3
const CHIPS_PER_ROW = 5
</script>

<template>
  <div class="monitoring-host-overview-skeleton" aria-hidden="true">
    <div class="monitoring-host-overview-skeleton__link">
      <CmkSkeleton type="text" width="120px" />
    </div>

    <div class="monitoring-host-overview-skeleton__grid">
      <template v-for="row in DETAIL_ROWS" :key="`detail-${row}`">
        <CmkSkeleton type="text" width="90px" />
        <CmkSkeleton type="text" width="60%" />
      </template>
    </div>

    <div class="monitoring-host-overview-skeleton__grid">
      <template v-for="row in SITE_ROWS" :key="`site-${row}`">
        <CmkSkeleton type="text" width="90px" />
        <CmkSkeleton type="text" width="50%" />
      </template>
    </div>

    <div class="monitoring-host-overview-skeleton__grid">
      <template v-for="row in CHIP_ROWS" :key="`chips-${row}`">
        <CmkSkeleton type="text" width="90px" />
        <div class="monitoring-host-overview-skeleton__chips">
          <CmkSkeleton v-for="chip in CHIPS_PER_ROW" :key="chip" type="box" width="72px" />
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.monitoring-host-overview-skeleton {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-double);
}

.monitoring-host-overview-skeleton__link {
  display: flex;
  justify-content: flex-end;
}

.monitoring-host-overview-skeleton__grid {
  display: grid;
  grid-template-columns: minmax(120px, max-content) 1fr;
  gap: var(--dimension-4) var(--spacing);
  align-items: center;
}

.monitoring-host-overview-skeleton__chips {
  display: flex;
  flex-flow: row wrap;
  gap: var(--dimension-3);
}
</style>
