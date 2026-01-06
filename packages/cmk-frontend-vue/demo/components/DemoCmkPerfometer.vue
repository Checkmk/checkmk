<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import CmkPerfometer from '@/components/CmkPerfometer.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkInput from '@/components/user-input/CmkInput.vue'

defineProps<{ screenshotMode: boolean }>()

const value = ref(75)
</script>

<template>
  <CmkHeading type="h3">Input value:</CmkHeading>
  <br />
  <CmkInput v-model="value" type="number" />

  <br />
  <CmkHeading type="h3">Perfometer:</CmkHeading>
  <br />
  <CmkPerfometer :value="value" :value-range="[0, 100]" :formatted="`${value} %`" color="green" />
</template>
