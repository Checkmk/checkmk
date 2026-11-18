<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
A warning about the whole map, said in the topbar beside the live indicator: a
banner over the map would cover the objects and the search it sits above.
-->
<script setup lang="ts">
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import CmkTooltip, {
  CmkTooltipContent,
  CmkTooltipProvider,
  CmkTooltipTrigger
} from 'cmk-ui-library/components/CmkTooltip'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { ref } from 'vue'

defineProps<{
  /** The full explanation; the slot holds the short form. */
  message: TranslatedString
}>()

const explained = ref(false)
</script>

<template>
  <span role="status" :aria-label="message">
    <CmkTooltipProvider :delay-duration="200">
      <CmkTooltip v-model:open="explained">
        <CmkTooltipTrigger as-child>
          <!-- A button, so the explanation is there for the keyboard too. -->
          <button type="button" class="maps-map-warning-pill">
            <CmkIcon name="problem" size="small" />
            <slot />
          </button>
        </CmkTooltipTrigger>
        <CmkTooltipContent side="bottom" align="end">{{ message }}</CmkTooltipContent>
      </CmkTooltip>
    </CmkTooltipProvider>
  </span>
</template>

<style scoped>
.maps-map-warning-pill {
  display: flex;
  align-items: center;
  gap: var(--dimension-3);
  padding: var(--dimension-2) var(--dimension-4);
  font-size: var(--font-size-normal);
  line-height: 16px;
  font-family: inherit;
  font-weight: var(--font-weight-bold);
  color: var(--status-text-color-warning-strong);
  cursor: default;
  background: color-mix(in srgb, var(--color-state-warning) var(--status-tint-mix), transparent);
  border: 0;
  border-radius: 9999px;
  box-shadow: 0 0 0 1px
    color-mix(in srgb, var(--color-state-warning) var(--status-tint-border-mix), transparent);
}

.maps-map-warning-pill:focus-visible {
  outline: revert;
  outline-offset: 2px;
}
</style>
