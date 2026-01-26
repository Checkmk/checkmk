<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import DashboardContent from '@/dashboard/components/DashboardContent/DashboardContent.vue'
import type { ContentProps } from '@/dashboard/components/DashboardContent/types'
import MissingFiltersMsg from '@/dashboard/components/DashboardFilterSettings/MissingFiltersMsg.vue'

import ResponsiveGridWidgetButton from './ResponsiveGridWidgetButton.vue'

const { _t } = usei18n()

interface Props {
  spec: ContentProps
  isEditing: boolean
}
const { spec, isEditing } = defineProps<Props>()

defineEmits<{
  'click:edit': []
  'click:clone': []
  'click:delete': []
}>()
</script>

<template>
  <div
    :id="`widget-${spec.widget_id}`"
    class="db-responsive-grid-widget__frame"
    :class="{ 'db-responsive-grid-widget__frame--edit': isEditing }"
    :aria-label="_t('Widget')"
  >
    <div v-if="isEditing" class="db-responsive-grid-widget__edit-controls">
      <div class="db-responsive-grid-widget__edit-controls-buttons">
        <ResponsiveGridWidgetButton
          icon-name="db-widget-delete"
          :title="_t('Delete widget')"
          @click="$emit('click:delete')"
        />
        <ResponsiveGridWidgetButton
          icon-name="db-widget-clone"
          :title="_t('Clone widget')"
          @click="$emit('click:clone')"
        />
        <ResponsiveGridWidgetButton
          icon-name="db-widget-edit"
          :title="_t('Edit widget')"
          @click="$emit('click:edit')"
        />
      </div>
    </div>
    <MissingFiltersMsg :effective-filter-context="spec.effective_filter_context">
      <DashboardContent v-bind="spec" class="db-responsive-grid-widget__content" />
    </MissingFiltersMsg>
  </div>
</template>

<style scoped>
.db-responsive-grid-widget__frame {
  height: 100%;
  width: 100%;
  position: relative;
  overflow: hidden;
}

.db-responsive-grid-widget__frame--edit {
  /* disable selecting text while dragging / resizing widgets */
  user-select: none;

  /* show border, reduce margin to keep size the same */
  margin: -1px;
  border-radius: var(--border-radius);
  border: 1px solid var(--color-corporate-green-80);

  /* NOTE: the hover effect is defined in ResponsiveGrid.vue */
  transition: border-color 200ms ease;
}

.db-responsive-grid-widget__content,
.db-responsive-grid-widget__edit-controls {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}

.db-responsive-grid-widget__edit-controls {
  /* this must be above the content and placeholder, but below the resizer */
  z-index: 4;
  background-color: color-mix(in srgb, var(--color-daylight-grey-50) 50%, transparent);
}

body[data-theme='modern-dark'] .db-responsive-grid-widget__edit-controls {
  background-color: color-mix(in srgb, var(--color-midnight-grey-90) 50%, transparent);
}

.db-responsive-grid-widget__edit-controls-buttons {
  position: absolute;
  top: 0;
  right: 0;

  /* align buttons on the right */
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: flex-end;
}
</style>
