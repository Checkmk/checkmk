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
    {{ _t('Further topics') }}
  </CmkHeading>
  <CmkSpace />
  <CmkLinkCardContainer class="welcome-next-steps">
    <CmkLinkCard
      :title="
        _t('Structure hosts with folders, labels, tags, parent relationships, and host groups')
      "
      :subtitle="
        _t('Organize your hosts to enable clear, scalable, and easy to manage monitoring.')
      "
      icon-name="hostgroups"
      borders="borderless"
      contrast="high"
      :url="cards.setup_folder_structure"
      :open-in-new-tab="true"
    />

    <CmkLinkCard
      :title="_t('Set up backup')"
      :subtitle="
        _t('No backup, no mercy! Protect your configuration and data with automated backups.')
      "
      icon-name="backup"
      :url="cards.setup_backup"
      borders="borderless"
      contrast="high"
      :open-in-new-tab="false"
    />
    <CmkLinkCard
      :title="_t('Learn how to scale your monitoring')"
      :subtitle="_t('Add more hosts, sites, or distributed setups as your environment grows.')"
      icon-name="sites"
      :url="cards.scale_monitoring"
      borders="borderless"
      contrast="high"
      :open-in-new-tab="true"
    />
    <CmkLinkCard
      :title="_t('Fine-tune your monitoring')"
      :subtitle="
        _t(
          'Dive deep into the details and learn how to optimize checks, thresholds, and notifications.'
        )
      "
      icon-name="rulesets"
      :url="cards.fine_tune_monitoring"
      borders="borderless"
      contrast="high"
      :open-in-new-tab="true"
    />
    <CmkLinkCard
      v-if="cards.license_site"
      :title="_t('License your site')"
      :subtitle="
        _t(
          'It’s time to enjoy the full experience! Set up automated licensing for a smooth experience.'
        )
      "
      icon-name="licensing"
      :url="cards.license_site"
      borders="borderless"
      contrast="high"
      :open-in-new-tab="false"
    />
    <CmkLinkCard
      :title="_t('Choose a different start page')"
      :subtitle="
        _t(
          'Use the \'Start URL to display in main frame\' option in your profile to define which page, dashboard or custom URL is shown when you log in.'
        )
      "
      icon-name="users"
      :url="cards.start_page"
      borders="borderless"
      contrast="high"
      :open-in-new-tab="false"
    />
  </CmkLinkCardContainer>
</template>

<style scoped>
.welcome-next-steps {
  margin-bottom: 56px;
}
</style>
