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
  <CmkHeading> Default Heading </CmkHeading>
  <CmkHeading type="h1"> Heading 1 </CmkHeading>
  <CmkHeading type="h2"> Heading 2 </CmkHeading>
  <CmkHeading type="h3"> Heading 3 </CmkHeading>
  <CmkHeading type="h4"> Heading 4 </CmkHeading>
  <CmkParagraph> Paragraph 1 </CmkParagraph>
  <CmkParagraph> Paragraph 2 </CmkParagraph>
</template>

<style scoped></style>
