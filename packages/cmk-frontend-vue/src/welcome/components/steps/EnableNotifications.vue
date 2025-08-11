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
import CmkWizardStep from '@/components/CmkWizard/CmkWizardStep.vue'
import CmkWizard from '@/components/CmkWizard/CmkWizard.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'

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
    :info="t('time', '5-7 min')"
  >
    <StepParagraph>
      {{
        t(
          'paragraph',
          'Notifications help you to stay on top of problems without having to constantly check the interface. ' +
            'In Checkmk, they are rule-based, enabling you to create a notification system that evolves alongside ' +
            'your environment.'
        )
      }}
    </StepParagraph>

    <CmkWizard mode="overview">
      <CmkWizardStep>
        <template #header>
          <CmkHeading type="h3">{{ t('stage-0-title', 'Create a notification rule') }}</CmkHeading>
        </template>
        <template #content>
          <StepParagraph>
            {{
              t(
                'stage-0-instruction-1',
                'Follow the step-by-step guide in Setup > Notifications to set up notification rules.'
              )
            }}
          </StepParagraph>
          <StepCardsRow>
            <CmkLinkCard
              icon-name="notifications"
              :title="t('add-notification-rule', 'Add notification rule')"
              :url="urls.add_notification_rule"
              :open-in-new-tab="false"
            />
          </StepCardsRow>
        </template>
      </CmkWizardStep>

      <CmkWizardStep>
        <template #header>
          <CmkHeading type="h3">{{ t('stage-1-title', 'Send a test notification') }}</CmkHeading>
        </template>
        <template #content>
          <StepParagraph>
            {{
              t(
                'stage-1-instruction-1',
                'After creation, test your notification rule to make sure alerts reach you the way you expect.'
              )
            }}
          </StepParagraph>
          <StepCardsRow>
            <CmkLinkCard
              icon-name="analysis"
              :title="t('test-notifications', 'Test notifications')"
              :url="urls.test_notifications"
              :open-in-new-tab="false"
            />
          </StepCardsRow>
        </template>
      </CmkWizardStep>
    </CmkWizard>
  </CmkAccordionStepPanelItem>
</template>
