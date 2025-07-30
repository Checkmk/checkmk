<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type { Site } from '../../ChangesInterfaces'
import usei18n from '@/lib/i18n'
import { immediateWatch } from '@/lib/watch'
import CmkTabs from '@/components/CmkTabs/CmkTabs.vue'
import CmkTab from '@/components/CmkTabs/CmkTab.vue'
import CmkTabContent from '@/components/CmkTabs/CmkTabContent.vue'
import CmkScrollContainer from '@/components/CmkScrollContainer.vue'
import { ref } from 'vue'
import SiteStatusItem from './SiteStatusItem.vue'

const { t } = usei18n('changes-app')

const props = defineProps<{
  sites: Site[]
  open: boolean
  activating: boolean
  recentlyActivatedSites: string[]
}>()

const selectedSites = defineModel<string[]>({ required: true })
type ActiveTab = 'sites-with-changes' | 'sites-with-errors'
const activeTab = ref<ActiveTab>('sites-with-changes')
const sitesWithChanges = ref<Site[]>([])
const sitesWithErrors = ref<Site[]>([])

function siteHasChanges(site: Site): boolean {
  return site.changes > 0
}

function siteHasErrors(site: Site): boolean {
  return (
    (site.lastActivationStatus && ['error', 'warning'].includes(site.lastActivationStatus.state)) ||
    site.onlineStatus !== 'online'
  )
}

function toggleSelectedSite(siteId: string, value: boolean) {
  if (value) {
    selectedSites.value.push(siteId)
  } else {
    selectedSites.value.splice(selectedSites.value.indexOf(siteId), 1)
  }
}

immediateWatch(
  () => ({ newSites: props.sites }),
  async ({ newSites }) => {
    sitesWithChanges.value = newSites.filter(siteHasChanges)
    sitesWithErrors.value = newSites.filter(siteHasErrors)

    if (sitesWithErrors.value.length > 0) {
      activeTab.value = 'sites-with-errors'
    }
  }
)
</script>

<template>
  <div class="cmk-changes-sites" :class="{ 'add-flex': props.sites.length === 1 }">
    <div
      v-if="props.sites.length === 1 && typeof props.sites[0] !== 'undefined' && !activating"
      class="cmk-changes-site-single"
    >
      <div class="cmk-changes-site-single-title">{{ t('sites', 'Sites') }}</div>
      <SiteStatusItem
        :idx="0"
        :site="props.sites[0]"
        :activating="activating"
        :checked="selectedSites.includes(props.sites[0].siteId)"
        :is-recently-activated="recentlyActivatedSites.includes(props.sites[0].siteId)"
        :hide-checkbox="true"
        @update-checked="toggleSelectedSite"
      ></SiteStatusItem>
    </div>
    <CmkTabs v-if="props.sites.length > 1" v-model="activeTab">
      <template #tabs>
        <CmkTab id="sites-with-changes" :disabled="sitesWithChanges.length === 0"
          >{{ t('sites-with-changes', 'Sites with changes') }} ({{
            sitesWithChanges.length
          }})</CmkTab
        >
        <CmkTab id="sites-with-errors" :disabled="sitesWithErrors.length === 0"
          >{{ t('sites-with-errors', 'Sites with errors') }} ({{ sitesWithErrors.length }})</CmkTab
        >
      </template>
      <template #tab-contents>
        <CmkTabContent id="sites-with-changes" spacing="none">
          <CmkScrollContainer height="auto" class="cmk-scroll-container">
            <SiteStatusItem
              v-for="(site, idx) in sitesWithChanges"
              :key="idx"
              :idx="idx"
              :site="site"
              :activating="activating"
              :checked="selectedSites.includes(site.siteId)"
              :is-recently-activated="recentlyActivatedSites.includes(site.siteId)"
              @update-checked="toggleSelectedSite"
            ></SiteStatusItem>
          </CmkScrollContainer>
        </CmkTabContent>

        <CmkTabContent id="sites-with-errors" spacing="none">
          <CmkScrollContainer height="auto" class="cmk-scroll-container">
            <SiteStatusItem
              v-for="(site, idx) in sitesWithErrors"
              :key="idx"
              :idx="idx"
              :site="site"
              :activating="activating"
              :checked="selectedSites.includes(site.siteId)"
              :is-recently-activated="recentlyActivatedSites.includes(site.siteId)"
              :hide-checkbox="true"
              @update-checked="toggleSelectedSite"
            ></SiteStatusItem>
          </CmkScrollContainer>
        </CmkTabContent>
      </template>
    </CmkTabs>
  </div>
</template>

<style scoped>
.cmk-changes-sites {
  margin-top: var(--dimension-item-spacing-7);
}

.cmk-changes-site-single {
  background: var(--ux-theme-3);
  padding: var(--dimension-padding-4);

  .cmk-changes-site-single-title {
    color: var(--font-color);
    font-weight: var(--font-weight-bold);
    padding-bottom: var(--dimension-padding-4);
  }
}
</style>
