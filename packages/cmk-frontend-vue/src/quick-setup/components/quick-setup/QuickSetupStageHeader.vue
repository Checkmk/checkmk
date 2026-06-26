<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkCollapsible from '@/components/CmkCollapsible/CmkCollapsible.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkParagraph from '@/components/typography/CmkParagraph.vue'

interface QuickSetupStageHeaderProps {
  title: string
  subTitle?: string | null | undefined
  isCompleted?: boolean
}

defineProps<QuickSetupStageHeaderProps>()
</script>

<template>
  <div>
    <CmkHeading type="h2" class="qs-stage-header__title">{{ title }}</CmkHeading>

    <CmkCollapsible v-if="!!subTitle" :open="!isCompleted">
      <CmkParagraph class="qs-stage-header__subtitle">{{ subTitle }}</CmkParagraph>
    </CmkCollapsible>
  </div>
</template>

<style scoped>
.qs-stage-header__title {
  margin: 2px 0;
}

.qs-stage-header__subtitle {
  margin-bottom: var(--spacing);
}
</style>
