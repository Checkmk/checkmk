<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

defineProps<{ screenshotMode: boolean }>()
</script>

<template>
  <CmkHeading type="h1"> Heading1 </CmkHeading>
  <CmkHeading type="h2"> Heading2 </CmkHeading>
  <CmkParagraph> Paragraph </CmkParagraph>
</template>

<style scoped></style>
