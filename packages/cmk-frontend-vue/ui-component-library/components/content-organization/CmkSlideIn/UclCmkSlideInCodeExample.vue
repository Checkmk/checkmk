<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import CmkButton from '@/components/CmkButton'
import CmkSlideIn from '@/components/CmkSlideIn'
import CmkHeading from '@/components/typography/CmkHeading.vue'

const isOpen = ref(false)
</script>

<template>
  <CmkButton @click="isOpen = true">Open Slide-In</CmkButton>

  <CmkSlideIn :open="isOpen" size="medium" aria-label="Demo Slide-In" @close="isOpen = false">
    <div style="padding: var(--dimension-5)">
      <CmkHeading type="h2">Slide-In Content</CmkHeading>
      <p>
        This is an overlay panel that slides in from the right. It traps focus and prevents
        interaction with the background page.
      </p>
      <CmkButton variant="primary" @click="isOpen = false">Close Panel</CmkButton>
    </div>
  </CmkSlideIn>
</template>
