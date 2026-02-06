<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import MissingFiltersMsg from '@/dashboard/components/DashboardFilterSettings/MissingFiltersMsg.vue'

import DashboardContent from './DashboardContent/DashboardContent.vue'
import { isContentWithScrollablePreview } from './DashboardContent/contentWithScrollablePreview.ts'
import type { ContentProps } from './DashboardContent/types.ts'

const props = defineProps<ContentProps>()
const effectiveContentProps = computed(() => {
  return isContentWithScrollablePreview(props.content.type) ? { ...props, isPreview: true } : props
})
</script>

<template>
  <div class="db-preview-content">
    <MissingFiltersMsg
      render-context="configurationPreview"
      :effective-filter-context="effective_filter_context"
    >
      <div
        class="db-preview-content__inner-wrapper"
        :class="{
          'db-preview-content__click-shield': !isContentWithScrollablePreview(content.type)
        }"
      >
        <DashboardContent v-bind="effectiveContentProps" />
      </div>
    </MissingFiltersMsg>
  </div>
</template>

<style scoped>
.db-preview-content {
  --db-preview-content-height: calc(var(--dimension-8) * 10);
  --db-preview-content-padding: var(--dimension-3);

  display: flex;
  flex-direction: column;
  position: relative;
  height: var(--db-preview-content-height);
  margin: 0;
  padding: var(--db-preview-content-padding);
  box-sizing: border-box;
}

.db-preview-content__inner-wrapper {
  /* "parent node" is used for figure height calculation */
  height: calc(var(--db-preview-content-height) - calc(2 * var(--db-preview-content-padding)));
}

.db-preview-content__click-shield {
  pointer-events: none;
}
</style>
