<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAlert from 'cmk-ui-library/components/CmkAlert.vue'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import type { ServicesToCreate } from '../definition'
import type { ServicesPreview } from '../servicesPreview'

const { _t } = usei18n()

// More clashes are only counted, the list flags every one of them
const CLASHES_EXPLAINED = 3

const { preview } = defineProps<{ preview: ServicesPreview }>()

type Clash = ServicesToCreate['services'][number]['clash']

function clashLabel(clash: Clash): string | null {
  switch (clash) {
    case 'own_series':
      return _t('Several series get this name')
    case 'custom_service':
      return _t('Another custom service creates this service')
    case 'monitored':
      return _t('The host already has this service')
    default:
      return null
  }
}

const services = computed(() => (preview.status === 'resolved' ? preview.services : null))
</script>

<template>
  <div class="mode-custom-services-services-to-be-created" aria-live="polite">
    <span class="mode-custom-services-services-to-be-created__label">
      {{ _t('Services to be created') }}
      <template v-if="services">({{ services.total }})</template>
    </span>
    <span v-if="preview.status === 'idle'">{{
      _t(
        'Enter a service name and select a host or enter a host name template to see the services to be created.'
      )
    }}</span>
    <CmkAlert
      v-else-if="preview.status === 'loading'"
      size="small"
      variant="loading"
      :text="_t('Looking up the services to be created…')"
    />
    <CmkAlert
      v-else-if="preview.status === 'failed'"
      size="small"
      variant="error"
      :text="untranslated(preview.error)"
    />
    <template v-else-if="services">
      <span v-if="services.total === 0">{{
        _t(
          'The metric currently has no series for these hosts. Services are created as series appear.'
        )
      }}</span>
      <ol v-else class="mode-custom-services-services-to-be-created__list">
        <li
          v-for="(service, index) in services.services"
          :key="`${service.host_name}/${service.service_name}/${index}`"
          class="mode-custom-services-services-to-be-created__item"
          :class="{ 'mode-custom-services-services-to-be-created__item--clash': service.clash }"
        >
          <span class="mode-custom-services-services-to-be-created__number"
            >{{ index + 1 }}/{{ services.total }}</span
          >
          <span class="mode-custom-services-services-to-be-created__key">{{ _t('Service:') }}</span>
          <span class="mode-custom-services-services-to-be-created__name">{{
            service.service_name
          }}</span>
          <span class="mode-custom-services-services-to-be-created__key">{{
            _t('Target host:')
          }}</span>
          <span
            >{{ service.host_name }}
            <template v-if="service.new_host">{{ _t('(new host)') }}</template></span
          >
          <span
            v-if="clashLabel(service.clash)"
            class="mode-custom-services-services-to-be-created__clash"
            >{{ clashLabel(service.clash) }}</span
          >
        </li>
      </ol>
      <span v-if="services.total > services.services.length">{{
        _t('Showing the first %{shown} of %{total} services.', {
          shown: services.services.length,
          total: services.total
        })
      }}</span>
      <span v-if="!services.complete">{{
        _t(
          'The metric has more series than are looked up here, so it creates more services than counted, and their names are checked only when saving.'
        )
      }}</span>
      <CmkAlert
        v-for="clash in services.clashes.slice(0, CLASHES_EXPLAINED)"
        :key="`${clash.host_name}/${clash.service_name}`"
        size="small"
        variant="error"
        :text="untranslated(clash.message)"
      />
      <span v-if="services.clashes.length > CLASHES_EXPLAINED">{{
        _t('%{count} more service names clash.', {
          count: services.clashes.length - CLASHES_EXPLAINED
        })
      }}</span>
      <span v-if="services.total > 0" class="mode-custom-services-services-to-be-created__note">{{
        _t('Series appearing after saving add services that are not shown here.')
      }}</span>
    </template>
  </div>
</template>

<style scoped>
.mode-custom-services-services-to-be-created {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-3);
  font-size: var(--font-size-small);
  overflow-wrap: anywhere;
}

.mode-custom-services-services-to-be-created__label {
  font-weight: bold;
  text-transform: uppercase;
}

.mode-custom-services-services-to-be-created__list {
  max-height: 320px;
  margin: 0;
  padding: 0;
  overflow-y: auto;
  list-style: none;
  border: 1px solid var(--ux-theme-6, rgb(255 255 255 / 10%));
}

.mode-custom-services-services-to-be-created__item {
  display: grid;
  grid-template-columns: max-content max-content 1fr;
  gap: var(--dimension-2) var(--dimension-4);
  padding: var(--dimension-4);

  &:not(:last-child) {
    border-bottom: 1px solid var(--ux-theme-6, rgb(255 255 255 / 10%));
  }
}

.mode-custom-services-services-to-be-created__item--clash {
  border-left: 3px solid var(--color-danger);
}

.mode-custom-services-services-to-be-created__number {
  grid-row: span 2;
  font-family: monospace;
}

.mode-custom-services-services-to-be-created__key {
  color: var(--font-color-dimmed);
}

.mode-custom-services-services-to-be-created__name {
  font-family: monospace;
}

.mode-custom-services-services-to-be-created__clash {
  grid-column: 2 / -1;
  color: var(--color-danger);
}

.mode-custom-services-services-to-be-created__note {
  color: var(--font-color-dimmed);
}
</style>
