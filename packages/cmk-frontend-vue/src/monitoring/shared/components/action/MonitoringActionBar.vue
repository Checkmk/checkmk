<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton/CmkButton.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { computed } from 'vue'

import ActionIcon from '@/monitoring/shared/components/cell/ActionIcon.vue'
import type { CellAction } from '@/monitoring/shared/components/cell/ActionsCell.vue'

const { _t } = usei18n()

const props = defineProps<{
  selectedCount: number
  actions: CellAction[]
  /** How the rows the actions act on are named, e.g. "Selected hosts: 3". */
  selectionLabel: TranslatedString
  /** Names the toolbar for screen readers, e.g. "Actions for selected hosts". */
  label: TranslatedString
  /** The action performing right away, pulsing until it settles. */
  runningActionId?: string | null
}>()

const emit = defineEmits<{
  (event: 'action', action: CellAction): void
}>()

/** Shorter form of the selection label for very narrow containers. */
const shortSelectionLabel = computed(() => _t('Selected: %{count}', { count: props.selectedCount }))

const disabled = computed(() => props.selectedCount === 0)

function select(action: CellAction): void {
  if (disabled.value || action.disabled) {
    return
  }
  emit('action', action)
}
</script>

<template>
  <div
    class="monitoring-action-bar"
    :class="{ 'monitoring-action-bar--disabled': disabled }"
    role="toolbar"
    :aria-label="label"
    :aria-disabled="disabled"
  >
    <span class="monitoring-action-bar__selection" aria-live="polite">
      <span class="monitoring-action-bar__selection-long">{{ selectionLabel }}</span>
      <span class="monitoring-action-bar__selection-short">{{ shortSelectionLabel }}</span>
    </span>
    <div class="monitoring-action-bar__actions">
      <CmkButton
        v-for="action in actions"
        :key="action.id"
        size="small"
        variant="optional"
        :disabled="disabled || action.disabled"
        :title="action.label"
        :running="runningActionId === action.id"
        class="monitoring-action-bar__action"
        @click="select(action)"
      >
        <ActionIcon :icon="action.icon" />
        <span class="monitoring-action-bar__label">{{ action.label }}</span>
      </CmkButton>
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '@/assets/breakpoints' as bp;

.monitoring-action-bar {
  box-sizing: border-box;
  display: flex;
  min-width: 0;
  align-items: center;
  gap: var(--spacing);
  padding: var(--dimension-3) var(--dimension-4);
  border: 1px solid var(--ux-theme-4);
  border-radius: var(--border-radius);
  background: var(--ux-theme-2);
}

.monitoring-action-bar--disabled {
  opacity: 0.6;
}

.monitoring-action-bar__selection {
  flex: 0 0 auto;
  white-space: nowrap;
}

.monitoring-action-bar__action {
  /* CmkButton only spaces icon from label for its `icon` prop, and the icon comes via the slot. */
  gap: var(--dimension-4);
  position: relative;
  white-space: nowrap;
}

/* Inside a container narrower than S only the icon is shown; the label stays available to
   assistive technology (and as tooltip via the button title). */
.monitoring-action-bar__selection-short {
  display: none;
}

@include bp.container-below(s) {
  .monitoring-action-bar__selection-short {
    display: inline;
  }

  .monitoring-action-bar__selection-long {
    display: none;
  }

  .monitoring-action-bar__label {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip-path: inset(50%);
    white-space: nowrap;
  }
}

.monitoring-action-bar__actions {
  display: flex;
  flex: 1 1 auto;
  flex-wrap: wrap;
  gap: var(--dimension-4);
}
</style>
