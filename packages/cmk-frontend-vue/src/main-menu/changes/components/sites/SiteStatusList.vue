<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { toRef } from 'vue'

import usei18n from '@/lib/i18n'

import CmkScrollContainer from '@/components/CmkScrollContainer.vue'
import CmkTabs, { CmkTab, CmkTabContent } from '@/components/CmkTabs'

import { useSiteStatus } from '@/main-menu/changes/useSiteStatus'

import type { PendingChanges, Site } from '../../ChangesInterfaces'
import SiteStatusItem from './SiteStatusItem.vue'

const { _t } = usei18n()

const props = defineProps<{
  sites: Site[]
  open: boolean
  activating: boolean
  recentlyActivatedSites: string[]
  pendingChanges: PendingChanges[]
  userHasActivateForeign: boolean
}>()

const selectedSites = defineModel<string[]>({ required: true })
const {
  sitesWithChanges,
  siteHasStatusProblems,
  siteHasActivationIssues,
  siteHasForeignChangesWithoutPermission
} = useSiteStatus(
  toRef(props, 'sites'),
  toRef(props, 'pendingChanges'),
  toRef(props, 'userHasActivateForeign')
)

function toggleSelectedSite(siteId: string, value: boolean) {
  if (value) {
    selectedSites.value.push(siteId)
  } else {
    selectedSites.value.splice(selectedSites.value.indexOf(siteId), 1)
  }
}
</script>

<template>
  <div class="cmk-changes-sites" :class="{ 'add-flex': props.sites.length === 1 }">
    <div
      v-if="
        props.sites.length === 1 &&
        typeof props.sites[0] !== 'undefined' &&
        !activating &&
        props.sites[0].changes > 0
      "
      class="cmk-changes-site-single"
    >
      <div class="cmk-changes-site-single-title">{{ _t('Site(s) with changes') }}</div>
      <CmkScrollContainer max-height="30vh">
        <SiteStatusItem
          :idx="0"
          :site="props.sites[0]"
          :activating="activating"
          :checked="selectedSites.includes(props.sites[0].siteId)"
          :is-recently-activated="recentlyActivatedSites.includes(props.sites[0].siteId)"
          :hide-checkbox="true"
          :has-activation-issues="siteHasActivationIssues(props.sites[0])"
          :has-status-problems="siteHasStatusProblems(props.sites[0])"
          :has-foreign-changes-without-permission="
            siteHasForeignChangesWithoutPermission(props.sites[0])
          "
          @update-checked="toggleSelectedSite"
        ></SiteStatusItem>
      </CmkScrollContainer>
    </div>

    <CmkTabs v-if="props.sites.length > 1" model-value="sites-with-changes">
      <template #tabs>
        <CmkTab v-if="sitesWithChanges.length > 0" id="sites-with-changes">{{
          _t('Sites with changes: %{n}', { n: sitesWithChanges.length })
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
              :has-activation-issues="siteHasActivationIssues(site)"
              :has-status-problems="siteHasStatusProblems(site)"
              :has-foreign-changes-without-permission="siteHasForeignChangesWithoutPermission(site)"
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
