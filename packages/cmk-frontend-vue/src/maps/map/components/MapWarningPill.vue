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
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

defineProps<{
  /** The full explanation; the slot holds the short form. */
  message: TranslatedString
}>()
</script>

<template>
  <span class="maps-map-warning-pill" role="status" :aria-label="message" :title="message">
    <CmkIcon name="problem" size="small" />
    <slot />
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
  font-weight: var(--font-weight-bold);
  color: var(--status-text-color-warning-strong);
  background: color-mix(in srgb, var(--color-state-warning) var(--status-tint-mix), transparent);
  border-radius: 9999px;
  box-shadow: 0 0 0 1px
    color-mix(in srgb, var(--color-state-warning) var(--status-tint-border-mix), transparent);
}
</style>
