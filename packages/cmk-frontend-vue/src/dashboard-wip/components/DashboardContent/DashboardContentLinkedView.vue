<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import type { IFrameContent, LinkedViewContent } from '@/dashboard-wip/types/widget.ts'

import DashboardContentIFrame from './DashboardContentIFrame.vue'
import type { ContentProps } from './types.ts'

const props = defineProps<ContentProps>()

const iFrameProps = computed(() => {
  const content = props.content as LinkedViewContent
  const urlParams = new URLSearchParams({
    dashboard: props.dashboardName,
    widget_id: props.widgetId,
    view_name: content.view_name,
    context: JSON.stringify(props.effectiveFilterContext.filters)
  }).toString()
  const iFrameContent: IFrameContent = {
    type: 'url',
    url: `widget_iframe_view.py?${urlParams}`
  }
  return {
    ...props,
    content: iFrameContent
  }
})
</script>

<template>
  <DashboardContentIFrame v-bind="iFrameProps" />
</template>
