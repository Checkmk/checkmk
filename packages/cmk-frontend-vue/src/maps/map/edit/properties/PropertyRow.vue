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
import useId from 'cmk-ui-library/lib/useId'

defineProps<{
  label: TranslatedString
  /** Top-aligns the label for a control that is taller than one line. */
  tall?: boolean
  labelsControl?: boolean
}>()

defineSlots<{
  /** ``id`` goes on the control, so the label names it. */
  default(props: { id: string; label: TranslatedString }): unknown
}>()

const id = useId()
</script>

<template>
  <div class="maps-property-row" :class="{ 'maps-property-row--tall': tall }">
    <CmkLabel v-bind="labelsControl ? { for: id } : {}" class="maps-property-row__label">
      {{ label }}
    </CmkLabel>
    <!-- A control the label cannot point at is named by the group around it. -->
    <div
      class="maps-property-row__control"
      v-bind="labelsControl ? {} : { role: 'group', 'aria-label': label }"
    >
      <slot :id="id" :label="label" />
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
