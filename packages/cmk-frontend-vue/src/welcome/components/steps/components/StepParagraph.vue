<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkParagraph from '@/components/typography/CmkParagraph.vue'
</script>

<template>
  <CmkParagraph class="welcome-step-paragraph">
    <slot />
  </CmkParagraph>
</template>

<style scoped>
.welcome-step-paragraph {
  margin-bottom: var(--spacing);
}
</style>
