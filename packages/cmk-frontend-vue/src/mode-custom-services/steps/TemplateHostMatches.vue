<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAlert from 'cmk-ui-library/components/CmkAlert.vue'
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkParagraph from 'cmk-ui-library/components/typography/CmkParagraph.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'

import type { TemplatePreview } from '../templatePreview'

const { _t, _tn } = usei18n()

const { preview } = defineProps<{
  preview: TemplatePreview
}>()

const emit = defineEmits<{
  refresh: []
}>()
</script>

<template>
  <div class="mode-custom-services-template-host-matches">
    <div class="mode-custom-services-template-host-matches__header">
      <span class="mode-custom-services-template-host-matches__label" aria-live="polite"
        >{{ _t('Matching hosts') }}
        <template v-if="preview.status === 'resolved'"
          >({{ preview.resolution.matching_hosts.length }})</template
        ></span
      >
      <CmkButton
        variant="optional"
        size="small"
        :disabled="preview.status === 'idle' || preview.status === 'loading'"
        @click="emit('refresh')"
        >{{ _t('Refresh') }}</CmkButton
      >
    </div>
    <CmkParagraph
      v-if="preview.status === 'idle'"
      class="mode-custom-services-template-host-matches__note"
      >{{ _t('Enter a host name template to see the hosts it matches.') }}</CmkParagraph
    >
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
          preview.resolution.hidden_match_count === 0 &&
          !preview.resolution.truncated
        "
        size="small"
        variant="warning"
        :text="
          _t('No configured host currently matches this template, so the service cannot be saved.')
        "
      />
      <ul
        v-if="preview.resolution.matching_hosts.length > 0"
        class="mode-custom-services-template-host-matches__host-list"
      >
        <li
          v-for="host in preview.resolution.matching_hosts"
          :key="host"
          class="mode-custom-services-template-host-matches__host"
        >
          {{ host }}
        </li>
      </ul>
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
            'The metric has too many attribute combinations to look them all up, so this list is incomplete. Saving is refused until the attribute filter narrows them down.'
          )
        "
      />
      <template v-if="preview.resolution.unmatched_host_names.length > 0">
        <span class="mode-custom-services-template-host-matches__label"
          >{{ _t('Resolved names without a configured host') }} ({{
            preview.resolution.unmatched_host_names.length
          }})</span
        >
        <ul class="mode-custom-services-template-host-matches__host-list">
          <li
            v-for="name in preview.resolution.unmatched_host_names"
            :key="name"
            class="mode-custom-services-template-host-matches__host mode-custom-services-template-host-matches__host--unmatched"
          >
            {{ name }}
          </li>
        </ul>
      </template>
    </template>
  </div>
</template>

<style scoped>
.mode-custom-services-template-host-matches {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
}

.mode-custom-services-template-host-matches__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--dimension-3);
}

.mode-custom-services-template-host-matches__label {
  font-weight: bold;
  font-size: var(--font-size-small);
}

.mode-custom-services-template-host-matches__note {
  font-size: var(--font-size-small);
}

.mode-custom-services-template-host-matches__host-list {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-2);
  max-height: 200px;
  margin: 0;
  padding: 0;
  overflow-y: auto;
  list-style: none;
}

.mode-custom-services-template-host-matches__host {
  font-family: monospace;
  font-size: var(--font-size-small);
}

.mode-custom-services-template-host-matches__host--unmatched {
  opacity: 0.6;
}
</style>
