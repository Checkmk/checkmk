<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import { getInjectedTriggerItem, getIsItemExpandedCallback } from './trigger-item'

const { _t } = usei18n()

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
    :aria-label="_t('Toggle accordion item %{item}', { item: props.value })"
    class="cmk-accordion-trigger__button"
    @click="toggle"
    @keydpress.enter="toggle"
    @keydpress.space="toggle"
  >
    <slot />
  </button>
</template>

<style scoped>
.cmk-accordion-trigger__button {
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
