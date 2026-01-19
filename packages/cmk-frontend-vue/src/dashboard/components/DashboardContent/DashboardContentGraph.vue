<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type Ref, computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import useTimer from '@/lib/useTimer.ts'

import { useInjectCmkToken } from '@/dashboard/composables/useCmkToken'
import type { FilterHTTPVars } from '@/dashboard/types/widget.ts'

import DashboardContentContainer from './DashboardContentContainer.vue'
import type { ContentProps } from './types.ts'

const props = defineProps<ContentProps>()
const cmkToken = useInjectCmkToken()
const dataEndpointUrl: Ref<string> = computed(() => {
  return cmkToken ? 'widget_graph_token_auth.py' : 'widget_graph.py'
})

// @ts-expect-error comes from different javascript file
const cmkToolkit = window['cmk']

const contentDiv = ref<HTMLDivElement | null>(null)
const parentDiv = computed(() => contentDiv.value?.parentElement || null)

const httpVars: Ref<FilterHTTPVars> = computed(() => {
  if (cmkToken !== undefined) {
    return {
      widget_id: props.widget_id,
      'cmk-token': cmkToken
    }
  }
  return {
    widget_id: props.widget_id,
    content: JSON.stringify(props.content),
    context: JSON.stringify(props.effective_filter_context.filters),
    single_infos: JSON.stringify(props.effective_filter_context.uses_infos)
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
  cmkToolkit.ajax.call_ajax(dataEndpointUrl.value, {
    post_data: new URLSearchParams({ ...httpVars.value, ...sizeVars.value }).toString(),
    method: 'POST',
    response_handler: handleRefreshData,
    handler_data: props.widget_id
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
  <DashboardContentContainer
    :effective-title="effectiveTitle"
    :general_settings="general_settings"
    content-overflow="hidden"
  >
    <div :id="`db-content-graph-${widget_id}`" ref="contentDiv" class="db-content-graph" />
  </DashboardContentContainer>
</template>
