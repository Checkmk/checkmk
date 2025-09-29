<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

const { currentLanguage } = usei18n()
</script>

<template>
  <div v-if="!!currentLanguage" class="cmk-vue-app">
    <slot />
  </div>
</template>
