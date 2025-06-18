<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkHeading1 from '@/components/typography/CmkHeading1.vue'
import CmkHeading2 from '@/components/typography/CmkHeading2.vue'
import CmkBodyText from '@/components/typography/CmkBodyText.vue'

defineProps<{ screenshotMode: boolean }>()
</script>

<template>
  <CmkHeading1> Heading1 </CmkHeading1>
  <CmkHeading2> Heading2 </CmkHeading2>
  <CmkBodyText> Body Text </CmkBodyText>
</template>

<style scoped></style>
