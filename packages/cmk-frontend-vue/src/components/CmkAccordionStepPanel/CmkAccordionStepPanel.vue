<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAccordion from '../CmkAccordion/CmkAccordion.vue'

const model = defineModel<string[]>({ required: true })
</script>

<template>
  <CmkAccordion v-model="model" :max-open="0" :min-open="0" class="cmk-accordion-step-panels">
    <slot />
  </CmkAccordion>
</template>

<style scoped></style>
