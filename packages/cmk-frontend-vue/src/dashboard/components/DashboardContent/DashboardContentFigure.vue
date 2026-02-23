<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type Ref, computed, onBeforeUnmount, onMounted, ref, useTemplateRef, watch } from 'vue'

import CmkIcon from '@/components/CmkIcon'

import DashboardContentContainer from '@/dashboard/components/DashboardContent/DashboardContentContainer.vue'
import { useInjectCmkToken } from '@/dashboard/composables/useCmkToken'
import { useSuppressEventOnPublicDashboard } from '@/dashboard/composables/useIsPublicDashboard'
import type { FilterHTTPVars } from '@/dashboard/types/widget.ts'

import { FigureBase } from './cmk_figures.ts'
import type { ContentProps } from './types.ts'

const props = defineProps<ContentProps>()
const cmkToken = useInjectCmkToken()
const suppressEventOnPublicDashboard = useSuppressEventOnPublicDashboard()
const dataEndpointUrl: Ref<string> = computed(() => {
  return cmkToken ? 'widget_figure_token_auth.py' : 'widget_figure.py'
})

const wrapperDiv = useTemplateRef<HTMLDivElement>('wrapperDiv')
const figureDiv = useTemplateRef<HTMLDivElement>('figureDiv')
const figureId = computed(() => `db-content-figure-${props.widget_id}`)

const currentDimensions = ref({ width: 0, height: 0 })
const isLoading = ref(true)

let figure: FigureBase | null = null
let mutationObserver: MutationObserver | null = null

watch(
  () => wrapperDiv.value,
  (newValue, _oldValue, onCleanup) => {
    if (!newValue) {
      return
    }
    currentDimensions.value = {
      width: newValue?.clientWidth || 0,
      height: newValue?.clientHeight || 0
    }
    let resizeTimeout: number | null = null
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect

        if (resizeTimeout) {
          clearTimeout(resizeTimeout)
        }

        resizeTimeout = window.setTimeout(() => {
          handleResize(width, height)
        }, 10)
      }
    })
    observer.observe(wrapperDiv.value!)

    onCleanup(() => {
      observer.disconnect()
    })
  },
  { immediate: true }
)

function handleResize(newWidth: number, newHeight: number) {
  if (!figure) {
    return
  }

  const widthChanged = Math.abs(currentDimensions.value.width - newWidth) > 2
  const heightChanged = Math.abs(currentDimensions.value.height - newHeight) > 2

  if (widthChanged || heightChanged) {
    currentDimensions.value = { width: newWidth, height: newHeight }

    figure.resize()
    figure.update_gui()
  }
}

const httpVars: Ref<FilterHTTPVars> = computed(() => {
  if (cmkToken !== undefined) {
    return {
      widget_id: props.widget_id,
      'cmk-token': cmkToken
    }
  }
  return {
    content: JSON.stringify(props.content),
    context: JSON.stringify(props.effective_filter_context.filters),
    general_settings: JSON.stringify(props.general_settings),
    single_infos: JSON.stringify(props.effective_filter_context.uses_infos)
  }
})

// Resolve figure type for special cases where figure and content type are not the same
const figureType: Ref<string> = computed(() => {
  // NOTE: this logic must match with the keys generated in DashboardContent componentKey()
  if (props.content.type === 'alert_timeline' || props.content.type === 'notification_timeline') {
    const renderType: string = props.content.render_mode.type
    if (renderType === 'bar_chart') {
      return 'timeseries'
    } else if (renderType === 'simple_number') {
      return 'single_metric'
    }
  }
  return props.content.type
})
const typeMap: Record<string, string> = {
  event_stats: 'eventstats',
  host_stats: 'hoststats',
  service_stats: 'servicestats',
  host_state: 'state_host',
  service_state: 'state_service'
}
const legacyFigureType: Ref<string> = computed(() => {
  const newType: string = figureType.value
  if (newType in typeMap && typeMap[newType]) {
    return typeMap[newType]
  }
  return newType
})

// We need to style SVGs for some figure types to make them responsive
const sizeSvg = computed(() =>
  ['event_stats', 'host_stats', 'service_stats'].includes(figureType.value)
)

const updateInterval = 60

function setupMutationObserver(targetElement: HTMLElement) {
  if (mutationObserver) {
    mutationObserver.disconnect()
  }
  mutationObserver = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      for (const node of mutation.removedNodes) {
        if (node instanceof HTMLElement && node.classList.contains('loading_img')) {
          isLoading.value = false
          return
        }
      }
      for (const node of mutation.addedNodes) {
        if (node instanceof HTMLElement && node.id === 'figure_error') {
          isLoading.value = false
          return
        }
      }
    }
  })
  mutationObserver.observe(targetElement, { childList: true })
}

const initializeFigure = () => {
  if (figureDiv.value) {
    setupMutationObserver(figureDiv.value)
  }

  figure = new FigureBase(
    legacyFigureType.value,
    `#${figureId.value}`,
    dataEndpointUrl.value,
    new URLSearchParams(httpVars.value).toString(),
    props.content,
    updateInterval
  )
}

onMounted(() => {
  initializeFigure()
})

watch(httpVars, (newHttpVars: FilterHTTPVars) => {
  if (figure) {
    isLoading.value = true
    figure.update(dataEndpointUrl.value, new URLSearchParams(newHttpVars).toString(), props.content)
  }
})

onBeforeUnmount(() => {
  figure?.disable()
  mutationObserver?.disconnect()
  mutationObserver = null
})
</script>

<template>
  <DashboardContentContainer
    :effective-title="effectiveTitle"
    :general_settings="general_settings"
    content-overflow="hidden"
  >
    <div class="db-content-figure__loading-container">
      <CmkIcon
        v-if="isLoading"
        name="load-graph"
        size="xlarge"
        class="db-content-figure__loading-icon"
      />
      <div
        ref="wrapperDiv"
        class="db-content-figure__wrapper"
        :class="{ 'db-content-figure__wrapper--loading': isLoading }"
      >
        <div
          :id="figureId"
          ref="figureDiv"
          class="db-content-figure cmk_figure"
          :class="[
            {
              'db-content-figure__size-svg': sizeSvg,
              'db-content-figure__background': !!general_settings.render_background
            },
            legacyFigureType
          ]"
          @click.capture="suppressEventOnPublicDashboard"
          @auxclick.capture="suppressEventOnPublicDashboard"
          @mousedown.capture="suppressEventOnPublicDashboard"
          @keydown.capture="suppressEventOnPublicDashboard"
          @wheel.capture="suppressEventOnPublicDashboard"
        ></div>
      </div>
    </div>
  </DashboardContentContainer>
</template>

<style scoped>
.db-content-figure__loading-container {
  display: flex;
  flex: 1;
  position: relative;
}

.db-content-figure__loading-icon {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 1;
}

.db-content-figure__wrapper {
  display: flex;
  width: 100%;
  height: 100%;
}

.db-content-figure__wrapper--loading {
  visibility: hidden;
}

.db-content-figure {
  color: var(--font-color) !important;
  flex: 1;

  &.db-content-figure__background {
    background-color: var(--db-content-bg-color);
  }
}
</style>
