<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

const { currentLanguage } = usei18n()

export interface CmkAppProps {
  fullPage?: boolean
}

defineProps<CmkAppProps>()
</script>

<template>
  <div
    v-if="!!currentLanguage"
    class="cmk-vue-app"
    :class="{ 'lib-cmk-app__full-page': fullPage!! }"
  >
    <slot />
  </div>
</template>

<style scoped>
.lib-cmk-app__full-page {
  height: 100%;
}
</style>
