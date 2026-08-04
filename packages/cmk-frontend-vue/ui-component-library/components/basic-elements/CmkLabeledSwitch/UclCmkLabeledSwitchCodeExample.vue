<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkLabeledSwitch from 'cmk-ui-library/components/CmkLabeledSwitch.vue'
import { ref } from 'vue'

const peakZoomActive = ref(false)
</script>

<template>
  <CmkLabeledSwitch
    v-model="peakZoomActive"
    off-label="Time zoom"
    on-label="Peak zoom"
    off-help="Drag to zoom into a time range."
    on-help="Drag to zoom into a value range."
  />
</template>
