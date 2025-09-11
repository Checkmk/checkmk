<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import { urlEncodeVars } from '@/lib/urls.ts'

import type { EmbeddedViewContent } from '@/dashboard-wip/types/widget'

import DashboardContentIFrame from './DashboardContentIFrame.vue'
import type { ContentProps } from './types.ts'

const props = defineProps<ContentProps>()

const iframeUrl = computed(() => {
  const content = props.content as EmbeddedViewContent
  const httpVars = {
    dashboard: props.dashboardName,
    widget_id: props.widget_id,
    // @ts-expect-error: this is correct, we just need to update the openapi schema
    embedded_id: content.embedded_id,
    context: props.effective_filter_context.filters
  }
  return `widget_iframe_view.py?${urlEncodeVars(httpVars)}`
})
</script>

<template>
  <DashboardContentIFrame :general-settings="general_settings" :iframe-url="iframeUrl" />
</template>
