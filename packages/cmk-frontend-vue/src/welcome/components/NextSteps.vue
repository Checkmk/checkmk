<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { WelcomeUrls } from 'cmk-shared-typing/typescript/welcome'

import usei18n from '@/lib/i18n'

import CmkLinkCard from '@/components/CmkLinkCard.vue'
import CmkLinkCardContainer from '@/components/CmkLinkCardContainer.vue'
import CmkSpace from '@/components/CmkSpace.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'

const { _t } = usei18n()

defineProps<{
  urls: WelcomeUrls
}>()
</script>

<template>
  <CmkHeading type="h4">
    {{ _t("What's next?") }}
  </CmkHeading>
  <CmkSpace />
  <CmkLinkCardContainer class="next-link-card-container">
    <CmkLinkCard
      :title="_t('Set up backup')"
      :subtitle="
        _t('No backup, no mercy! Protect your configuration and data with automated backups.')
      "
      icon-name="backup"
      :url="urls.setup_backup"
      variant="borderless"
      :open-in-new-tab="false"
    />
    <CmkLinkCard
      :title="_t('Scale your monitoring')"
      :subtitle="_t('Add more hosts, sites, or distributed setups as your environment grows.')"
      icon-name="sites"
      :url="urls.scale_monitoring"
      variant="borderless"
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
      :url="urls.fine_tune_monitoring"
      variant="borderless"
      :open-in-new-tab="true"
    />
    <CmkLinkCard
      :title="_t('License your site')"
      :subtitle="
        _t(
          'It’s time to enjoy the full experience! Set up automated licensing for a smooth experience.'
        )
      "
      icon-name="licensing"
      :url="urls.license_site"
      variant="borderless"
      :open-in-new-tab="false"
    />
  </CmkLinkCardContainer>
</template>

<style scoped>
.next-link-card-container {
  margin-bottom: 56px;
}
</style>
