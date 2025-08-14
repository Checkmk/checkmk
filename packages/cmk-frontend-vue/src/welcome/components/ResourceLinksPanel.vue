<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import usei18n from '@/lib/i18n'
import CmkHeading from '@/components/typography/CmkHeading.vue'
import CmkLinkCard from '@/components/CmkLinkCard.vue'
import CmkSpace from '@/components/CmkSpace.vue'
import type { WelcomeUrls } from 'cmk-shared-typing/typescript/welcome'
import CmkLinkCardContainer from '@/components/CmkLinkCardContainer.vue'

const { _t } = usei18n()
defineProps<{
  urls: WelcomeUrls
}>()
</script>

<template>
  <CmkHeading type="h4">
    {{ _t('Resources') }}
  </CmkHeading>
  <CmkSpace />
  <CmkLinkCardContainer>
    <CmkLinkCard
      :title="_t('Ask Checkmk AI')"
      :subtitle="_t('Your assistant for Checkmk - ask anything from setup to troubleshooting.')"
      :url="urls.checkmk_ai"
      variant="borderless"
      :open-in-new-tab="true"
    />
    <CmkLinkCard
      :title="_t('Read the Beginner’s Guide')"
      :subtitle="_t('A step-by-step introduction to help you get started quickly and confidently.')"
      :url="urls.checkmk_docs"
      variant="borderless"
      :open-in-new-tab="true"
    />
    <CmkLinkCard
      :title="_t('Join the community')"
      :subtitle="_t('Connect with other users and ask questions in our active forum.')"
      :url="urls.checkmk_forum"
      variant="borderless"
      :open-in-new-tab="true"
    />
  </CmkLinkCardContainer>
</template>

<style scoped></style>
