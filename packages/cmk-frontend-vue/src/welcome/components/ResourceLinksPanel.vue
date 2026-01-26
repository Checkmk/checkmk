<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { WelcomeCards } from 'cmk-shared-typing/typescript/welcome'

import usei18n from '@/lib/i18n'

import CmkLinkCard, { CmkLinkCardContainer } from '@/components/CmkLinkCard'
import CmkSpace from '@/components/CmkSpace.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'

const { _t } = usei18n()
defineProps<{
  cards: WelcomeCards
}>()
</script>

<template>
  <CmkHeading type="h4">
    {{ _t('Resources') }}
  </CmkHeading>
  <CmkSpace />
  <CmkLinkCardContainer>
    <CmkLinkCard
      :title="_t('Read the Beginner’s Guide')"
      :subtitle="_t('A step-by-step introduction to help you get started quickly and confidently.')"
      :url="cards.checkmk_docs"
      variant="borderless"
      :open-in-new-tab="true"
    />
    <CmkLinkCard
      :title="_t('Discover best practices')"
      :subtitle="
        _t(
          'Explore proven best practices, helpful tips, and practical tricks to get the most out of your monitoring setup.'
        )
      "
      :url="cards.checkmk_best_practices"
      variant="borderless"
      :open-in-new-tab="true"
    />
    <CmkLinkCard
      :title="_t('Learn Checkmk via expert training')"
      :subtitle="
        _t(
          'Build a solid foundation and deepen your knowledge in our official, instructor-led Checkmk trainings.'
        )
      "
      :url="cards.checkmk_trainings"
      variant="borderless"
      :open-in-new-tab="true"
    />
    <CmkLinkCard
      :title="_t('Attend a free webinar')"
      :subtitle="
        _t('Watch our on-demand or live webinars to master the configuration and use of Checkmk.')
      "
      :url="cards.checkmk_webinars"
      variant="borderless"
      :open-in-new-tab="true"
    />
    <CmkLinkCard
      :title="_t('Join the community')"
      :subtitle="_t('Connect with other users and ask questions in our active forum.')"
      :url="cards.checkmk_forum"
      variant="borderless"
      :open-in-new-tab="true"
    />
    <CmkLinkCard
      :title="_t('Ask Checkmk AI')"
      :subtitle="_t('Your assistant for Checkmk - ask anything from setup to troubleshooting.')"
      :url="cards.checkmk_ai"
      variant="borderless"
      :open-in-new-tab="true"
    />
  </CmkLinkCardContainer>
</template>
