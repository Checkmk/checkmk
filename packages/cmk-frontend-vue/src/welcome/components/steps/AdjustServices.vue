<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { WelcomeCards } from 'cmk-shared-typing/typescript/welcome'
import type { Ref } from 'vue'

import usei18n from '@/lib/i18n'
import usePersistentRef from '@/lib/usePersistentRef.ts'

import CmkAccordionStepPanelItem from '@/components/CmkAccordionStepPanel/CmkAccordionStepPanelItem.vue'
import CmkHelpText from '@/components/CmkHelpText.vue'
import CmkIcon from '@/components/CmkIcon'
import CmkLinkCard from '@/components/CmkLinkCard'
import CmkWizard, { CmkWizardButton, CmkWizardStep } from '@/components/CmkWizard'
import CmkHeading from '@/components/typography/CmkHeading.vue'

import StepCardsRow from '@/welcome/components/steps/components/StepCardsRow.vue'
import StepParagraph from '@/welcome/components/steps/components/StepParagraph.vue'
import { type StepId } from '@/welcome/components/steps/utils.ts'

const { _t } = usei18n()

const props = defineProps<{
  step: number
  stepId: StepId
  cards: WelcomeCards
  accomplished: boolean
}>()
const emit = defineEmits(['step-completed'])

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
    :title="_t('Adjust services')"
    :info="_t('5-7 min')"
  >
    <StepParagraph>
      {{
        _t(
          `Each service in Checkmk comes with default parameter values.
            You can customize these to match your monitoring needs,
            most commonly by setting thresholds for WARN and CRIT states using rules.
            To find the right ruleset for a service,
            start with the Service discovery page of a host.`
        )
      }}
    </StepParagraph>

    <CmkWizard v-model="currentStep" mode="guided">
      <CmkWizardStep :index="0" :is-completed="() => currentStep >= 0">
        <template #header>
          <CmkHeading type="h3">{{ _t('Run a service discovery') }}</CmkHeading>
        </template>
        <template #content>
          <StepParagraph>
            {{ _t('To adjust parameters for a host, start by running a service discovery.') }}
            <br />
            {{ _t('In the host table, click on the') }}
            <CmkIcon name="services" variant="inline" size="small" />{{
              _t('-icon next to the host to open the service discovery.')
            }}
          </StepParagraph>
          <StepCardsRow>
            <CmkLinkCard
              icon-name="folder"
              :title="_t('View host table')"
              :url="cards.setup_hosts"
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
          <CmkHeading type="h3">{{ _t('Open the ruleset for a check parameter') }}</CmkHeading>
        </template>
        <template #content>
          <StepParagraph>
            {{ _t('In the Service Discovery view, find the service you want to configure.') }}
            <br />
            {{ _t('Click the') }}
            <CmkIcon name="check-parameters" variant="inline" size="small" />{{
              _t('-icon next to it to open the corresponding ruleset.')
            }}
            <CmkHelpText
              :help="
                _t(
                  'This icon is only visible after the service has been added to monitoring and is listed under <b>Monitored services</b>'
                )
              "
            />
          </StepParagraph>
        </template>
        <template #actions>
          <CmkWizardButton type="next" />
          <CmkWizardButton type="previous" />
        </template>
      </CmkWizardStep>

      <CmkWizardStep :index="2" :is-completed="() => currentStep >= 2">
        <template #header>
          <CmkHeading type="h3">{{ _t('Create a check parameter rule') }}</CmkHeading>
        </template>
        <template #content>
          <StepParagraph>
            {{
              _t(
                'In the ruleset view, click Add rule for current host to create a rule that applies specifically to the selected host.'
              )
            }}
            <br />
            {{
              _t('You can now define custom parameters like thresholds or other check settings.')
            }}
          </StepParagraph>
        </template>
        <template #actions>
          <CmkWizardButton type="next" />
          <CmkWizardButton type="previous" />
        </template>
      </CmkWizardStep>

      <CmkWizardStep :index="3" :is-completed="() => currentStep >= 3">
        <template #header>
          <CmkHeading type="h3">{{ _t('Activate changes') }}</CmkHeading>
        </template>
        <template #content>
          <StepParagraph>
            {{
              _t(
                `Changes are saved in a temporary environment first,
                letting you review and adjust them safely.`
              )
            }}
            <br />
            {{ _t('Activate changes to apply them to live monitoring.') }}
          </StepParagraph>
          <StepCardsRow>
            <CmkLinkCard
              icon-name="main-changes"
              :title="_t('Activate changes')"
              :url="cards.activate_changes"
              :open-in-new-tab="false"
            />
          </StepCardsRow>
        </template>
        <template #actions>
          <CmkWizardButton
            v-if="!accomplished && stepId"
            type="finish"
            :override-label="_t('Mark as complete')"
            @click="emit('step-completed', stepId)"
          />
          <CmkWizardButton type="previous" />
        </template>
      </CmkWizardStep>
    </CmkWizard>
  </CmkAccordionStepPanelItem>
</template>
