<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAlert from 'cmk-ui-library/components/CmkAlert.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import type { HostNameTemplateResolution } from '../definition'
import type { OpenTelemetryData } from '../openTelemetryData'
import type { TemplatePreview } from '../templatePreview'
import OpenTelemetryDataNotice from './OpenTelemetryDataNotice.vue'

const { _t, _tn } = usei18n()

const { preview, opentelemetryData = { status: 'idle' } } = defineProps<{
  preview: TemplatePreview
  opentelemetryData?: OpenTelemetryData
}>()

function hostCreationRefused(
  refusal: HostNameTemplateResolution['host_creation_refusal']
): TranslatedString {
  switch (refusal) {
    case 'missing_permission':
      return _t(
        'You may not create hosts: you lack the permission "Add & remove hosts". Saving is refused while the template resolves to new hosts.'
      )
    case 'no_write_access':
      return _t(
        'You may not create hosts in any folder: you have neither "Write access to all hosts and folders" nor membership in a contact group permitted on a folder. Saving is refused while the template resolves to new hosts.'
      )
    case 'hosts_locked':
      return _t(
        'You may not create hosts in any folder: the hosts are locked in every folder you may write to. Saving is refused while the template resolves to new hosts.'
      )
    default:
      return _t(
        'You may not create hosts in any folder. Saving is refused while the template resolves to new hosts.'
      )
  }
}
</script>

<template>
  <div class="mode-custom-services-template-host-matches" aria-live="polite">
    <span v-if="preview.status === 'idle'">{{
      _t('Enter a host name template to see the hosts it matches.')
    }}</span>
    <CmkAlert
      v-else-if="preview.status === 'loading'"
      size="small"
      variant="loading"
      :text="_t('Looking up the matching hosts…')"
    />
    <CmkAlert
      v-else-if="preview.status === 'failed' || preview.status === 'refused'"
      size="small"
      variant="error"
      :text="untranslated(preview.error)"
    />
    <template v-else>
      <CmkAlert
        v-if="
          preview.resolution.matching_hosts.length === 0 &&
          preview.resolution.unmatched_host_names.length === 0 &&
          preview.resolution.hidden_match_count === 0 &&
          !preview.resolution.truncated
        "
        size="small"
        variant="warning"
        :text="
          _t('This template currently resolves to no host name, so the service cannot be saved.')
        "
      />
      <template v-if="preview.resolution.matching_hosts.length > 0">
        <span
          >{{ _t('Target hosts:') }}
          <strong>{{ preview.resolution.matching_hosts.join(', ') }}</strong></span
        >
        <OpenTelemetryDataNotice :data="opentelemetryData" />
      </template>
      <span v-if="preview.resolution.unmatched_host_names.length > 0"
        >{{ _t('New hosts, created on saving:') }}
        <strong>{{ preview.resolution.unmatched_host_names.join(', ') }}</strong></span
      >
      <CmkAlert
        v-if="
          preview.resolution.unmatched_host_names.length > 0 &&
          preview.resolution.creatable_folders.length === 0
        "
        size="small"
        variant="warning"
        :text="hostCreationRefused(preview.resolution.host_creation_refusal)"
      />
      <CmkAlert
        v-if="preview.resolution.hidden_match_count > 0"
        size="small"
        variant="warning"
        :text="
          _tn(
            '%{n} matching host is in a folder you may not see. Saving is refused while the template matches it.',
            '%{n} matching hosts are in folders you may not see. Saving is refused while the template matches them.',
            preview.resolution.hidden_match_count,
            { n: preview.resolution.hidden_match_count }
          )
        "
      />
      <CmkAlert
        v-if="preview.resolution.truncated"
        size="small"
        variant="warning"
        :text="
          _t(
            'The metric has too many attribute combinations to look them all up, so the target hosts may be incomplete. Saving is refused until the attribute filter narrows them down.'
          )
        "
      />
    </template>
  </div>
</template>

<style scoped>
.mode-custom-services-template-host-matches {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-2);
  overflow-wrap: anywhere;
}
</style>
