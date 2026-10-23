<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkLabel from 'cmk-ui-library/components/CmkLabel.vue'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

/** One label-value pair, laid out the way the forms of Setup lay out theirs. */
const props = defineProps<{
  label: TranslatedString
  help?: TranslatedString | undefined
  /** The id of the input the label names, if the value is a single input. */
  for?: string | undefined
  labelId?: string | undefined
}>()
</script>

<template>
  <div class="mode-host-relation-detection-labeled-row">
    <div class="mode-host-relation-detection-labeled-row__label">
      <CmkLabel
        :id="props.labelId"
        :for="props.for ?? ''"
        :help="props.help"
        cursor="inherit"
        dots
        grow
        >{{ props.label }}</CmkLabel
      >
    </div>
    <div class="mode-host-relation-detection-labeled-row__value">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.mode-host-relation-detection-labeled-row {
  display: flex;
  align-items: flex-start;
  gap: var(--dimension-4);
}

.mode-host-relation-detection-labeled-row__label {
  display: flex;
  flex: 0 0 240px;
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
}

.mode-host-relation-detection-labeled-row__value {
  display: flex;
  flex: 1 1 0;
  flex-direction: column;
  gap: var(--spacing-half);
  min-width: 0;
}
</style>
