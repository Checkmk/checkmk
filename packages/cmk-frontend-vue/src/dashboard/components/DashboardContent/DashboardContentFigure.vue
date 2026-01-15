<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import {
  type Ref,
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  useTemplateRef,
  watch
} from 'vue'

import DashboardContentContainer from '@/dashboard/components/DashboardContent/DashboardContentContainer.vue'
import { useInjectCmkToken } from '@/dashboard/composables/useCmkToken'
import type { FilterHTTPVars } from '@/dashboard/types/widget.ts'

import { type DashletSpec, FigureBase } from './cmk_figures.ts'
import type { ContentProps } from './types.ts'

const props = defineProps<ContentProps>()
const cmkToken = useInjectCmkToken()
const dataEndpointUrl: Ref<string> = computed(() => {
  return cmkToken ? 'widget_figure_token_auth.py' : 'widget_figure.py'
})
const emit = defineEmits(['vue:mounted', 'vue:updated'])

const wrapperDiv = useTemplateRef<HTMLDivElement>('wrapperDiv')

const currentDimensions = ref({ width: 0, height: 0 })

let figure: FigureBase | null = null

watch(
  wrapperDiv,
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

// This is needed by the old cmk_figures.ts code, hence the old naming "dashlet"
const dashletSpec: Ref<DashletSpec> = computed(() => {
  return {
    ...props.content,
    show_title: props.general_settings.title?.render_mode === 'with_background'
  }
})
const initializeFigure = () => {
  figure = new FigureBase(
    legacyFigureType.value,
    `#db-content-figure-${props.widget_id}`,
    dataEndpointUrl.value,
    new URLSearchParams(httpVars.value).toString(),
    dashletSpec.value,
    updateInterval
  )
}

onMounted(async () => {
  initializeFigure()
  await nextTick()
  emit('vue:mounted')
})

watch(httpVars, (newHttpVars) => {
  if (figure) {
    figure.update(
      dataEndpointUrl.value,
      new URLSearchParams(newHttpVars).toString(),
      dashletSpec.value
    )
  }
})

onBeforeUnmount(() => {
  figure?.disable()
})
</script>

<template>
  <DashboardContentContainer
    :effective-title="effectiveTitle"
    :general_settings="general_settings"
    content-overflow="hidden"
  >
    <div ref="wrapperDiv" class="db-content-figure__wrapper">
      <div
        :id="`db-content-figure-${widget_id}`"
        class="db-content-figure cmk_figure"
        :class="[
          {
            'db-content-figure__size-svg': sizeSvg,
            'db-content-figure__background': !!general_settings.render_background
          },
          legacyFigureType
        ]"
      ></div>
    </div>
  </DashboardContentContainer>
</template>

<style scoped>
.db-content-figure__wrapper {
  display: flex;
  width: 100%;
  height: 100%;
}

.db-content-figure {
  color: var(--font-color) !important;
  flex: 1;

  &.db-content-figure__background {
    background-color: var(--db-content-bg-color);
  }
}
</style>

<style>
.db-content-figure__size-svg > svg {
  width: 100%;
  height: 100%;
}
</style>
