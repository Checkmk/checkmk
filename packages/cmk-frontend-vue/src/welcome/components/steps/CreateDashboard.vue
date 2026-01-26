<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { WelcomeCards } from 'cmk-shared-typing/typescript/welcome'
import type { Ref } from 'vue'

import usei18n from '@/lib/i18n'
import usePersistentRef from '@/lib/usePersistentRef'

import CmkAccordionStepPanelItem from '@/components/CmkAccordionStepPanel/CmkAccordionStepPanelItem.vue'
import CmkLinkCard from '@/components/CmkLinkCard'
import CmkWizard, { CmkWizardButton, CmkWizardStep } from '@/components/CmkWizard'
import CmkHeading from '@/components/typography/CmkHeading.vue'

import StepCardsRow from '@/welcome/components/steps/components/StepCardsRow.vue'
import StepParagraph from '@/welcome/components/steps/components/StepParagraph.vue'

import type { StepId } from './utils'

const { _t } = usei18n()

const props = defineProps<{
  step: number
  stepId: StepId
  cards: WelcomeCards
  accomplished: boolean
}>()

const currentStep: Ref<number> = usePersistentRef<number>(
  `${props.stepId}-currentStep`,
  0,
  (v) => v as number,
  'local'
)
</script>

<template>
  <CmkAccordionStepPanelItem
    :step="step"
    :disabled="false"
    :accomplished="accomplished"
    :title="_t('Create a dashboard')"
    :info="_t('2 Steps | Takes 7-10 min')"
  >
    <StepParagraph>
      {{
        _t(
          `Tailor your monitoring experience by creating a custom dashboard
            that highlights what matters most to you.
            Whether you want to track specific hosts, services, or metrics,
            dashboards help you stay focused and efficient.
            You can create your own or explore the list of all dashboards to find useful presets.`
        )
      }}
    </StepParagraph>

    <CmkWizard v-model="currentStep" mode="guided">
      <CmkWizardStep :index="0" :is-completed="() => currentStep >= 0">
        <template #header>
          <CmkHeading type="h3">{{ _t('Explore the Checkmk built-in dashboards') }}</CmkHeading>
        </template>
        <template #content>
          <StepParagraph>
            {{
              _t(
                'Explore all of the built-in dashboards available in Checkmk. You can also clone and modify them to suit your needs.'
              )
            }}
          </StepParagraph>
          <StepCardsRow>
            <CmkLinkCard
              icon-name="dashboard"
              :title="_t('View list of all dashboards')"
              :url="cards.all_dashboards"
              :open-in-new-tab="false"
            />
          </StepCardsRow>
        </template>
        <template #actions>
          <CmkWizardButton type="next" :override-label="_t('Continue')" />
        </template>
      </CmkWizardStep>

      <CmkWizardStep :index="1" :is-completed="() => currentStep >= 1">
        <template #header>
          <CmkHeading type="h3">{{ _t('Create your own custom dashboard') }}</CmkHeading>
        </template>
        <template #content>
          <StepParagraph>
            {{
              _t(
                "Now it's time to create your own customized dashboard so you can see what matters at a glance."
              )
            }}
          </StepParagraph>
          <StepCardsRow>
            <CmkLinkCard
              icon-name="new"
              :title="_t('Add custom dashboard')"
              :url="cards.add_custom_dashboard"
              :open-in-new-tab="false"
            />
          </StepCardsRow>
        </template>
        <template #actions>
          <CmkWizardButton type="previous" />
        </template>
      </CmkWizardStep>
    </CmkWizard>
  </CmkAccordionStepPanelItem>
</template>
