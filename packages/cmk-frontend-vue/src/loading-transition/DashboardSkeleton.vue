<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkSkeleton from '@/components/CmkSkeleton.vue'

// Generate panels with varying row and column spans
const panels = Array.from({ length: 40 }, (_, i) => {
  const highPanel = Math.random() > 0.5
  return {
    id: i,
    colSpan: Math.floor(1 + Math.random() * (highPanel ? 2 : 3)),
    rowSpan: highPanel ? 2 : 1
  }
})

const getRandomWidth = (min: number, max: number): string => {
  return `${min + Math.random() * (max - min)}px`
}
</script>

<template>
  <div class="loading-transition-dashboard-skeleton">
    <div
      v-for="panel in panels"
      :key="panel.id"
      class="loading-transition-dashboard-skeleton__panel"
      :style="{
        gridColumn: `span ${panel.colSpan}`,
        gridRow: `span ${panel.rowSpan}`
      }"
    >
      <div class="loading-transition-dashboard-skeleton__panel-header">
        <CmkSkeleton :type="'text'" :width="getRandomWidth(50, 170)" />
      </div>
      <div class="loading-transition-dashboard-skeleton__panel-content">
        <CmkSkeleton :type="'box'" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.loading-transition-dashboard-skeleton {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  grid-auto-rows: 175px;
  grid-auto-flow: dense;
  gap: var(--spacing);
  pointer-events: none;

  .loading-transition-dashboard-skeleton__panel {
    display: flex;
    flex-direction: column;
    background: var(--ux-theme-2);

    .loading-transition-dashboard-skeleton__panel-header {
      display: flex;
      width: 100%;
      height: 22px;
      justify-content: center;
      align-items: center;
      background: var(--ux-theme-3);
    }

    .loading-transition-dashboard-skeleton__panel-content {
      flex-grow: 1;
      padding: var(--spacing);
    }
  }
}
</style>
