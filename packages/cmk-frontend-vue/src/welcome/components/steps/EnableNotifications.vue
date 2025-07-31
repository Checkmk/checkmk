<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { WelcomeUrls } from 'cmk-shared-typing/typescript/welcome'
import CmkLinkCard from '@/components/CmkLinkCard.vue'
import usei18n from '@/lib/i18n.ts'
import StepCardsRow from '@/welcome/components/steps/components/StepCardsRow.vue'
import CmkAccordionStepPanelItem from '@/components/CmkAccordionStepPanel/CmkAccordionStepPanelItem.vue'
import StepParagraph from '@/welcome/components/steps/components/StepParagraph.vue'
import StepHeading from '@/welcome/components/steps/components/StepHeading.vue'

const { t } = usei18n('welcome-step-4')

defineProps<{
  step: number
  urls: WelcomeUrls
  accomplished: boolean
}>()
</script>

<template>
  <CmkAccordionStepPanelItem
    :step="step"
    :disabled="false"
    :accomplished="accomplished"
    :title="t('title', 'Enable notifications')"
    :info="t('time', '10-15 min')"
  >
    <StepParagraph>
      {{
        t(
          'paragraph',
          'Notifications help you stay on top of problems ' +
            'without constantly checking the interface. ' +
            'Start by configuring contact groups, time periods, and host groups ' +
            'to define who should be notified and when. ' +
            'Then, add a notification rule and use the test feature ' +
            'to make sure alerts reach you the way you expect.'
        )
      }}
    </StepParagraph>

    <StepHeading>
      {{ t('prepare', 'Prepare') }}
    </StepHeading>
    <StepCardsRow>
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
    </StepCardsRow>

    <StepHeading>
      {{ t('setup-up-notifications', 'Set up notifications') }}
    </StepHeading>
    <StepCardsRow>
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
    </StepCardsRow>
  </CmkAccordionStepPanelItem>
</template>
