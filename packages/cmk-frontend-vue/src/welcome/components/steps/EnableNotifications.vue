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
import { ref } from 'vue'
import CmkWizardButton from '@/components/CmkWizard/CmkWizardButton.vue'
import { markStepAsComplete, type StepId } from '@/welcome/components/steps/utils.ts'

const { _t } = usei18n()

defineProps<{
  step: number
  stepId: StepId
  urls: WelcomeUrls
  accomplished: boolean
}>()

const currentStep = ref(0)
</script>

<template>
  <CmkAccordionStepPanelItem
    :step="step"
    :disabled="false"
    :accomplished="accomplished"
    :title="_t('Enable notifications')"
    :info="_t('5-7 min')"
  >
    <StepParagraph>
      {{
        _t(
          `Notifications help you to stay on top of problems without having to constantly check the interface.
            In Checkmk, they are rule-based, enabling you to create a notification system that evolves alongside
            your environment.`
        )
      }}
    </StepParagraph>

    <CmkWizard v-model="currentStep" mode="guided">
      <CmkWizardStep :index="0" :is-completed="() => currentStep >= 0">
        <template #header>
          <CmkHeading type="h3">{{ _t('Create a notification rule') }}</CmkHeading>
        </template>
        <template v-if="currentStep === 0" #content>
          <StepParagraph>
            {{
              _t(
                'Follow the step-by-step guide in Setup > Notifications to set up notification rules.'
              )
            }}
          </StepParagraph>
          <StepCardsRow>
            <CmkLinkCard
              icon-name="notifications"
              :title="_t('Add notification rule')"
              :url="urls.add_notification_rule"
              :open-in-new-tab="false"
            />
          </StepCardsRow>
        </template>
        <template #actions>
          <CmkWizardButton type="next" />
        </template>
      </CmkWizardStep>

      <CmkWizardStep :index="1" :is-completed="() => currentStep >= 1">
        <template #header>
          <CmkHeading type="h3">{{ _t('Send a test notification') }}</CmkHeading>
        </template>
        <template v-if="currentStep === 1" #content>
          <StepParagraph>
            {{
              _t(
                'After creation, test your notification rule to make sure alerts reach you the way you expect.'
              )
            }}
          </StepParagraph>
          <StepCardsRow>
            <CmkLinkCard
              icon-name="analysis"
              :title="_t('Test notifications')"
              :url="urls.test_notifications"
              :open-in-new-tab="false"
            />
          </StepCardsRow>
        </template>
        <template #actions>
          <CmkWizardButton
            v-if="!accomplished && stepId"
            type="finish"
            :override-label="_t('Mark as complete')"
            @click="markStepAsComplete(urls.mark_step_completed, stepId)"
          />
          <CmkWizardButton type="previous" />
        </template>
      </CmkWizardStep>
    </CmkWizard>
  </CmkAccordionStepPanelItem>
</template>
