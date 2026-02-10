<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

const { _t } = usei18n()

interface DisabledTooltipWrapperProps {
  disabled: boolean
}

const props = defineProps<DisabledTooltipWrapperProps>()
</script>

<template>
  <span
    v-if="props.disabled"
    class="db-disabled-tooltip-wrapper"
    :title="_t('Available in Checkmk Pro or higher.')"
  >
    <slot />
  </span>
  <slot v-else />
</template>

<style scoped>
.db-disabled-tooltip-wrapper {
  display: block;
  width: 100%;
}
</style>
