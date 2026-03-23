<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import CmkButton from '@/components/CmkButton'
import CmkPaste from '@/components/CmkPaste.vue'

const inputValue = ref('')
</script>

<template>
  <CmkPaste>
    <template #trigger>
      <CmkButton variant="secondary">Paste</CmkButton>
    </template>
    <template #input>
      <input v-model="inputValue" />
    </template>
  </CmkPaste>
</template>
