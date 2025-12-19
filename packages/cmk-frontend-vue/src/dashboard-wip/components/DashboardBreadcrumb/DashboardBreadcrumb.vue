<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import type { SelectedDashboard } from '@/dashboard-wip/components/DashboardMenuHeader/types'
import type { DashboardKey } from '@/dashboard-wip/types/dashboard'
import type { BreadcrumbItem } from '@/dashboard-wip/types/page'
import { urlHandler } from '@/dashboard-wip/utils'

interface Props {
  selectedDashboard: SelectedDashboard | null
  selectedDashboardBreadcrumb: BreadcrumbItem[] | null
  initialBreadcrumb: BreadcrumbItem[]
}

const props = defineProps<Props>()
const activeBreadcrumb = computed<BreadcrumbItem[]>(() => {
  if (props.selectedDashboardBreadcrumb) {
    const key: DashboardKey = {
      name: props.selectedDashboard?.name ?? '',
      owner: props.selectedDashboard?.owner ?? ''
    }
    const link = urlHandler.getDashboardUrl(key, {})
    return [
      ...props.selectedDashboardBreadcrumb,
      {
        title: props.selectedDashboard?.title ?? '...',
        link: link.toString()
      }
    ]
  }
  return props.initialBreadcrumb
})
</script>

<template>
  <div class="db-breadcrumb--container">
    <div
      v-for="(item, index) in activeBreadcrumb"
      :key="item.link || index"
      :class="`db-breadcrumb--item${index === activeBreadcrumb.length - 1 ? '-final' : ''}`"
    >
      <a v-if="item.link" :href="item.link" class="db-breadcrumb--interactive-item">
        {{ item.title }}
      </a>
      <span v-else class="db-breadcrumb--static-item">
        {{ item.title }}
      </span>
    </div>
  </div>
</template>

<style scoped>
.db-breadcrumb--container {
  white-space: nowrap;
  font-size: var(--font-size-normal);
  padding: var(--dimension-4) var(--dimension-4) 0;
}

.db-breadcrumb--static-item {
  color: var(--font-color-breadcrumb-inactive);
  text-decoration: none;
}

.db-breadcrumb--interactive-item {
  color: var(--font-color-breadcrumb-interactive);
  text-decoration: underline;
}

.db-breadcrumb--interactive-item:hover {
  color: var(--font-color-breadcrumb-hover);
}

.db-breadcrumb--item,
.db-breadcrumb--item-final {
  display: inline-block;
}

.db-breadcrumb--item::after {
  color: var(--font-color-breadcrumb-inactive);
  content: '>';
  cursor: default;
  display: inline-block;
  padding: 0 var(--spacing-half);
  text-decoration: none;
}

.db-breadcrumb--item-final::after {
  content: '';
}
</style>
