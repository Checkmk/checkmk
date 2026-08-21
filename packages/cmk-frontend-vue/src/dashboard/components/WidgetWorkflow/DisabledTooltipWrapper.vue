<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

interface DisabledTooltipWrapperProps {
  disabled: boolean
  tooltip?: TranslatedString | undefined
}

const props = defineProps<DisabledTooltipWrapperProps>()
</script>

<template>
  <span v-if="props.disabled" class="db-disabled-tooltip-wrapper" :title="props.tooltip">
    <slot />
  </span>
  <slot v-else />
</template>

<style scoped>
.db-disabled-tooltip-wrapper {
  display: block;
  width: 100%;
  height: 100%;
}
</style>
