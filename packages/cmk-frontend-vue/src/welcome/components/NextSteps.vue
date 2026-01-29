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
      :url="cards.setup_backup"
      variant="borderless"
      :open-in-new-tab="false"
    />
    <CmkLinkCard
      :title="_t('Learn how to scale your monitoring')"
      :subtitle="_t('Add more hosts, sites, or distributed setups as your environment grows.')"
      icon-name="sites"
      :url="cards.scale_monitoring"
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
      :url="cards.fine_tune_monitoring"
      variant="borderless"
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
      variant="borderless"
      :open-in-new-tab="false"
    />
  </CmkLinkCardContainer>
</template>

<style scoped>
/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.next-link-card-container {
  margin-bottom: 56px;
}
</style>
