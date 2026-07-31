<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import { LOADING_AFFORDANCE_DELAY_MS, useDelayedFlag } from 'cmk-ui-library/lib/useDelayedFlag'
import { useResizeObserver } from 'cmk-ui-library/lib/useResizeObserver'
import { type Ref, computed, onBeforeUnmount, onMounted, ref, useTemplateRef, watch } from 'vue'

import DashboardContentContainer from '@/dashboard/components/DashboardContent/DashboardContentContainer.vue'
import { useInjectCmkToken } from '@/dashboard/composables/useCmkToken'
import { useSuppressEventOnPublicDashboard } from '@/dashboard/composables/useIsPublicDashboard'
import type { FilterHTTPVars } from '@/dashboard/types/widget.ts'
import { GraphNotice, useGraphNotice } from '@/graphing'

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
// null until a fetch fails; then the legacy node's text, which the notice shows as the detail
// under its headline. Empty when that node carried none.
const error = ref<string | null>(null)

const notice = useGraphNotice({
  error: () => error.value,
  isLoading: () => isLoading.value,
  // This transport reports a failure and nothing else: it carries no channel for the diagnostics a
  // 200 from the graph endpoints would bring.
  partialErrors: () => [],
  warnings: () => []
})

// Only the icon waits out the delay; the wrapper below stays hidden on the raw flag throughout. The
// icon also stands down for a failure, which the notice states instead.
const showLoadingIcon = useDelayedFlag(
  () => isLoading.value && error.value === null,
  LOADING_AFFORDANCE_DELAY_MS
)

let figure: FigureBase | null = null
let mutationObserver: MutationObserver | null = null

let resizeTimeout: number | null = null
const { observe } = useResizeObserver((entries) => {
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
observe(wrapperDiv)

// Seed the baseline dimensions when the wrapper first mounts, so the observer's initial delivery
// (same size) doesn't count as a change.
watch(
  () => wrapperDiv.value,
  (newValue) => {
    if (newValue) {
      currentDimensions.value = {
        width: newValue.clientWidth || 0,
        height: newValue.clientHeight || 0
      }
    }
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
          // Left hidden behind the wrapper's modifier rather than removed here; only `onRetry`
          // removes it, so that a repeat failure stays observable.
          error.value = node.textContent?.trim() ?? ''
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
  // FigureBase calls its post-render hooks only from process_data, so reaching here means success.
  figure.instance.subscribe_post_render_hook(() => {
    isLoading.value = false
    error.value = null
  })
}

const onRetry = () => {
  if (!figure) {
    return
  }
  // FigureBase writes #figure_error through a d3 join and clears it only on a successful render,
  // so without removing it here a second failure in a row rewrites the text of a node already
  // there, mutating nothing the observer watches, and the widget loads forever.
  figure.instance.clear_error_info()
  isLoading.value = true
  figure.update(
    dataEndpointUrl.value,
    new URLSearchParams(httpVars.value).toString(),
    props.content
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
        v-if="showLoadingIcon"
        name="load-graph"
        size="xlarge"
        class="db-content-figure__loading-icon"
      />
      <GraphNotice
        v-if="notice"
        v-bind="notice"
        class="db-content-figure__notice"
        @retry="onRetry"
      />
      <div
        ref="wrapperDiv"
        class="db-content-figure__wrapper"
        :class="{ 'db-content-figure__wrapper--loading': isLoading || error !== null }"
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
  min-height: 0;
}

.db-content-figure__loading-icon,
.db-content-figure__notice {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 1;
}

.db-content-figure__notice {
  max-width: 100%;
}

.db-content-figure__wrapper {
  display: flex;
  flex: 1;
  min-height: 0;
  width: 100%;
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
