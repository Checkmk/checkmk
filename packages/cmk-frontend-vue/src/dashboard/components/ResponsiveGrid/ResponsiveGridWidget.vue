<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkIconButton from '@/components/CmkIconButton.vue'

import DashboardContent from '@/dashboard/components/DashboardContent/DashboardContent.vue'
import type { ContentProps } from '@/dashboard/components/DashboardContent/types'
import MissingRuntimeFiltersMsg from '@/dashboard/components/DashboardFilterSettings/runtime-filter/MissingRuntimeFiltersMsg.vue'

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
        <!-- TODO: icons are too small, likely need re-export of the SVG and adjustment here -->
        <CmkIconButton
          class="db-responsive-widget-frame__edit-controls-button"
          name="widget-delete"
          size="medium"
          @click="$emit('click:delete')"
        />
        <CmkIconButton
          class="db-responsive-grid-widget__edit-controls-button"
          name="widget-clone"
          size="medium"
          @click="$emit('click:clone')"
        />
        <CmkIconButton
          class="db-responsive-grid-widget__edit-controls-button"
          name="widget-edit"
          size="medium"
          @click="$emit('click:edit')"
        />
      </div>
    </div>
    <MissingRuntimeFiltersMsg>
      <DashboardContent v-bind="spec" class="db-responsive-grid-widget__content" />
    </MissingRuntimeFiltersMsg>
  </div>
</template>

<style scoped>
.db-responsive-grid-widget__frame {
  height: 100%;
  width: 100%;
  background-color: var(--color-midnight-grey-70);
  position: relative;
  overflow: hidden;
}

.db-responsive-grid-widget__frame--edit {
  /* disable selecting text while dragging / resizing widgets */
  user-select: none;

  /* show border, reduce margin to keep size the same */
  margin: -1px;
  border-radius: 4px;
  border: 1px solid var(--color-corporate-green-80);
  transition: border-color 200ms ease;

  &:hover {
    border-color: var(--color-corporate-green-50);
  }
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
  background-color: color-mix(in srgb, var(--color-midnight-grey-100) 40%, transparent);
}

.db-responsive-grid-widget__edit-controls-buttons {
  /* menu bar on top */
  height: 23px;
  width: 100%;
  background-color: color-mix(in srgb, var(--color-midnight-grey-100) 80%, transparent);

  /* align buttons on the right */
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: flex-end;
  gap: 4px;
}

.db-responsive-grid-widget__edit-controls-button {
  padding: 4px;

  /* filter to make icons white */
  filter: brightness(0) saturate(100%) invert(100%) brightness(70%);
  transition: filter 200ms ease;

  &:hover {
    filter: brightness(0) saturate(100%) invert(100%) brightness(100%);
  }
}
</style>
