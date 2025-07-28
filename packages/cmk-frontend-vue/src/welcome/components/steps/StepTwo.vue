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

const { t } = usei18n('welcome-step-2')

defineProps<{
  urls: WelcomeUrls
  accomplished: boolean
}>()
</script>

<template>
  <CmkAccordionStepPanelItem
    :step="2"
    :disabled="false"
    :accomplished="accomplished"
    :title="t('title', 'Add your first host')"
    :info="t('time', '2-5 min')"
  >
    <StepParagraph>
      {{
        t(
          'text',
          `Each host includes a number of services that represent what you want to monitor, for example,
  CPU usage, disk space, running processes, or hardware sensors. Checkmk makes this easy with the
  Service Discovery, which automatically detects relevant services on your host, so you can start
  monitoring with minimal setup.`
        )
      }}
    </StepParagraph>

    <StepHeading>
      {{ t('on-premise-hosts', 'On-premise-hosts') }}
    </StepHeading>
    <StepCardsRow>
      <CmkLinkCard
        icon-name="folder"
        :title="t('add-host', 'Add host')"
        :url="urls.add_host"
        :open-in-new-tab="false"
      />
      <CmkLinkCard
        icon-name="networking"
        :title="t('network-devices', 'Network devices and SNMP')"
        :url="urls.network_devices"
        :open-in-new-tab="false"
      />
    </StepCardsRow>

    <StepHeading>
      {{ t('cloud-hosts', 'Cloud hosts') }}
    </StepHeading>
    <StepCardsRow>
      <CmkLinkCard
        icon-name="aws-logo"
        :title="t('aws', 'Amazon Web Services (AWS)')"
        :url="urls.aws_quick_setup"
        :open-in-new-tab="false"
      />
      <CmkLinkCard
        icon-name="azure-vms"
        :title="t('azure', 'Microsoft Azure')"
        :url="urls.azure_quick_setup"
        :open-in-new-tab="false"
      />
      <CmkLinkCard
        icon-name="gcp"
        :title="t('gcp', 'Google Cloud Platform (GCP)')"
        :url="urls.gcp_quick_setup"
        :open-in-new-tab="false"
      />
    </StepCardsRow>

    <template v-if="urls.synthetic_monitoring || urls.opentelemetry">
      <StepHeading>
        {{ t('application-monitoring', 'Application monitoring') }}
      </StepHeading>
      <StepCardsRow>
        <CmkLinkCard
          v-if="urls.synthetic_monitoring"
          icon-name="synthetic-monitoring-yellow"
          :title="t('synthetic-monitoring', 'Synthetic monitoring')"
          :url="urls.synthetic_monitoring"
          :open-in-new-tab="false"
        />
        <CmkLinkCard
          v-if="urls.opentelemetry"
          icon-name="opentelemetry"
          :title="t('otel', 'OpenTelemetry (Beta)')"
          :url="urls.opentelemetry"
          :open-in-new-tab="false"
        />
      </StepCardsRow>
    </template>
  </CmkAccordionStepPanelItem>
</template>
