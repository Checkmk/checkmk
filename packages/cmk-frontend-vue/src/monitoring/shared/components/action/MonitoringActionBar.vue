<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton/CmkButton.vue'
import ArrowDown from 'cmk-ui-library/components/graphics/ArrowDown.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import {
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuPortal,
  DropdownMenuRoot,
  DropdownMenuTrigger
} from 'reka-ui'
import { computed, ref } from 'vue'

import ActionIcon from '@/monitoring/shared/components/cell/ActionIcon.vue'
import type { CellAction } from '@/monitoring/shared/components/cell/ActionsCell.vue'

const { _t } = usei18n()

const props = withDefaults(
  defineProps<{
    selectedCount: number
    actions: CellAction[]
    /** The entries of the "More" menu after the buttons. */
    moreActions?: CellAction[]
    /** How the rows the actions act on are named, e.g. "Selected hosts: 3". */
    selectionLabel: TranslatedString
    /** Names the toolbar for screen readers, e.g. "Actions for selected hosts". */
    label: TranslatedString
    /** The action performing right away, pulsing until it settles. */
    runningActionId?: string | null
  }>(),
  { moreActions: () => [], runningActionId: null }
)

const emit = defineEmits<{
  (event: 'action', action: CellAction): void
}>()

/** Shorter form of the selection label for very narrow containers. */
const shortSelectionLabel = computed(() => _t('Selected: %{count}', { count: props.selectedCount }))

const disabled = computed(() => props.selectedCount === 0)

const moreOpen = ref(false)

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
      <DropdownMenuRoot v-if="moreActions.length > 0" v-model:open="moreOpen">
        <DropdownMenuTrigger as-child :disabled="disabled">
          <CmkButton
            size="small"
            variant="optional"
            :disabled="disabled"
            :title="_t('More actions')"
            class="monitoring-action-bar__action"
          >
            <span class="monitoring-action-bar__more-label">{{ _t('More') }}</span>
            <ArrowDown
              class="monitoring-action-bar__more-icon"
              :class="{ 'monitoring-action-bar__more-icon--open': moreOpen }"
              aria-hidden="true"
            />
          </CmkButton>
        </DropdownMenuTrigger>
        <DropdownMenuPortal>
          <DropdownMenuContent
            class="cmk-vue-app monitoring-action-bar__menu"
            align="start"
            :side-offset="4"
          >
            <DropdownMenuItem
              v-for="action in moreActions"
              :key="action.id"
              class="monitoring-action-bar__menu-item"
              :title="action.tooltip ?? action.label"
              :disabled="action.disabled === true"
              @select="select(action)"
            >
              <ActionIcon :icon="action.icon" />
              <span>{{ action.label }}</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenuPortal>
      </DropdownMenuRoot>
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

.monitoring-action-bar__more-icon {
  width: 8px;
  height: 8px;
}

.monitoring-action-bar__more-icon--open {
  transform: rotate(180deg);
}
</style>

<style>
/* The menu is teleported out of the bar, so its styles cannot be scoped. */
/* stylelint-disable checkmk/vue-bem-naming-convention */
.monitoring-action-bar__menu {
  display: flex;
  flex-direction: column;
  min-width: 200px;
  padding: var(--dimension-2);
  background: var(--ux-theme-1);
  border: 1px solid var(--ux-theme-6);
  border-radius: var(--border-radius);
  box-shadow: 0 2px 8px rgb(0 0 0 / 30%);
  z-index: var(--z-index-modal);
}

.monitoring-action-bar__menu-item {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
  padding: var(--dimension-3) var(--dimension-4);
  border-radius: var(--dimension-2);
  white-space: nowrap;
  cursor: pointer;
  outline: none;
  user-select: none;

  &[data-highlighted] {
    background-color: var(--ux-theme-3);
  }

  &[data-disabled] {
    opacity: 0.5;
    cursor: not-allowed;
  }
}
</style>
