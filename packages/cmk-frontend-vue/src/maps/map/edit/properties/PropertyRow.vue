<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
One labelled property: its name on the left, the control that edits it on the
right. The card is narrow, so the label column has a fixed width and everything
lines up down the whole card.
-->
<script setup lang="ts">
import CmkLabel from 'cmk-ui-library/components/CmkLabel.vue'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

defineProps<{
  label: TranslatedString
  /** Top-aligns the label for a control that is taller than one line. */
  tall?: boolean
}>()
</script>

<template>
  <div class="maps-property-row" :class="{ 'maps-property-row--tall': tall }">
    <CmkLabel class="maps-property-row__label">{{ label }}</CmkLabel>
    <!-- Named, so what the row edits is announced with it: the controls come in
         through the slot, which cannot carry the label's ``for``. -->
    <div class="maps-property-row__control" role="group" :aria-label="label">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.maps-property-row {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
}

.maps-property-row--tall {
  align-items: flex-start;
}

.maps-property-row__label {
  flex-shrink: 0;
  width: 96px;
  color: var(--font-color-dimmed);
}

.maps-property-row__control {
  display: flex;
  flex: 1;
  min-width: 0;
  align-items: center;
  gap: var(--dimension-4);
}
</style>
