<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script lang="ts">
export const a11yData = [
  {
    keys: ['Tab'],
    description:
      'Reaches the dropdown, then each chosen value’s remove button - so a value can be taken back without disturbing the rest.'
  },
  {
    keys: ['↑', '↓'],
    description: 'Move between the offered values, including the entry echoing what has been typed.'
  },
  {
    keys: ['Enter'],
    description:
      'Takes the highlighted entry. Typing something the list does not know offers it as an entry of its own, so it can be taken the same way.'
  }
]
</script>

<script setup lang="ts">
import {
  UclDetailPageAccessibility,
  UclDetailPageComponent,
  UclDetailPageHeader,
  UclDetailPageLayout
} from '@ucl/_ucl/components/detail-page'
import { useMswWorker } from '@ucl/_ucl/composables/useMswWorker'
import {
  CmkFilterInputItem,
  type ConfiguredFilters,
  type FilterDefinitions,
  useProvideFilterDefinitions
} from 'cmk-ui-library/components/filter'
import { HttpResponse, http } from 'msw'
import { ref } from 'vue'

// Stands in for the autocompleter endpoint. The real one is a registered
// autocompleter ident resolved server-side; here the same request shape is
// answered from a fixed list so the picker behaves as it does in the product.
const APPLICATIONS = [
  'HTTP',
  'HTTPS',
  'TLS',
  'DNS',
  'SSH',
  'SMTP',
  'NTP',
  'QUIC',
  'BitTorrent',
  'Kerberos'
]

async function interceptor({ request }: { request: Request }) {
  // Never throw: msw turns a throwing resolver into a 500, which the
  // autocompleter reports as a bare "unknown error" - hiding the real cause.
  let query = ''
  try {
    const raw = new URLSearchParams(await request.text()).get('request')
    query = (raw === null ? '' : (JSON.parse(raw).value ?? '')) as string
  } catch {
    query = ''
  }
  const matching = APPLICATIONS.filter((name) => name.toLowerCase().includes(query.toLowerCase()))
  return HttpResponse.json({
    result: { choices: matching.map((name) => [name, name]), total: APPLICATIONS.length },
    result_code: 0,
    severity: 'success'
  })
}

const { mockLoaded } = useMswWorker([http.post(/ajax_vs_autocomplete\.py/, interceptor)])

defineProps<{ screenshotMode: boolean }>()

const DEFINITIONS: FilterDefinitions = {
  network_flow_application: {
    domainType: 'visual_filter',
    links: [],
    id: 'network_flow_application',
    title: 'Application',
    extensions: {
      info: 'host',
      group: null,
      is_show_more: false,
      components: [
        {
          component_type: 'multiselect_with_free_text',
          id: 'network_flow_application_value',
          separator: ',',
          pick_hint: 'Select an application...',
          autocompleter: { ident: 'network_flow_applications', params: {} }
        }
      ]
    }
  }
}

useProvideFilterDefinitions({ definitions: DEFINITIONS, groups: {} })

const configuredFilters = ref<ConfiguredFilters>({
  network_flow_application: { network_flow_application_value: 'TLS, HTTP' }
})
</script>

<template>
  <UclDetailPageLayout>
    <UclDetailPageHeader>MultiselectWithFreeText</UclDetailPageHeader>

    <UclDetailPageComponent>
      <span v-if="mockLoaded" class="ucl-multiselect-with-free-text-dev__stack">
        <div class="ucl-multiselect-with-free-text-dev__container">
          <CmkFilterInputItem
            filter-id="network_flow_application"
            :configured-filter-values="configuredFilters['network_flow_application'] ?? null"
            @update-filter-values="(id, values) => (configuredFilters[id] = values)"
          />
        </div>

        <p class="ucl-multiselect-with-free-text-dev__readout">
          Filter value:
          <code>{{
            configuredFilters['network_flow_application']?.['network_flow_application_value'] ||
            '(unset)'
          }}</code>
        </p>

        <p class="ucl-multiselect-with-free-text-dev__hint">
          For a filter whose values are open-ended - an address, an application name - where a list
          alone cannot express a value it does not know about, and free text alone makes the user
          guess at spelling. One input does both: a pick is appended to the chosen values, and
          anything the list does not know is simply typed in. The value stays a single
          separator-joined string, so a filter adopting this needs no change on the reading side.
        </p>
      </span>
    </UclDetailPageComponent>

    <UclDetailPageAccessibility :data="a11yData" />
  </UclDetailPageLayout>
</template>

<style scoped>
.ucl-multiselect-with-free-text-dev__stack {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
  width: 100%;
}

.ucl-multiselect-with-free-text-dev__container {
  width: 400px;
}

.ucl-multiselect-with-free-text-dev__readout,
.ucl-multiselect-with-free-text-dev__hint {
  margin: 0;
  font-style: italic;
  opacity: 0.7;
}
</style>
