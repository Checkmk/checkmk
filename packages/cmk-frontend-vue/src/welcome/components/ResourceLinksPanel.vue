<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import usei18n from '@/lib/i18n'
import CmkHeading2 from '@/components/typography/CmkHeading2.vue'
import CmkLinkCard from '@/components/CmkLinkCard.vue'
import CmkSpace from '@/components/CmkSpace.vue'

// TODO: send urls from the backend.

const { t } = usei18n('resource-links-panel')
</script>

<template>
  <CmkHeading2>
    {{ t('resources', 'Resources') }}
  </CmkHeading2>
  <CmkSpace />
  <CmkLinkCard
    :title="t('ask-ai', 'Ask Checkmk AI')"
    :subtitle="
      t(
        'ask-ai-subtitle',
        'Your assistant for Checkmk - ask anything from setup to troubleshooting.'
      )
    "
    url="https://chat.checkmk.com"
    variant="borderless"
    :open-in-new-tab="true"
  />
  <CmkLinkCard
    :title="t('beginners-guide', 'Read the Beginner’s Guide')"
    :subtitle="
      t(
        'beginners-guide-subtitle',
        'A step-by-step introduction to help you get started quickly and confidently.'
      )
    "
    url="https://docs.checkmk.com"
    variant="borderless"
    :open-in-new-tab="true"
  />
  <CmkLinkCard
    :title="t('community', 'Join the community')"
    :subtitle="
      t('community-subtitle', 'Connect with other users and ask questions in our active forum.')
    "
    url="https://forum.checkmk.com/"
    variant="borderless"
    :open-in-new-tab="true"
  />
</template>

<style scoped></style>
