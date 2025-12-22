<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import type { TranslatedString } from '@/lib/i18nString'

import type { SimpleIcons } from '@/components/CmkIcon'
import CmkIcon from '@/components/CmkIcon/CmkIcon.vue'
import CmkLabel from '@/components/CmkLabel.vue'

interface SelectableWidgetProps {
  id: string
  label: TranslatedString
  icon: SimpleIcons
  disabled?: boolean
  selected?: boolean
}

interface SelectableWidgetEmits {
  click: [string]
}

const props = defineProps<SelectableWidgetProps>()
const emit = defineEmits<SelectableWidgetEmits>()

const updateSelectedWidget = () => {
  if (props.disabled) {
    return
  }
  emit('click', props.id)
}

const modifierClass = computed(() => {
  if (props.selected) {
    return 'db-selectable-widget__item-selected'
  }

  if (props.disabled) {
    return 'db-selectable-widget__item-disabled'
  }

  return 'db-selectable-widget__item-available'
})
</script>

<template>
  <div
    class="db-selectable-widget__item"
    :class="modifierClass"
    role="button"
    @click="updateSelectedWidget"
  >
    <div class="db-selectable-widget__item-icon">
      <CmkIcon :name="icon" size="xxlarge" :colored="!disabled" :class="modifierClass" />
    </div>
    <div class="db-selectable-widget__item-label">
      <CmkLabel cursor="pointer" :class="modifierClass">{{ label }}</CmkLabel>
    </div>
  </div>
</template>

<style scoped>
.db-selectable-widget__item {
  display: flex;
  flex: 1 1 0% !important;
  align-items: center;
  padding: 1rem;
  border: var(--dimension-1) solid var(--ux-theme-10);
  border-radius: var(--border-radius);
  box-sizing: border-box;
  text-align: center;
}

.db-selectable-widget__item-label {
  margin-left: var(--dimension-4);
  overflow-wrap: break-word;
}

.db-selectable-widget__item-available {
  cursor: pointer;
}

.db-selectable-widget__item-selected {
  border-color: var(--default-border-color-green);
}

.db-selectable-widget__item-disabled {
  border-color: var(--ux-theme-8);
  color: var(--ux-theme-10);
}
</style>
