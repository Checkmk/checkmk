<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type Ref, computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import useTimer from '@/lib/useTimer.ts'

import CmkIcon from '@/components/CmkIcon'

import { useInjectCmkToken } from '@/dashboard/composables/useCmkToken'
import { useDebounceFn } from '@/dashboard/composables/useDebounce'
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
const isLoading = ref<boolean>(true)

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

const handleRefreshData = (_handlerData: null, body: string) => {
  if (contentDiv.value) {
    contentDiv.value.innerHTML = body
    cmkToolkit.utils.execute_javascript_by_object(contentDiv.value)
  }
  isLoading.value = false
}

const updateGraph = () => {
  cmkToolkit.ajax.call_ajax(dataEndpointUrl.value, {
    post_data: new URLSearchParams({ ...httpVars.value, ...sizeVars.value }).toString(),
    method: 'POST',
    response_handler: handleRefreshData
  })
}
const debouncedUpdateGraph = useDebounceFn(updateGraph, 300)

watch([httpVars, sizeVars], () => {
  debouncedUpdateGraph()
})

const resizeObserver = new ResizeObserver((entries) => {
  // only one element needs to be observed
  const entry = entries[0]!

  const size = entry.contentBoxSize![0]!
  sizeVars.value = {
    width: String(size.inlineSize),
    height: String(size.blockSize)
  }
})

const timer = useTimer(updateGraph, 60_000)

onMounted(() => {
  timer.start()
  resizeObserver.observe(parentDiv.value!)
})

onBeforeUnmount(() => {
  timer.stop()
  resizeObserver.disconnect()
  isLoading.value = false
})
</script>

<template>
  <DashboardContentContainer
    :effective-title="effectiveTitle"
    :general_settings="general_settings"
    content-overflow="hidden"
  >
    <CmkIcon
      v-show="isLoading"
      name="load-graph"
      size="xlarge"
      class="db-content-graph__loading-icon"
    />
    <div
      v-show="!isLoading"
      :id="`db-content-graph-${widget_id}`"
      ref="contentDiv"
      class="db-content-graph"
    />
  </DashboardContentContainer>
</template>

<style scoped>
.db-content-graph__loading-icon {
  margin: auto;
}
</style>
