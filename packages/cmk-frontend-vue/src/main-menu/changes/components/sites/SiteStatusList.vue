<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { ref, toRef } from 'vue'

import usei18n from '@/lib/i18n'
import { immediateWatch } from '@/lib/watch'

import CmkScrollContainer from '@/components/CmkScrollContainer.vue'
import CmkTabs, { CmkTab, CmkTabContent } from '@/components/CmkTabs'

import { useSiteStatus } from '@/main-menu/changes/useSiteStatus'

import type { Site } from '../../ChangesInterfaces'
import SiteStatusItem from './SiteStatusItem.vue'

const { _t } = usei18n()

const props = defineProps<{
  sites: Site[]
  open: boolean
  activating: boolean
  recentlyActivatedSites: string[]
}>()

const selectedSites = defineModel<string[]>({ required: true })
const activeTab = ref<string | number>('sites-with-changes')
const { sitesWithChanges, sitesWithErrors, siteHasErrors, loggedOutSites } = useSiteStatus(
  toRef(props, 'sites')
)

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
    const currentSitesWithErrors = newSites.filter(siteHasErrors)

    if (currentSitesWithErrors.length > 0) {
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
      <div class="cmk-changes-site-single-title">{{ _t('Site') }}</div>
      <CmkScrollContainer max-height="30vh">
        <SiteStatusItem
          :idx="0"
          :site="props.sites[0]"
          :activating="activating"
          :checked="selectedSites.includes(props.sites[0].siteId)"
          :is-recently-activated="recentlyActivatedSites.includes(props.sites[0].siteId)"
          :hide-checkbox="true"
          @update-checked="toggleSelectedSite"
        ></SiteStatusItem>
      </CmkScrollContainer>
    </div>

    <CmkTabs v-if="props.sites.length > 1" v-model="activeTab">
      <template #tabs>
        <CmkTab v-if="sitesWithChanges.length > 0" id="sites-with-changes">{{
          _t('Sites with changes: %{n}', { n: sitesWithChanges.length })
        }}</CmkTab>
        <CmkTab v-if="sitesWithErrors.length > 0" id="sites-with-errors">{{
          _t('Sites with errors: %{n}', { n: sitesWithErrors.length })
        }}</CmkTab>
        <CmkTab v-if="loggedOutSites.length > 0" id="logged-out-sites">{{
          _t('Sites logged out: %{n}', { n: loggedOutSites.length })
        }}</CmkTab>
      </template>
      <template #tab-contents>
        <CmkTabContent id="sites-with-changes" spacing="none">
          <CmkScrollContainer height="auto" max-height="30vh" class="cmk-scroll-container">
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
          <CmkScrollContainer height="auto" max-height="30vh" class="cmk-scroll-container">
            <SiteStatusItem
              v-for="(site, idx) in sitesWithErrors"
              :key="idx"
              :idx="idx"
              :site="site"
              :activating="activating"
              :checked="selectedSites.includes(site.siteId) && site.onlineStatus === 'online'"
              :is-recently-activated="recentlyActivatedSites.includes(site.siteId)"
              :hide-checkbox="true"
              @update-checked="toggleSelectedSite"
            ></SiteStatusItem>
          </CmkScrollContainer>
        </CmkTabContent>

        <CmkTabContent id="logged-out-sites" spacing="none">
          <CmkScrollContainer height="50%" max-height="30vh" class="cmk-scroll-container">
            <SiteStatusItem
              v-for="(site, idx) in loggedOutSites"
              :key="idx"
              :idx="idx"
              :site="site"
              :activating="activating"
              :checked="selectedSites.includes(site.siteId) && site.onlineStatus === 'online'"
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
/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.cmk-changes-sites {
  margin-top: var(--dimension-7);
}

/* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
.cmk-changes-site-single {
  background: var(--ux-theme-3);
  padding: var(--dimension-4);
  border-radius: var(--border-radius);

  /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
  .cmk-changes-site-single-title {
    color: var(--font-color);
    font-weight: var(--font-weight-bold);
    padding-bottom: var(--dimension-4);
  }
}
</style>
