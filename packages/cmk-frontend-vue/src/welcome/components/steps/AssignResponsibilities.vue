<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { WelcomeUrls } from 'cmk-shared-typing/typescript/welcome'
import usei18n from '@/lib/i18n.ts'
import CmkAccordionStepPanelItem from '@/components/CmkAccordionStepPanel/CmkAccordionStepPanelItem.vue'
import StepParagraph from '@/welcome/components/steps/components/StepParagraph.vue'
import CmkWizardStep from '@/components/CmkWizard/CmkWizardStep.vue'
import CmkLinkCard from '@/components/CmkLinkCard.vue'
import CmkWizard from '@/components/CmkWizard/CmkWizard.vue'
import StepCardsRow from '@/welcome/components/steps/components/StepCardsRow.vue'
import CmkHeading from '@/components/typography/CmkHeading.vue'

const { _t } = usei18n()

const props = defineProps<{
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
    :title="_t('Assign responsibilities')"
    :info="_t('5-7 min')"
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

    <CmkWizard mode="overview">
      <CmkWizardStep>
        <template #header>
          <CmkHeading type="h3">{{ _t('Create a contact group') }}</CmkHeading>
        </template>
        <template #content>
          <StepParagraph>
            {{ _t('On default, there is one contact group available "Everything".') }}
            <br />
            {{ _t('Go to Setup > Users > Contact groups to create or edit contact groups.') }}
          </StepParagraph>
          <StepCardsRow>
            <CmkLinkCard
              icon-name="contactgroups"
              :title="_t('Contact groups')"
              :url="props.urls.create_contactgroups"
              :open-in-new-tab="false"
            />
          </StepCardsRow>
        </template>
      </CmkWizardStep>

      <CmkWizardStep>
        <template #header>
          <CmkHeading type="h3">{{ _t('Assign users to a contact group') }}</CmkHeading>
        </template>
        <template #content>
          <StepParagraph>
            {{
              _t(
                'Each user can belong to multiple contact groups. You can assign them to contact groups in the "Contact groups" section when editing or creating a user'
              )
            }}
          </StepParagraph>
          <StepCardsRow>
            <CmkLinkCard
              icon-name="users"
              :title="_t('Users')"
              :url="props.urls.users"
              :open-in-new-tab="false"
            />
          </StepCardsRow>
        </template>
      </CmkWizardStep>

      <CmkWizardStep>
        <template #header>
          <CmkHeading type="h3">{{ _t('Assign the contact group to hosts') }}</CmkHeading>
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
              :url="props.urls.assign_host_to_contactgroups"
              :open-in-new-tab="false"
            />
          </StepCardsRow>
        </template>
      </CmkWizardStep>

      <CmkWizardStep>
        <template #header>
          <CmkHeading type="h3">{{ _t('Activate changes') }}</CmkHeading>
        </template>
        <template #content>
          <StepCardsRow>
            <CmkLinkCard
              icon-name="main_changes"
              :title="_t('Activate changes')"
              :url="props.urls.activate_changes"
              :open-in-new-tab="false"
            />
          </StepCardsRow>
        </template>
      </CmkWizardStep>
    </CmkWizard>
  </CmkAccordionStepPanelItem>
</template>
