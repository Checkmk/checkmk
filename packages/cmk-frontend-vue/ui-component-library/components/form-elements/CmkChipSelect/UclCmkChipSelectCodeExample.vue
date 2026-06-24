<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import CmkChipSelect from '@/components/CmkChipSelect.vue'

const selected = ref<string | null>(null)
</script>

<template>
  <CmkChipSelect
    v-model="selected"
    :options="{
      type: 'fixed',
      suggestions: [
        { name: '1h', title: 'Last hour' },
        { name: '1d', title: 'Last day' }
      ]
    }"
    input-hint="More ranges"
    label="time range"
  />
</template>
