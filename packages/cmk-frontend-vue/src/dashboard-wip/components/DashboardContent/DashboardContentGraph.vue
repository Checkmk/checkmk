<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type Ref, computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import useTimer from '@/lib/useTimer.ts'

import DashboardContentContainer from './DashboardContentContainer.vue'
import type { ContentProps, FilterHTTPVars } from './types.ts'

const props = defineProps<ContentProps>()

// @ts-expect-error comes from different javascript file
const cmkToolkit = window['cmk']

const contentDiv = ref<HTMLDivElement | null>(null)
const parentDiv = computed(() => contentDiv.value?.parentElement || null)

const httpVars: Ref<FilterHTTPVars> = computed(() => {
  return {
    widget_id: props.widgetId,
    content: JSON.stringify(props.content),
    context: JSON.stringify(props.effectiveFilterContext.filters),
    single_infos: JSON.stringify(props.effectiveFilterContext.uses_infos)
  }
})
const sizeVars: Ref<FilterHTTPVars> = ref({
  width: '0',
  height: '0'
})

const handleRefreshData = (widgetId: string, body: string) => {
  const container = document.getElementById(`db-content-graph-${widgetId}`)
  if (container) {
    container.innerHTML = body
    cmkToolkit.utils.execute_javascript_by_object(container)
  }
}

const updateGraph = () => {
  cmkToolkit.ajax.call_ajax('widget_graph.py', {
    post_data: new URLSearchParams({ ...httpVars.value, ...sizeVars.value }).toString(),
    method: 'POST',
    response_handler: handleRefreshData,
    handler_data: props.widgetId
  })
}

watch([httpVars, sizeVars], () => {
  updateGraph()
})

const resizeObserver = new ResizeObserver((entries) => {
  // only one element needs to be observed
  const entry = entries[0]!

  const size = entry.contentBoxSize![0]!
  sizeVars.value.width = String(size.inlineSize)
  sizeVars.value.height = String(size.blockSize)

  updateGraph()
})

const timer = useTimer(updateGraph, 60_000)

onMounted(() => {
  timer.start()
  resizeObserver.observe(parentDiv.value!)
})

onBeforeUnmount(() => {
  timer.stop()
  resizeObserver.disconnect()
})
</script>

<template>
  <DashboardContentContainer v-bind="generalSettings" content-overflow="hidden">
    <div :id="`db-content-graph-${widgetId}`" ref="contentDiv" class="db-content-graph" />
  </DashboardContentContainer>
</template>
