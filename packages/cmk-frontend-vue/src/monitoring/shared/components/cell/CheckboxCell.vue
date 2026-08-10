<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkCheckbox from 'cmk-ui-library/components/user-input/CmkCheckbox.vue'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import BaseCell, { type CellVerticalAlign } from './BaseCell.vue'

defineProps<{
  columnId?: string | undefined
  ariaLabel?: TranslatedString | undefined
  verticalAlign?: CellVerticalAlign | undefined
}>()

const value = defineModel<boolean>({ required: false, default: false })

function toggle(): void {
  value.value = !value.value
}
</script>

<template>
  <BaseCell class="monitoring-checkbox-cell" :column-id="columnId" :vertical-align="verticalAlign">
    <template #default>
      <div
        class="monitoring-checkbox-cell__hit-area"
        :class="{
          'monitoring-checkbox-cell__hit-area--vertical-middle': verticalAlign === 'middle'
        }"
        @click="toggle"
      >
        <CmkCheckbox v-model="value" :aria-label="ariaLabel" @click.stop></CmkCheckbox>
      </div>
    </template>
  </BaseCell>
</template>

<style scoped>
/* stylelint-disable selector-pseudo-class-no-unknown */
.monitoring-checkbox-cell {
  height: 1px;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
td.monitoring-checkbox-cell :deep(.monitoring-base-cell__wrapper) {
  height: 100%;
  padding: 0;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
td.monitoring-checkbox-cell :deep(.monitoring-base-cell__plain) {
  height: 100%;
  padding: 0;
}

.monitoring-checkbox-cell__hit-area {
  box-sizing: border-box;
  height: 100%;
  padding: 5px var(--dimension-4);
  cursor: pointer;
}

.monitoring-checkbox-cell__hit-area--vertical-middle {
  display: flex;
  align-items: center;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.monitoring-checkbox-cell__hit-area :deep(.cmk-checkbox__container) {
  pointer-events: none;
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.monitoring-checkbox-cell__hit-area:hover :deep(.cmk-checkbox__button) {
  background-color: var(--input-hover-bg-color);
}
</style>
