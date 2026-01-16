<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { GridLayout } from 'grid-layout-plus'
import { computed, ref, watch } from 'vue'

import usei18n from '@/lib/i18n'

import CmkDialog from '@/components/CmkDialog.vue'
import { useCmkErrorBoundary } from '@/components/CmkErrorBoundary'

import type { ContentPropsRecord } from '@/dashboard/components/DashboardContent/types'
import { useInjectMissingRuntimeFiltersAction } from '@/dashboard/composables/useProvideMissingRuntimeFiltersAction.ts'
import type {
  ContentResponsiveGrid,
  DashboardConstants,
  DashboardKey
} from '@/dashboard/types/dashboard'
import type { ResponsiveGridWidgetLayouts } from '@/dashboard/types/widget'

import ResponsiveGridWidget from './ResponsiveGridWidget.vue'
import { useInternalBreakpointConfig } from './composables/useInternalBreakpointConfig'
import { useResponsiveGridLayout } from './composables/useResponsiveGridLayout'
import type {
  ResponsiveGridInternalArrangement,
  ResponsiveGridInternalArrangementElement,
  ResponsiveGridInternalBreakpoint
} from './types'

/*
This component provides a responsive grid layout for dashboard widgets.

To do this, it deals with two formats:
 * State / API format (ContentResponsiveGrid type):
   * Input into this component, and output when the layout changes
   * Structure:
     * Multiple named layouts can be defined on the dashboard level
     * We currently only use the `default` layout
     * Layouts can define which breakpoints are enabled for them
     * Every widget has a layout definition per named layout
     * Every widget layout definition has a size/position per breakpoint

 * Internal format (ResponsiveGridConfiguredInternalLayouts type):
   * Computed based on the state format, see `useResponsiveGridLayout` composable
   * Merges the layout definitions from all widgets into a more manageable format
   * Uses the types from `grid-layout-plus`, so that we can directly pass it to the library
   * Structure:
     * Multiple named layouts
     * Every named layout has one or more breakpoints
     * Every breakpoint has an arrangement (array of arrangement elements)
     * An arrangement element has a widget ID, size and position
       * Based on the widget content type and breakpoint, it also has minimum sizes

Layout changes:
 * As mentioned above, we compute the internal format based on the state format
 * We keep a copy of the current arrangement in `currentInternalArrangement`
   * currentInternalArrangement: based on selected layout and current breakpoint within that layout
   * currentInternalArrangement: modified by the library, but should be treated as read-only
 * When the user changes the arrangement (dragging/resizing), we get events from the library
   * onArrangementUpdate: triggered when an element is moved or resized
   * onBreakpointChange: triggered when the screen breakpoint changes, also triggers once initially
 * Updates are done on the state format, via the `useResponsiveGridLayout` composable
   * This triggers recomputation of the internal format (and will likely trigger the events)
     * To avoid infinite loops, we compare the arrangements in JSON format before updates
*/

interface Props {
  dashboardKey: DashboardKey
  responsiveGridBreakpoints: DashboardConstants['responsive_grid_breakpoints']
  contentProps: ContentPropsRecord
  isEditing: boolean
}

const props = defineProps<Props>()
const { _t } = usei18n()

const content = defineModel<ContentResponsiveGrid>('content', {
  required: true
})

defineEmits<{
  'widget:edit': [widgetId: string]
  'widget:delete': [widgetId: string]
  'widget:clone': [widgetId: string, newLayout: ResponsiveGridWidgetLayouts]
}>()

const gridMargin = 10
const internalBreakpointConfig = useInternalBreakpointConfig(props.responsiveGridBreakpoints)
const composable = useResponsiveGridLayout(internalBreakpointConfig, content)

// unique key for the grid layout component to force reloading `responsive-layouts`
const gridKey = computed(
  () =>
    `responsive-grid-${props.dashboardKey.owner}-${props.dashboardKey.name}-${composable.selectedLayoutName.value}`
)

// This is used to filter out unnecessary updates.
// Always use `computeArrangementJSON` to update this, as this ensures that we only compare the
// relevant properties.
// We use '[]' as initial value, which matches the initial value of `currentInternalArrangement`.
// This should be overwritten immediately when the watch on composable.selectedLayout triggers.
const currentStrippedArrangementJSON = ref<string>('[]')

function computeArrangementJSON(layout: ResponsiveGridInternalArrangement) {
  // We cannot just use JSON.stringify here, since the library adds extra keys to the layout items
  // (and those aren't present when computing this from composable.selectedLayout)
  return JSON.stringify(
    layout.map(
      (item) =>
        ({
          i: item.i,
          x: item.x,
          y: item.y,
          w: item.w,
          h: item.h,
          minW: item.minW ?? 1,
          minH: item.minH ?? 1
        }) as ResponsiveGridInternalArrangementElement
    )
  )
}

// Keep track of the current breakpoint, so that we can update the correct (state-format) layout
// when the current (internal) one changes.
// Try to initialize it with any available breakpoint, otherwise fallback to 'lg'
const currentInternalBreakpoint = ref<ResponsiveGridInternalBreakpoint>(
  (Object.keys(composable.selectedLayout.value)[0] as ResponsiveGridInternalBreakpoint) || 'lg'
)

// The current internal arrangement, this is what the library will work with
const currentInternalArrangement = ref<ResponsiveGridInternalArrangement>([])

function onBreakpointChange(
  internalBreakpoint: ResponsiveGridInternalBreakpoint,
  newInternalArrangement: ResponsiveGridInternalArrangement
) {
  // A breakpoint change will always change the arrangement, so we can skip the comparison
  currentInternalBreakpoint.value = internalBreakpoint
  currentStrippedArrangementJSON.value = computeArrangementJSON(newInternalArrangement)
  composable.updateSelectedLayout(internalBreakpoint, newInternalArrangement)
}

function onArrangementUpdate(newInternalArrangement: ResponsiveGridInternalArrangement) {
  // Skip if nothing relevant changed
  const arrangementJSON = computeArrangementJSON(newInternalArrangement)
  if (arrangementJSON === currentStrippedArrangementJSON.value) {
    return
  }
  currentStrippedArrangementJSON.value = arrangementJSON
  composable.updateSelectedLayout(currentInternalBreakpoint.value, newInternalArrangement)
}

watch(
  composable.selectedLayout,
  (layout) => {
    // Update the current arrangement if the selected layout changed
    const newArrangement = layout[currentInternalBreakpoint.value]
    if (newArrangement === undefined) {
      return
    }
    const newJSON = computeArrangementJSON(newArrangement)
    if (newJSON === currentStrippedArrangementJSON.value) {
      return
    }

    currentStrippedArrangementJSON.value = newJSON
    currentInternalArrangement.value = structuredClone(newArrangement)
  },
  {
    immediate: true
  }
)

// eslint-disable-next-line @typescript-eslint/naming-convention
const { CmkErrorBoundary } = useCmkErrorBoundary()

const enterMissingRuntimeFiltersAction = useInjectMissingRuntimeFiltersAction()
</script>

<template>
  <CmkErrorBoundary>
    <div class="db-responsive-grid__container">
      <div v-if="props.isEditing" class="db-responsive-grid__edit-columns">
        <div
          v-for="n in internalBreakpointConfig.columns[currentInternalBreakpoint]"
          :key="n"
          class="db-responsive-grid__edit-column"
        />
      </div>
      <CmkDialog
        v-if="enterMissingRuntimeFiltersAction !== null"
        :message="_t('Runtime filters are required to load data.')"
        class="db-responsive-grid__missing-filters-dialog"
      />
      <GridLayout
        :key="gridKey"
        class="db-responsive-grid__layout"
        :layout="currentInternalArrangement"
        :responsive-layouts="composable.selectedLayout.value"
        :margin="[gridMargin, gridMargin]"
        :row-height="20"
        :responsive="true"
        :is-draggable="props.isEditing"
        :is-resizable="props.isEditing"
        :vertical-compact="false"
        :breakpoints="internalBreakpointConfig.widths"
        :cols="internalBreakpointConfig.columns"
        @breakpoint-changed="onBreakpointChange"
        @layout-updated="onArrangementUpdate"
      >
        <template #item="{ item }">
          <ResponsiveGridWidget
            :spec="props.contentProps[<string>item.i]!"
            :is-editing="props.isEditing"
            @click:edit="$emit('widget:edit', <string>item.i)"
            @click:delete="$emit('widget:delete', <string>item.i)"
            @click:clone="
              () => {
                const oldWidgetId = item.i as string
                const newLayout = composable.cloneWidgetLayout(oldWidgetId)
                if (newLayout === null) {
                  throw new Error('Original widget not found in all layouts')
                }
                $emit('widget:clone', oldWidgetId, newLayout)
              }
            "
          />
        </template>
      </GridLayout>
    </div>
  </CmkErrorBoundary>
</template>

<style scoped>
.db-responsive-grid__container {
  width: 100%;
  height: 100%;
  position: relative;

  --column-z-index: 1;
  --db-rg-resizer-bg-color: var(--color-daylight-grey-60);
  --db-rg-resizer-bg-hover-color: var(--color-white-50);
}

body[data-theme='modern-dark'] .db-responsive-grid__container {
  --db-rg-resizer-bg-color: var(--color-midnight-grey-60);
  --db-rg-resizer-bg-hover-color: var(--color-white-10);
}

.db-responsive-grid__missing-filters-dialog {
  position: relative;
  z-index: calc(var(--column-z-index) + 1);
  margin: var(--dimension-4);
}

.db-responsive-grid__layout {
  width: 100%;
  height: 100%;
  position: relative;

  /* this must be above the edit columns */
  z-index: calc(var(--column-z-index) + 1);
}

.db-responsive-grid__edit-columns {
  position: absolute;
  z-index: var(--column-z-index);
  display: flex;

  /* using v-bind to keep in sync with the used margins */
  gap: calc(1px * v-bind('gridMargin'));
  top: calc(1px * v-bind('gridMargin'));
  left: calc(1px * v-bind('gridMargin'));
  width: calc(100% - 2px * v-bind('gridMargin'));
  height: 100%;
}

.db-responsive-grid__edit-column {
  flex-grow: 1;
  background-color: var(--color-daylight-grey-30);
}

body[data-theme='modern-dark'] .db-responsive-grid__edit-column {
  background-color: var(--color-conference-grey-100);
}

/* NOTE: third party CSS selector (grid-layout-plus) */
/* stylelint-disable-next-line checkmk/vue-bem-naming-convention,selector-pseudo-class-no-unknown */
:deep(.vgl-item:hover .db-responsive-grid-widget__frame--edit) {
  /* We define the hover effect here, since hovering over the resizer would not count as hovering
   * over the item itself. */
  border-color: var(--color-corporate-green-50);
}

/* NOTE: third party CSS selector (grid-layout-plus) */
/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.vgl-layout {
  --vgl-placeholder-bg: var(--color-corporate-green-50);
  --vgl-placeholder-opacity: 30%;
  --vgl-resizer-border-color: var(--color-corporate-green-80);
}

/* NOTE: third party CSS selector (grid-layout-plus), we have to use :deep for this */
/* stylelint-disable-next-line checkmk/vue-bem-naming-convention,selector-pseudo-class-no-unknown */
:deep(.vgl-item--placeholder) {
  border-radius: 4px;

  /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
  .vgl-item__resizer {
    display: none;
  }
}

/* NOTE: third party CSS selector (grid-layout-plus), we have to use :deep for this */
/* stylelint-disable-next-line selector-pseudo-class-no-unknown,checkmk/vue-bem-naming-convention */
:deep(.vgl-item__resizer) {
  width: var(--dimension-8);
  height: var(--dimension-8);
  z-index: calc(var(--column-z-index) + 4);
  background-color: var(--db-rg-resizer-bg-color);
  border-bottom-right-radius: var(--border-radius);

  &:hover {
    --vgl-resizer-border-color: var(--color-corporate-green-50);

    /* Overlay the transparent hover color
     * This works by using two background layers, the first one is on top and has the hover color.
     * We use linear-gradient since they are treated as images and can thus be layered. */
    background:
      linear-gradient(var(--db-rg-resizer-bg-hover-color), var(--db-rg-resizer-bg-hover-color)),
      linear-gradient(var(--db-rg-resizer-bg-color), var(--db-rg-resizer-bg-color));
  }
}

/* NOTE: third party CSS selector (grid-layout-plus), we have to use :deep for this */
/* stylelint-disable-next-line selector-pseudo-class-no-unknown,checkmk/vue-bem-naming-convention */
:deep(.vgl-item__resizer::before) {
  inset: var(--dimension-4);
}
</style>
