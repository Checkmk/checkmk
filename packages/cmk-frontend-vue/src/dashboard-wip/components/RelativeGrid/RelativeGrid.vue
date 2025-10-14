<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref } from 'vue'

import type { ContentPropsRecord } from '@/dashboard-wip/components/DashboardContent/types'
import RelativeWidgetFrame from '@/dashboard-wip/components/RelativeGrid/RelativeWidgetFrame.vue'
import {
  type ResizeDirection,
  createResizeHelper
} from '@/dashboard-wip/components/RelativeGrid/helpers/resizeHelper.ts'
import type { ContentRelativeGrid, DashboardConstants } from '@/dashboard-wip/types/dashboard.ts'
import type { WidgetLayout } from '@/dashboard-wip/types/widget'

import { useRelativeGridLayout } from './composables/useRelativeGridLayout'
import { createDragHelper } from './helpers/dragHelper.ts'
import { type ANCHOR_POSITION, type Dimensions, type Position, WIDGET_MIN_SIZE } from './types.ts'
import { calculateDashboardDimensions } from './utils.ts'

/*
This component provides the relative (legacy) grid layout for dashboard widgets.

Each content saves its own internal layout information consisting of size (width, height) and position (left, top).
Those values also implicitly contain information about the anchor position (top-left, top-right, bottom-left, bottom-right)
as well the sizing mode for width and height.

The layout information is in an internal specific format (in some way relative) hence the RelativeGrid name.
The layout information is converted to absolute pixel values for rendering and interaction.

All widget layout modification (dragging and resizing) is handled in the absolute pixel space and then converted back
to the internal layout representation for storage.

Each pixel movement leads to a state internal layout update of the single widget but subsequently triggers the
recalculation of the ENTIRE absolute space (all widgets). The entire internal (legacy) layout was based upon this idea
and hence not changed during the migration. Further insights about this idea can be found in the (from legacy) ported
utils.calculateDashlets function.
 */

interface RelativeGridDashboardProps {
  contentProps: ContentPropsRecord
  dashboardConstants: DashboardConstants
  isEditing: boolean
}

const props = defineProps<RelativeGridDashboardProps>()

const content = defineModel<ContentRelativeGrid>('content', {
  required: true
})

const emit = defineEmits<{
  'widget:edit': [widgetId: string]
  'widget:delete': [widgetId: string]
  'widget:clone': [widgetId: string, newWidgetLayout: WidgetLayout]
}>()

const dashboard = ref<HTMLElement | null>(null)

const {
  dashboardState,
  getAbsoluteLayout,
  getLayoutZIndex,
  getAnchorPosition,
  getDimensionModes,
  updateDashboardLayout,
  updateLayoutPosition,
  updateLayoutDimensions,
  toggleSizing,
  selectAnchor,
  bringToFront
} = useRelativeGridLayout(content, WIDGET_MIN_SIZE)

const { handleDrag } = createDragHelper(
  dashboardState.position,
  WIDGET_MIN_SIZE,
  updateLayoutPosition
)

const { handleResize } = createResizeHelper(
  WIDGET_MIN_SIZE,
  (widgetId: string, newPosition: Position, newDimensions: Dimensions) => {
    updateLayoutPosition(widgetId, newPosition)
    updateLayoutDimensions(widgetId, newDimensions)
  }
)

const setDashboardLayout = () => {
  if (!dashboard.value) {
    return
  }

  // Moved this from calculateDashboard function
  const dimensions = calculateDashboardDimensions(dashboard.value)

  // Legacy Note: For Firefox we need to substitute the container's padding-right from the dashboard width to
  // prevent unnecessary scroll bars
  // Migrated Note: we set this value even bigger now. The dashboard's old code was adjusted to the old page layout
  // and hence had an 'interesting' behaviour when widgets had their anchors on the right side. This handling was
  // already broken there. We maintain the same behaviour since users potentially have dashboard relying on this
  const dashboardDimensions = {
    width: dimensions.width,
    height: dimensions.height - 30
  }
  const dashboardRect = dashboard.value.getBoundingClientRect()
  const dashboardPosition = {
    x: dashboardRect.left,
    y: dashboardRect.top
  }

  updateDashboardLayout(dashboardDimensions, dashboardPosition)

  dashboard.value.style.width = `${dashboardDimensions.width}px`
  dashboard.value.style.height = `${dashboardDimensions.height}px`
}

onMounted(async () => {
  // Calculate dashboard dimensions and layout
  await nextTick()

  setDashboardLayout()
  window.addEventListener('resize', setDashboardLayout)
})

onUnmounted(() => {
  window.removeEventListener('resize', setDashboardLayout)
})

function handleDragForWidget(widgetId: string) {
  return (event: PointerEvent) => {
    bringToFront(widgetId)
    handleDrag(
      event,
      widgetId,
      getAnchorPosition(widgetId),
      getDimensionModes(widgetId),
      getAbsoluteLayout(widgetId)!
    )
    event.stopPropagation()
  }
}

function handleResizeForWidget(widgetId: string) {
  return (event: PointerEvent, direction: ResizeDirection) => {
    bringToFront(widgetId)
    handleResize(
      event,
      widgetId,
      direction,
      getAnchorPosition(widgetId),
      getAbsoluteLayout(widgetId)!,
      dashboardState.dimensions
    )
    event.stopPropagation()
  }
}

const cloneRelativeGridWidget = (oldWidgetId: string) => {
  const widgetType = props.contentProps[oldWidgetId]!.content.type
  const layoutConstant = props.dashboardConstants.widgets[widgetType]!.layout.relative

  emit('widget:clone', oldWidgetId, {
    type: 'relative_grid',
    position: layoutConstant.initial_position,
    size: layoutConstant.initial_size
  })
}
</script>

<template>
  <div class="simplebar-content">
    <div id="dashboard" ref="dashboard" class="dashboard dashboard_main">
      <div v-for="spec of contentProps" :key="spec.widget_id">
        <RelativeWidgetFrame
          :debug="false"
          :is-editing="isEditing"
          :content-props="spec"
          :is-resizable="
            dashboardConstants.widgets[spec.content.type]!.layout.relative.is_resizable || false
          "
          :dimensions="
            getAbsoluteLayout(spec.widget_id)?.frame.dimensions || { width: 100, height: 100 }
          "
          :z-index="getLayoutZIndex(spec.widget_id) || 1"
          :position="getAbsoluteLayout(spec.widget_id)?.frame.position || { left: 0, top: 0 }"
          :handle-drag="handleDragForWidget(spec.widget_id)"
          :handle-resize="handleResizeForWidget(spec.widget_id)"
          :anchor-position="getAnchorPosition(spec.widget_id)"
          :dimension-modes="getDimensionModes(spec.widget_id)"
          @toggle:sizing="
            (dimension: 'width' | 'height') => toggleSizing(spec.widget_id, dimension)
          "
          @update:anchor-position="
            (anchorPosition: ANCHOR_POSITION) => selectAnchor(spec.widget_id, anchorPosition)
          "
          @click:edit="$emit('widget:edit', spec.widget_id)"
          @click:delete="$emit('widget:delete', spec.widget_id)"
          @click:clone="cloneRelativeGridWidget(spec.widget_id)"
        />
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.dashboard {
  position: relative;
  width: 100%;
  height: 90vh;
}
</style>
