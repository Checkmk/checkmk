<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import {
  type Ref,
  computed,
  defineEmits,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  useTemplateRef,
  watch
} from 'vue'

import { FigureBase } from './cmk_figures.ts'
import type { ContentProps, FilterHTTPVars } from './types.ts'

const props = defineProps<ContentProps>()
const emit = defineEmits(['vue:mounted', 'vue:updated'])

const contentDiv = useTemplateRef<HTMLDivElement>('contentDiv')
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
  return {
    name: props.dashboardName,
    owner: props.dashboardOwner,
    widget_id: props.widget_id,
    content: JSON.stringify(props.content),
    context: JSON.stringify(props.effective_filter_context.filters),
    single_infos: JSON.stringify(props.effective_filter_context.restricted_to_single)
  }
})

// Resolve figure type for special cases where figure and content type are not the same
const figureType = computed(() => {
  if (['alert_timeline', 'notification_timeline'].includes(props.content.type)) {
    if (!('render_mode' in props.content)) {
      throw new Error(
        `No render mode found for DashboardContentFigure of type '${props.content.type}'`
      )
    }
    const renderType: string = props.content.render_mode.type
    if (renderType === 'bar_chart') {
      return 'timeseries'
    } else if (renderType === 'simple_number') {
      return 'single_metric'
    }
  }
  return props.content.type
})

// We need to style SVGs for some figure types to make them responsive
const sizeSvg = computed(() => ['host_stats', 'service_stats'].includes(figureType.value))

const ajaxPage: string = 'widget_figure.py'
const updateInterval = 60

const initializeFigure = () => {
  figure = new FigureBase(
    figureType.value,
    `#db-content-figure-${props.widget_id}`,
    ajaxPage,
    new URLSearchParams(httpVars.value).toString(),
    props.content,
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
    figure.update(ajaxPage, new URLSearchParams(newHttpVars).toString(), props.content)
  }
})

onBeforeUnmount(() => {
  figure?.disable()
})
</script>

<template>
  <div ref="wrapperDiv" class="db-content-figure__wrapper">
    <div
      :id="`db-content-figure-${widget_id}`"
      ref="contentDiv"
      class="db-content-figure"
      :class="{
        'db-content-figure__size-svg': sizeSvg,
        'db-content-figure__background': !!general_settings.render_background
      }"
    ></div>
  </div>
</template>

<style scoped>
.db-content-figure__wrapper {
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
