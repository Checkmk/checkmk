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

interface WidgetTileProps {
  label: TranslatedString
  icon: SimpleIcons
  disabled?: boolean
  selected?: boolean
  compact?: boolean
}

const props = defineProps<WidgetTileProps>()

const modifierClass = computed(() => {
  if (props.selected) {
    return 'db-widget-tile__item-selected'
  }

  if (props.disabled) {
    return 'db-widget-tile__item-disabled'
  }

  return 'db-widget-tile__item-available'
})
</script>

<template>
  <div class="db-widget-tile__item" :class="modifierClass">
    <div class="db-widget-tile__item-icon">
      <CmkIcon :name="icon" :size="compact ? 'xlarge' : 'xxlarge'" :colored="!disabled" />
    </div>
    <div class="db-widget-tile__item-label">
      <CmkLabel :cursor="disabled ? 'default' : 'pointer'">{{ label }}</CmkLabel>
    </div>
  </div>
</template>

<style scoped>
.db-widget-tile__item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  gap: var(--dimension-4);
  padding: var(--dimension-4);
  width: 100%;
  height: 100%;
  text-align: center;
  border: 1px solid var(--ux-theme-6);
  border-radius: var(--dimension-4);
  box-sizing: border-box;
}

.db-widget-tile__item-icon {
  display: block;
}

.db-widget-tile__item-label {
  display: block;
  overflow-wrap: break-word;
}

.db-widget-tile__item-available {
  cursor: pointer;

  &:hover {
    background-color: rgb(from var(--default-form-element-bg-color) r g b / 60%);
  }
}

.db-widget-tile__item-selected {
  border-color: var(--default-border-color-green);
  cursor: pointer;

  &:hover {
    background-color: rgb(from var(--default-form-element-bg-color) r g b / 60%);
  }
}

.db-widget-tile__item-disabled {
  border-color: var(--ux-theme-8);
  color: var(--ux-theme-10);
}
</style>
