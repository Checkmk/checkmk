<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
export const codeExample = `<script setup lang="ts">
${'import'} CmkParagraph from '@/components/typography/CmkParagraph.vue'
<${'/'}script>

<template>
  <CmkParagraph>
    The quick brown fox jumps over the lazy dog.
  </CmkParagraph>
</template>`
</script>

<script setup lang="ts">
import {
  UclDetailPageAccessibility,
  UclDetailPageCodeExample,
  UclDetailPageComponent,
  UclDetailPageHeader,
  UclDetailPageLayout
} from '@ucl/_ucl/components/detail-page'

import CmkParagraph from '@/components/typography/CmkParagraph.vue'

defineProps<{ screenshotMode: boolean }>()
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>CmkParagraph</UclDetailPageHeader>

    <UclDetailPageComponent>
      <CmkParagraph>The quick brown fox jumps over the lazy dog.</CmkParagraph>
    </UclDetailPageComponent>

    <UclDetailPageCodeExample :code="codeExample" />

    <UclDetailPageAccessibility :data="[]" />
  </UclDetailPageLayout>
</template>
