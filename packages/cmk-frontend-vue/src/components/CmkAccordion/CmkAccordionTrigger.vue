<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'
import { getInjectedTriggerItem } from './trigger-item'

const { t } = usei18n('cmk-accordion')

const toggle = getInjectedTriggerItem()

defineProps<{
  value: string
  disabled: boolean
}>()
</script>

<template>
  <button
    :aria-label="t('open-item', `Open accordion item ${value}`)"
    class="cmk-accordion-trigger-button"
    @click="
      () => {
        if (!disabled && toggle) {
          toggle(value)
        }
      }
    "
  ></button>
  <slot />
</template>

<style scoped>
.cmk-accordion-trigger-button {
  padding: 0;
  margin: 0;
  left: 0;
  top: 0;
  background: transparent;
  border: 0;
  position: absolute;
  z-index: +1;
  width: 100%;
  height: 100%;

  &:focus,
  &:active {
    border: 1px solid var(--success);
  }
}
</style>
