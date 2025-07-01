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
import type { WelcomeUrls } from 'cmk-shared-typing/typescript/welcome'

const { t } = usei18n('next-steps')

defineProps<{
  urls: WelcomeUrls
}>()
</script>

<template>
  <CmkHeading2>
    {{ t('whats-next', "What's next?") }}
  </CmkHeading2>
  <CmkSpace />
  <CmkLinkCard
    :title="t('create-contact-groups', 'Create contact groups')"
    :subtitle="
      t(
        'create-contact-groups-subtitle',
        'Streamline responsibilities to ensure that the right people receive relevant alerts and access.'
      )
    "
    icon-name="contactgroups"
    :url="urls.create_contactgoups"
    variant="borderless"
    :open-in-new-tab="false"
  />
  <CmkLinkCard
    :title="t('setup-backup', 'Set up backup')"
    :subtitle="
      t(
        'setup-backup-subtitle',
        'No backup, no mercy! Protect your configuration and data with automated backups.'
      )
    "
    icon-name="backup"
    :url="urls.setup_backup"
    variant="borderless"
    :open-in-new-tab="false"
  />
  <CmkLinkCard
    :title="t('scale-monitoring', 'Scale your monitoring')"
    :subtitle="
      t(
        'scale-monitoring-subtitle',
        'Add more hosts, sites, or distributed setups as your environment grows.'
      )
    "
    icon-name="sites"
    :url="urls.scale_monitoring"
    variant="borderless"
    :open-in-new-tab="true"
  />
  <CmkLinkCard
    :title="t('fine-tune', 'Fine-tune your monitoring')"
    :subtitle="
      t(
        'fine-tune-subtitle',
        'Dive deep into the details and learn how to optimize checks, thresholds, and notifications.'
      )
    "
    icon-name="rulesets"
    :url="urls.fine_tune_monitoring"
    variant="borderless"
    :open-in-new-tab="true"
  />
  <CmkLinkCard
    :title="t('license', 'License your site')"
    :subtitle="
      t(
        'license-subtitle',
        'It’s time to enjoy the full experience! Set up automated licensing for a smooth experience.'
      )
    "
    icon-name="licensing"
    :url="urls.license_site"
    variant="borderless"
    :open-in-new-tab="false"
  />
</template>

<style scoped></style>
