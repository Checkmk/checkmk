<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkMultitoneIcon from 'cmk-ui-library/components/CmkIcon/CmkMultitoneIcon.vue'
import usei18n from 'cmk-ui-library/lib/i18n'

import BaseCell, { type CellVerticalAlign } from './BaseCell.vue'

const { _t } = usei18n()

defineProps<{
  columnId?: string | undefined
  verticalAlign?: CellVerticalAlign | undefined
}>()

const visible = defineModel<boolean>({ required: false, default: true })
</script>

<template>
  <BaseCell
    class="monitoring-visibility-cell"
    :column-id="columnId"
    :vertical-align="verticalAlign"
  >
    <button
      type="button"
      class="monitoring-visibility-cell__toggle"
      :aria-pressed="visible"
      :aria-label="_t('Toggle visibility')"
      :title="visible ? _t('Hide') : _t('Show')"
      @click="visible = !visible"
    >
      <CmkMultitoneIcon
        :name="visible ? 'eye' : 'eye-crossed-out'"
        primary-color="font"
        aria-hidden="true"
      />
    </button>
  </BaseCell>
</template>

<style scoped>
.monitoring-visibility-cell__toggle {
  margin: 0;
  padding: 0;
  background: none;
  border: none;
  cursor: pointer;
  display: inline-flex;

  &:focus-visible {
    outline: revert;
  }
}
</style>
