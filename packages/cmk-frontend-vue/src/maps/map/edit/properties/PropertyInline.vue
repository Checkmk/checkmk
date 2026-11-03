<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
Values that only make sense together, side by side in one row: a position's
coordinates, a label's offset. Each one is a PropertyInlineInput.
-->
<script setup lang="ts">
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

/** Names the row as a group; left out where a PropertyRow around it already does. */
defineProps<{ label?: TranslatedString | undefined }>()
</script>

<template>
  <div class="maps-property-inline" v-bind="label ? { role: 'group', 'aria-label': label } : {}">
    <slot />
  </div>
</template>

<style scoped>
.maps-property-inline {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--dimension-4) var(--dimension-7);
}
</style>
