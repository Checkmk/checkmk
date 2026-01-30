<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import { useInjectCmkToken } from '@/dashboard/composables/useCmkToken'
import type { IFrameContent, LinkedViewContent } from '@/dashboard/types/widget.ts'

import DashboardContentIFrame from './DashboardContentIFrame.vue'
import type { ContentProps } from './types.ts'

const props = defineProps<ContentProps>()
const cmkToken = useInjectCmkToken()

const iFrameUrl = computed(() => {
  if (cmkToken !== undefined) {
    const urlParams = new URLSearchParams({
      widget_id: props.widget_id,
      'cmk-token': cmkToken
    }).toString()
    return `widget_iframe_view_token_auth.py?${urlParams}`
  }

  const content = props.content as LinkedViewContent
  const urlParams = new URLSearchParams({
    dashboard_name: props.dashboardKey.name,
    dashboard_owner: props.dashboardKey.owner,
    widget_id: props.widget_id,
    view_name: content.view_name,
    context: JSON.stringify(props.effective_filter_context.filters)
  }).toString()
  return `widget_iframe_view.py?${urlParams}`
})

const iFrameProps = computed(() => {
  const iFrameContent: IFrameContent = {
    type: 'url',
    url: iFrameUrl.value
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
