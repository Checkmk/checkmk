<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { WelcomeUrls } from 'cmk-shared-typing/typescript/welcome'
import CmkLinkCard from '@/components/CmkLinkCard.vue'
import CmkBodyText from '@/components/typography/CmkBodyText.vue'
import usei18n from '@/lib/i18n.ts'
import FlexRow from '@/welcome/components/steps/FlexRow.vue'
import CmkAccordionStepPanelItem from '@/components/CmkAccordionStepPanel/CmkAccordionStepPanelItem.vue'
const { t } = usei18n('welcome-step-4')

defineProps<{
  urls: WelcomeUrls
  accomplished: boolean
}>()
</script>

<template>
  <CmkAccordionStepPanelItem
    :step="4"
    :disabled="false"
    :accomplished="accomplished"
    :title="t('title', 'Enable notifications')"
    :info="t('time', '10-15 min')"
  >
    <CmkBodyText class="margin-bottom">
      {{ t('text', 'TBD') }}
    </CmkBodyText>

    <b> {{ t('prepare', 'Prepare') }}</b>
    <FlexRow>
      <CmkLinkCard
        icon-name="contactgroups"
        :title="t('contact-groups', 'Contact groups')"
        :url="urls.create_contactgoups"
        :open-in-new-tab="false"
      />
      <CmkLinkCard
        icon-name="timeperiods"
        :title="t('time-periods', 'Time periods')"
        :url="urls.time_periods"
        :open-in-new-tab="false"
      />
      <CmkLinkCard
        icon-name="hostgroups"
        :title="t('hostgroups', 'Host groups')"
        :url="urls.host_groups"
        :open-in-new-tab="false"
      />
    </FlexRow>

    <b> {{ t('setup-up-notifications', 'Set up notifications') }}</b>
    <FlexRow>
      <CmkLinkCard
        icon-name="notifications"
        :title="t('add-notification-rule', 'Add notification rule')"
        :url="urls.add_notification_rule"
        :open-in-new-tab="false"
      />
      <CmkLinkCard
        icon-name="analysis"
        :title="t('test-notifications', 'Test notifications')"
        :url="urls.test_notifications"
        :open-in-new-tab="false"
      />
    </FlexRow>
  </CmkAccordionStepPanelItem>
</template>

<style scoped>
.margin-bottom {
  margin-bottom: var(--spacing);
}
</style>
