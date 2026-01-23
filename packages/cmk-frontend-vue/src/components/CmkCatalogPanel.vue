<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref, useId } from 'vue'

import usei18n from '@/lib/i18n'
import type { TranslatedString } from '@/lib/i18nString'

import CmkCollapsible from '@/components/CmkCollapsible'
import CmkIcon from '@/components/CmkIcon'

const { _t } = usei18n()

const { title, open: initialOpen = true } = defineProps<{
  title: TranslatedString
  open?: boolean
}>()

const open = ref(initialOpen)

const label = _t('Toggle %{ title }', { title })

const id = useId()
</script>

<template>
  <div class="cmk-catalog-panel__container">
    <button
      class="cmk-catalog-panel__header"
      :title="label"
      :aria-label="label"
      :aria-controls="id"
      @click.prevent="open = !open"
    >
      <CmkIcon
        class="cmk-catalog-panel__icon"
        :class="{ 'cmk-catalog-panel__icon--open': open }"
        name="tree-closed"
        size="xxsmall"
      />
      <slot name="header">{{ title }}</slot>
    </button>
    <CmkCollapsible :content-id="id" :open="open">
      <div class="cmk-catalog-panel__content">
        <slot />
      </div>
    </CmkCollapsible>
  </div>
</template>

<style scoped>
.cmk-catalog-panel__title-container {
  width: 100%;
  padding: 0;
  margin: 10px 0;
  border-radius: 4px;
  border-collapse: collapse;
}

.cmk-catalog-panel__header {
  width: 100%;
  background: var(--ux-theme-3);
  padding: 4px 10px 3px 9px;
  margin: 0;
  font-weight: 700;
  letter-spacing: 1px;
  vertical-align: middle;
  text-align: left;
  border-radius: 4px 4px 0 0;
  border: none;

  /* Reset global style from global css */
  button&:active {
    box-shadow: none;
  }

  &:hover {
    background: var(--ux-theme-5);
  }

  .cmk-catalog-panel__icon {
    margin-right: var(--spacing);
    transition: transform 0.2s ease-in-out;

    &.cmk-catalog-panel__icon--open {
      transform: rotate(90deg);
    }
  }
}

.cmk-catalog-panel__content {
  background: var(--ux-theme-2);
  padding: var(--spacing-half) var(--spacing);
}
</style>
