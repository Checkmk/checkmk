<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'
import { getIsItemExpandedCallback, getInjectedTriggerItem } from './trigger-item'
const { t } = usei18n('cmk-accordion')

const toggleItem = getInjectedTriggerItem()
const isItemExpanded = getIsItemExpandedCallback()

const props = defineProps<{
  value: string
  disabled: boolean
}>()

function toggle() {
  if (!props.disabled) {
    toggleItem(props.value)
  }
}
</script>

<template>
  <button
    :id="'cmk-accordion-trigger-'.concat(props.value)"
    :aria-controls="'cmk-accordion-content-'.concat(props.value)"
    :aria-expanded="isItemExpanded(props.value)"
    :aria-label="t('toggle-accordion-item', 'Toggle accordion item ').concat(props.value)"
    class="cmk-accordion-trigger-button"
    @click="toggle"
    @keydpress.enter="toggle"
    @keydpress.space="toggle"
  >
    <slot />
  </button>
</template>

<style scoped>
.cmk-accordion-trigger-button {
  padding: 20px;
  margin: 0;
  left: 0;
  top: 0;
  background: transparent;
  display: flex;
  flex-direction: row;
  align-items: center;
  border: 0;
  width: 100%;
  height: 100%;

  &:focus-visible {
    border: 1px solid var(--success);
  }
}
</style>
