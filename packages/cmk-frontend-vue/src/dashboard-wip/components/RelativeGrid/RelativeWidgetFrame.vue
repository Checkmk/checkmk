<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import DashboardContent from '@/dashboard-wip/components/DashboardContent/DashboardContent.vue'
import type { ContentProps } from '@/dashboard-wip/components/DashboardContent/types'

interface DashboardFrameProps {
  contentProps: ContentProps
  dimensions: { width: number; height: number }
  position: { left: number; top: number }
}

const props = defineProps<DashboardFrameProps>()

const containerStyle = computed(() => {
  return {
    top: `${props.position?.top || 0}px`,
    left: `${props.position?.left || 0}px`,
    width: `${props.dimensions?.width || 100}px`,
    height: `${props.dimensions?.height || 100}px`
  }
})
</script>

<template>
  <div
    :id="`db-relative-grid-frame-${contentProps.widget_id}`"
    class="db-relative-grid-frame"
    :style="{ ...containerStyle }"
  >
    <DashboardContent v-bind="contentProps" />
  </div>
</template>

<style scoped>
.db-relative-grid-frame {
  position: absolute;
  display: flex;
  flex-direction: column;
  margin: 0;
  padding: var(--dimension-3);
  box-sizing: border-box;
}
</style>
