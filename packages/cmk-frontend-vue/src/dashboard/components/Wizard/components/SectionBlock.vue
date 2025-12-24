<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { TranslatedString } from '@/lib/i18nString'

import CmkHeading from '@/components/typography/CmkHeading.vue'

import ContentSpacer from './ContentSpacer.vue'

interface SectionBlockProps {
  title: TranslatedString
}

defineProps<SectionBlockProps>()
</script>

<template>
  <div role="region" :aria-label="title">
    <CmkHeading type="h3">
      {{ title }}
    </CmkHeading>

    <ContentSpacer :dimension="5" />

    <slot />

    <ContentSpacer :dimension="8" />
  </div>
</template>
