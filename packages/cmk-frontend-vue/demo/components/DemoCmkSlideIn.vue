<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { ref } from 'vue'

import CmkButton from '@/components/CmkButton.vue'
import CmkSlideIn from '@/components/CmkSlideIn'

const isOpen = ref(false)

const openSlideIn = () => {
  isOpen.value = true
}

const closeSlideIn = () => {
  isOpen.value = false
}
defineProps<{ screenshotMode: boolean }>()
</script>

<template>
  <div>
    <CmkButton @click="openSlideIn"> Open </CmkButton>

    <CmkSlideIn :open="isOpen" size="small" @close="closeSlideIn">
      <div>
        <h2>Small Slide-In</h2>
        <p>This is a simple slide-in panel example.</p>
        <button @click="closeSlideIn">Close</button>
      </div>
    </CmkSlideIn>
  </div>
</template>
