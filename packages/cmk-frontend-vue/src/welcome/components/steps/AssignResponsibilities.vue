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
    :title="_t('Assign responsibilities with contact groups')"
    :info="_t('3 Steps | Takes 5-7 min')"
  >
    <StepParagraph>
      {{
        _t(
          `The recommended way to manage responsibilities in Checkmk is by using contact groups.
            Contact groups can be assigned to users, hosts, and services, making them a flexible
            and scalable tool for defining who is responsible for what.`
        )
      }}
    </StepParagraph>

    <CmkWizard v-model="currentStep" mode="guided">
      <CmkWizardStep :index="0" :is-completed="() => currentStep >= 0">
        <template #header>
          <CmkHeading type="h3">{{ _t('Create a contact group') }}</CmkHeading>
        </template>
        <template #content>
          <StepParagraph>
            {{ _t('By default, there is one contact group available, called "Everything".') }}
            <br />
            {{ _t('Go to Setup > Users > Contact groups to create or edit contact groups.') }}
          </StepParagraph>
          <StepCardsRow>
            <CmkLinkCard
              icon-name="contactgroups"
              :title="_t('Contact groups')"
              :url="cards.create_contactgroups"
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
          <CmkHeading type="h3">{{ _t('Assign users to a contact group') }}</CmkHeading>
        </template>
        <template #content>
          <StepParagraph>
            {{
              _t(
                'Each user can belong to multiple contact groups. You can assign them to contact groups in the "Contact groups" section when editing or creating a user.'
              )
            }}
          </StepParagraph>
          <StepCardsRow>
            <CmkLinkCard
              icon-name="users"
              :title="_t('Users')"
              :url="cards.users"
              :open-in-new-tab="false"
            />
          </StepCardsRow>
        </template>
        <template #actions>
          <CmkWizardButton type="next" :override-label="_t('Continue')" />
          <CmkWizardButton type="previous" />
        </template>
      </CmkWizardStep>

      <CmkWizardStep :index="2" :is-completed="() => currentStep >= 2">
        <template #header>
          <CmkHeading type="h3">{{ _t('Assign hosts to a contact group') }}</CmkHeading>
        </template>
        <template #content>
          <StepParagraph>
            {{
              _t(
                'There are two options available for assigning hosts to contact groups. Either make a direct assignment when creating or editing hosts, or use a rule.'
              )
            }}
            <br />
            {{
              _t(
                'We recommend using the latter, as rules can adapt more easily to changes in your environment.'
              )
            }}
          </StepParagraph>
          <StepCardsRow>
            <CmkLinkCard
              icon-name="assign"
              :title="_t('Assignment of hosts to contact groups')"
              :url="cards.assign_host_to_contactgroups"
              :open-in-new-tab="false"
            />
          </StepCardsRow>
        </template>
        <template #actions>
          <CmkWizardButton
            v-if="!accomplished && stepId"
            type="finish"
            :override-label="_t('Mark as done')"
            @click="emit('step-completed', stepId)"
          />
          <CmkWizardButton type="previous" />
        </template>
      </CmkWizardStep>
    </CmkWizard>
  </CmkAccordionStepPanelItem>
</template>
