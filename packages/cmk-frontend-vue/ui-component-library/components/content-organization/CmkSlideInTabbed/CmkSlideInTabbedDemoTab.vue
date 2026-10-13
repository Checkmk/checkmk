<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'

defineProps<{
  label: string
  data?: { loadedAt: string } | undefined
}>()
</script>

<template>
  <div>
    <CmkHeading type="h3">{{ label }}</CmkHeading>
    <CmkParagraph>
      This body is only mounted once it is on show, and its <code>data</code> is fetched
      asynchronously by the loader the page supplied.
    </CmkParagraph>
    <CmkParagraph v-if="data"> Loaded at: {{ data.loadedAt }} </CmkParagraph>
  </div>
</template>
