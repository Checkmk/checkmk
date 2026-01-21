<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import type { IFrameContent, SidebarElementContent } from '@/dashboard/types/widget.ts'

import DashboardContentIFrame from './DashboardContentIFrame.vue'
import type { ContentProps } from './types.ts'

const props = defineProps<ContentProps<SidebarElementContent>>()

const iFrameProps = computed(() => {
  const urlParams = new URLSearchParams({
    name: props.content.name
  }).toString()
  const iFrameContent: IFrameContent = {
    type: 'url',
    url: `widget_iframe_sidebar.py?${urlParams}`
  }
  return {
    ...props,
    content: iFrameContent
  } as ContentProps<IFrameContent>
})
</script>

<template>
  <DashboardContentIFrame v-bind="iFrameProps" />
</template>
