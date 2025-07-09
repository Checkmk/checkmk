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
const { t } = usei18n('welcome-step-2')

defineProps<{
  urls: WelcomeUrls
}>()
</script>

<template>
  <CmkAccordionStepPanelItem
    :step="2"
    :disabled="false"
    :accomplished="false"
    :title="t('title', 'Add your first host')"
    :info="t('time', '2-5 min')"
  >
    <CmkBodyText class="margin-bottom">
      {{
        t(
          'text',
          `Each host includes a number of services that represent what you want to monitor, for example,
  CPU usage, disk space, running processes, or hardware sensors. Checkmk makes this easy with the
  Service Discovery, which automatically detects relevant services on your host, so you can start
  monitoring with minimal setup.`
        )
      }}
    </CmkBodyText>

    <b> {{ t('on-premise-hosts', 'On-premise-hosts') }}</b>
    <FlexRow>
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
    </FlexRow>

    <b> {{ t('cloud-hosts', 'Cloud hosts') }}</b>
    <FlexRow>
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
    </FlexRow>

    <b> {{ t('application-monitoring', 'Application monitoring') }}</b>
    <FlexRow>
      <CmkLinkCard
        icon-name="synthetic-monitoring-yellow"
        :title="t('synthetic-monitoring', 'Synthetic monitoring')"
        :url="urls.synthetic_monitoring"
        :open-in-new-tab="false"
      />
      <CmkLinkCard
        icon-name="opentelemetry"
        :title="t('otel', 'OpenTelemetry (Beta)')"
        :url="urls.opentelemetry"
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
