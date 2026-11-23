<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkAlert from 'cmk-ui-library/components/CmkAlert.vue'
import CmkBadge from 'cmk-ui-library/components/CmkBadge.vue'
import CmkDropdown from 'cmk-ui-library/components/CmkDropdown'
import type { Suggestions } from 'cmk-ui-library/components/CmkSuggestions'
import usei18n, { untranslated } from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import type { ServicesToCreate } from '../definition'
import type { CreatableFolder, NewHostFolders } from '../newHostFolders'
import type { ServicesPreview } from '../servicesPreview'

const { _t, _tn } = usei18n()

// More clashes are only counted; the list flags those among the services it shows
const CLASHES_EXPLAINED = 3

const {
  preview,
  folders = [],
  newHostFolders = {},
  foldersNotLookedUp = false
} = defineProps<{
  preview: ServicesPreview
  folders?: CreatableFolder[]
  newHostFolders?: NewHostFolders
  foldersNotLookedUp?: boolean
}>()

const emit = defineEmits<{
  chooseFolder: [hostNames: string[], folder: string]
}>()

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

const services = computed(() =>
  preview.status === 'resolved' || preview.status === 'refreshing' ? preview.services : null
)

const createdInMainUnasked = computed<boolean>(() => {
  const listed = services.value
  return (
    foldersNotLookedUp &&
    listed !== null &&
    (listed.total > listed.services.length || listed.services.some((service) => service.new_host))
  )
})

const folderOptions = computed<Suggestions>(() => ({
  type: 'fixed',
  suggestions: folders.map((folder) => ({ name: folder.path, title: untranslated(folder.title) }))
}))

function folderTitle(path: string): string {
  return folders.find((folder) => folder.path === path)?.title ?? path
}

type Service = ServicesToCreate['services'][number]

function choosesFolder(service: Service): boolean {
  return service.new_host && newHostFolders[service.host_name] !== undefined
}

/** The rows that choose the folder of their host: the first listed service of each new host. */
const choosingRows = computed<Map<number, string>>(() => {
  const rows = new Map<number, string>()
  const seen = new Set<string>()
  services.value?.services.forEach((service, index) => {
    if (choosesFolder(service) && !seen.has(service.host_name)) {
      seen.add(service.host_name)
      rows.set(index, service.host_name)
    }
  })
  return rows
})

/** New hosts no row chooses the folder of, given one folder together */
const otherNewHosts = computed<string[]>(() => {
  const chosenInRows = new Set(choosingRows.value.values())
  return Object.keys(newHostFolders).filter((hostName) => !chosenInRows.has(hostName))
})

const otherNewHostsFolder = computed<string | null>(() => {
  const paths = new Set(otherNewHosts.value.map((hostName) => newHostFolders[hostName]))
  return paths.size === 1 ? [...paths][0]! : null
})
</script>

<template>
  <div class="mode-custom-services-services-to-be-created" aria-live="polite">
    <div class="mode-custom-services-services-to-be-created__header">
      <span class="mode-custom-services-services-to-be-created__label">
        {{ _t('Services to be created') }}
        <template v-if="services">({{ services.total }})</template>
      </span>
      <span
        v-if="preview.status === 'refreshing'"
        class="mode-custom-services-services-to-be-created__note"
        >{{ _t('Updating…') }}</span
      >
    </div>
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
          <div class="mode-custom-services-services-to-be-created__host">
            {{ service.host_name }}
            <CmkBadge size="small" :color="service.new_host ? 'success' : 'default'">{{
              service.new_host ? _t('To be created') : _t('Existing')
            }}</CmkBadge>
          </div>
          <template v-if="choosesFolder(service)">
            <span
              class="mode-custom-services-services-to-be-created__key mode-custom-services-services-to-be-created__key--folder"
              >{{ _t('Folder:') }}</span
            >
            <CmkDropdown
              v-if="choosingRows.has(index)"
              :model-value="newHostFolders[service.host_name]!"
              :options="folderOptions"
              :label="_t('Folder of %{host}', { host: service.host_name })"
              @update:model-value="
                (folder: string | null) =>
                  folder !== null && emit('chooseFolder', [service.host_name], folder)
              "
            />
            <span v-else>{{ folderTitle(newHostFolders[service.host_name]!) }}</span>
          </template>
          <span
            v-if="clashLabel(service.clash)"
            class="mode-custom-services-services-to-be-created__clash"
            >{{ clashLabel(service.clash) }}</span
          >
        </li>
      </ol>
      <CmkAlert
        v-if="createdInMainUnasked"
        size="small"
        variant="warning"
        :text="
          _t(
            'The folders you may create hosts in could not be looked up, so new hosts go to the Main folder. Saving fails if you may not create hosts there.'
          )
        "
      />
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
    <div
      v-if="(services !== null || preview.status === 'failed') && otherNewHosts.length > 0"
      class="mode-custom-services-services-to-be-created__more-hosts"
    >
      <span>{{
        choosingRows.size > 0
          ? _tn(
              '%{n} more new host is created in',
              '%{n} more new hosts are created in',
              otherNewHosts.length,
              { n: otherNewHosts.length }
            )
          : _tn(
              '%{n} new host is created in',
              '%{n} new hosts are created in',
              otherNewHosts.length,
              {
                n: otherNewHosts.length
              }
            )
      }}</span>
      <CmkDropdown
        :model-value="otherNewHostsFolder"
        :options="folderOptions"
        :input-hint="_t('Several folders')"
        :label="_t('Folder of the other new hosts')"
        @update:model-value="
          (folder: string | null) => folder !== null && emit('chooseFolder', otherNewHosts, folder)
        "
      />
    </div>
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

.mode-custom-services-services-to-be-created__header {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: var(--dimension-3);
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
  align-items: center;
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
  align-self: start;
  font-family: monospace;
}

.mode-custom-services-services-to-be-created__key {
  color: var(--font-color-dimmed);
}

.mode-custom-services-services-to-be-created__host {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
}

.mode-custom-services-services-to-be-created__key--folder {
  grid-column: 2;
}

.mode-custom-services-services-to-be-created__more-hosts {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--dimension-3);
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
