<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import CmkButton from '@/components/CmkButton.vue'
import CmkPopup from '@/components/CmkPopup.vue'

const isOpen = ref(false)
</script>

<template>
  <CmkButton @click="isOpen = true">Open Popup</CmkButton>
  <CmkPopup :open="isOpen" @close="isOpen = false">
    <p>Popup content goes here.</p>
  </CmkPopup>
</template>
