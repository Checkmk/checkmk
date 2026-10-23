<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkBreadcrumb, { type BreadcrumbItem } from 'cmk-ui-library/components/CmkBreadcrumb'
import { computed } from 'vue'

import type { SelectedDashboard } from '@/dashboard/components/DashboardMenuHeader/types'
import type { DashboardKey } from '@/dashboard/types/dashboard'
import type { FilterHTTPVars } from '@/dashboard/types/widget'
import { urlHandler } from '@/dashboard/utils'

interface Props {
  selectedDashboard: SelectedDashboard | null
  selectedDashboardBreadcrumb: BreadcrumbItem[] | null
  initialBreadcrumb: BreadcrumbItem[]
  runtimeFilters: FilterHTTPVars
}

const props = defineProps<Props>()
const activeBreadcrumb = computed<BreadcrumbItem[]>(() => {
  if (props.selectedDashboardBreadcrumb) {
    const key: DashboardKey = {
      name: props.selectedDashboard?.name ?? '',
      owner: props.selectedDashboard?.owner ?? ''
    }
    const link = urlHandler.getDashboardUrl(key, props.runtimeFilters)
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
  <CmkBreadcrumb :items="activeBreadcrumb" />
</template>
