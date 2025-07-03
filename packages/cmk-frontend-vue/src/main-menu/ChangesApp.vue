<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import usei18n from '@/lib/i18n'
import CmkButtonSubmit from '@/components/CmkButtonSubmit.vue'
import DefaultPopup from './DefaultPopup.vue'
import CmkCollapsibleTitle from '@/components/CmkCollapsibleTitle.vue'
import CmkCollapsible from '@/components/CmkCollapsible.vue'
import CmkIndent from '@/components/CmkIndent.vue'
import CmkButton from '@/components/CmkButton.vue'
import { Api } from '@/lib/api-client'
import CmkIcon from '@/components/CmkIcon.vue'
import CmkProgressbar from '@/components/CmkProgressbar.vue'
import CmkChip from '@/components/CmkChip.vue'
import CmkScrollContainer from '@/components/CmkScrollContainer.vue'
import CmkAlertBox from '@/components/CmkAlertBox.vue'

const { t } = usei18n('changes-app')
const props = defineProps<{
  activate_changes_url: string
  user_has_activate_foreign: boolean
  user_name: string
}>()

const activationStatusCollapsible = ref<boolean>(true)
const pendingChangesCollapsible = ref<boolean>(true)
const restAPI = new Api(`api/1.0/`, [['Content-Type', 'application/json']])
const ajaxCall = new Api()
const activateChangesInProgress = ref<boolean>(false)
const activationStartAndEndTimes = ref<string>('')
const sitesRecentlyActivated = ref<Array<string>>([])
const alreadyMadeAjaxCall = ref<boolean>(false)
const statusColor = (status: string): 'success' | 'warning' | 'danger' | 'default' => {
  const mapping: Record<string, 'success' | 'warning' | 'danger' | 'default'> = {
    online: 'success',
    disabled: 'warning',
    down: 'danger',
    unknown: 'default',
    unreach: 'danger',
    dead: 'danger',
    waiting: 'warning',
    missing: 'warning'
  }
  return mapping[status] ?? 'warning'
}

interface Sites {
  siteId: string
  siteName: string
  onlineStatus: string
  changes: number
  version: string
}

interface PendingChanges {
  changeId: string
  changeText: string
  user: string
  time: number
  whichSites: string
  timestring?: string
}

interface SitesAndChanges {
  sites: Array<Sites>
  pendingChanges: Array<PendingChanges>
}

const sitesAndChanges = ref<SitesAndChanges>({
  sites: [],
  pendingChanges: []
})

// eslint-disable-next-line @typescript-eslint/no-explicit-any
declare const cmk: any

function activateChangesComplete(starttime: number): void {
  activateChangesInProgress.value = false
  sitesRecentlyActivated.value = sitesAndChanges.value.sites
    .filter((site) => site.changes > 0 && site.onlineStatus === 'online')
    .map((site) => site.siteId)

  void fetchPendingChangesAjax()
  const starttimeFormatted = new Date(starttime).toLocaleTimeString('en-GB', {
    hour12: false
  })
  activationStartAndEndTimes.value = `Start: ${starttimeFormatted} | End: ${new Date().toLocaleTimeString('en-GB', { hour12: false })}`
}

async function activateAllChanges() {
  // Activate changes button should be disabled if there are no pending changes
  // so this shouldn't be necessary.
  if (sitesAndChanges.value.pendingChanges.length === 0) {
    return
  }

  activateChangesInProgress.value = true
  const starttime = Date.now()
  try {
    await restAPI.post(
      `domain-types/activation_run/actions/activate-changes/invoke`,
      {
        redirect: true,
        sites: sitesAndChanges.value.sites
          .filter((site) => site.changes > 0 && site.onlineStatus === 'online')
          .map((site) => site.siteId),
        force_foreign_changes: true
      },
      { headers: [['If-Match', '*']] }
    )

    return
  } catch (error) {
    throw new Error(`Activation failed: ${error}`)
  } finally {
    // Sometimes the API call is too quick. When we fetch the pending changes
    // with the ajax call, the sites are still in the process of activating
    // and the variables don't get updated accordingly. Hence this delay.
    setTimeout(() => {
      void activateChangesComplete(starttime)
    }, 3000)
  }
}

async function fetchPendingChangesAjax(): Promise<void> {
  try {
    const dataAsJson = (await ajaxCall.get(
      'ajax_sidebar_get_sites_and_changes.py'
    )) as SitesAndChanges

    if (Array.isArray(dataAsJson.pendingChanges)) {
      dataAsJson.pendingChanges = dataAsJson.pendingChanges.map((change: PendingChanges) => ({
        ...change,
        timestring: new Date(change.time * 1000).toLocaleString()
      }))
    }

    sitesAndChanges.value = dataAsJson
  } catch (error) {
    throw new Error(`fetchPendingChangsAjax failed: ${error}`)
  }
}

function openActivateChangesPage() {
  cmk.popup_menu.close_popup()
  window.open(props.activate_changes_url, 'main')
}

async function checkIfMenuActive(): Promise<void> {
  if (cmk.popup_menu.is_open('main_menu_changes')) {
    if (!alreadyMadeAjaxCall.value) {
      await fetchPendingChangesAjax()
      alreadyMadeAjaxCall.value = true
      sitesRecentlyActivated.value = []
    }
  } else {
    alreadyMadeAjaxCall.value = false
  }

  setTimeout(() => {
    void checkIfMenuActive()
  }, 300)
}

const activateChangesButtonDisabled = computed((): boolean => {
  if (!props.user_has_activate_foreign) {
    return true
  }
  if (activateChangesInProgress.value) {
    return true
  }
  return !sitesAndChanges.value.sites.some(
    (site) => site.onlineStatus === 'online' && site.changes > 0
  )
})

onMounted(() => {
  void checkIfMenuActive()
})
</script>

<template>
  <DefaultPopup class="mainmenu-popout">
    <div class="mainmenu-popout-header">
      <h1 class="mainmenu-popout-title">
        {{ t('activate-pending-changes', 'Activate pending changes') }}
      </h1>
      <CmkButtonSubmit
        class="cmk-button-submit"
        :disabled="activateChangesButtonDisabled"
        @click="() => activateAllChanges()"
      >
        {{ t('activate-changes-on-all-sites', 'Activate changes (on all sites)') }}
      </CmkButtonSubmit>
      <CmkButton
        variant="secondary"
        class="cmk-button-secondary"
        @click="() => openActivateChangesPage()"
        >{{ t('open-full-page', 'Open full page') }}
      </CmkButton>
      <CmkAlertBox
        v-if="!user_has_activate_foreign && sitesAndChanges.pendingChanges.length > 0"
        variant="warning"
        class="cmk-alert-box"
      >
        {{
          t(
            'activate-foreign-changes-info',
            'Sorry, you are not allowed to activate changes of other users.'
          )
        }}
      </CmkAlertBox>
    </div>
    <CmkCollapsibleTitle
      :title="'Activation status'"
      class="collapsible-title"
      :open="activationStatusCollapsible"
      @toggle-open="activationStatusCollapsible = !activationStatusCollapsible"
    />
    <CmkScrollContainer
      height="auto"
      :class="[
        { 'display-none': !activationStatusCollapsible },
        { 'add-flex': sitesAndChanges.sites.length > 2 }
      ]"
    >
      <CmkCollapsible :open="activationStatusCollapsible">
        <template v-for="site in sitesAndChanges.sites" :key="site.siteId">
          <CmkIndent v-if="sitesRecentlyActivated.includes(site.siteId)" class="sites_status">
            <div class="site-activate-success">
              <span class="site-name-activate-success">{{ site.siteName }}</span>
              <span :class="[`status-${site.onlineStatus}`]">{{ site.onlineStatus }}</span>
              <span class="site-version-activate-success grey-text">{{ site.version }}</span>
            </div>
            <CmkIcon variant="inline" name="save" />
            <span>{{ t('changes-successfully-activated', 'Changes successfully activated') }}</span>
            <br />
            <span class="grey-text start-end-time">{{ activationStartAndEndTimes }}</span>
          </CmkIndent>
          <CmkIndent v-if="!sitesRecentlyActivated.includes(site.siteId)" :key="site.siteId">
            <div class="site-name-status-version">
              <span class="site-name">{{ site.siteName }}</span>
              <CmkChip
                :content="site.onlineStatus"
                :color="statusColor(site.onlineStatus)"
                size="small"
              ></CmkChip>
              <span class="site-version grey-text">{{ site.version }}</span>
            </div>
            <div>
              <div v-if="site.changes > 0">
                <div
                  v-if="activateChangesInProgress && site.onlineStatus === 'online'"
                  class="progress-bar"
                >
                  <CmkProgressbar max="unknown"></CmkProgressbar>
                </div>
                <div v-else>
                  <span class="grey-text">{{ t('changes', 'Changes:') }} {{ site.changes }}</span
                  ><br />
                  <span>{{ t('activation-needed', 'Activation needed') }}</span>
                </div>
              </div>
              <div v-else class="no-pending-changes">
                <CmkIcon variant="inline" name="save" />
                <span>{{ t('no-pending-changes', 'No pending changes') }}</span>
              </div>
            </div>
          </CmkIndent>
        </template>
      </CmkCollapsible>
    </CmkScrollContainer>

    <CmkCollapsibleTitle
      v-if="sitesAndChanges.pendingChanges.length > 0 || sitesRecentlyActivated.length > 0"
      :title="`Pending changes`"
      class="collapsible-title"
      :open="pendingChangesCollapsible"
      @toggle-open="pendingChangesCollapsible = !pendingChangesCollapsible"
    />
    <CmkScrollContainer class="container-pending-changes" height="auto">
      <CmkCollapsible :open="pendingChangesCollapsible" class="cmk-collapsible">
        <CmkIndent
          v-if="sitesAndChanges.pendingChanges.length === 0 && sitesRecentlyActivated.length > 0"
          class="pending-changes"
        >
          <div class="pending-changes-activate-success">
            <span>
              <CmkIcon variant="plain" size="xxlarge" name="save" />
            </span>
            <br />
            <span class="no-pending-changes-text">{{
              t('no-pending-changes', 'No pending changes')
            }}</span>
            <br />
            <span>{{ t('everything-is-up-to-date', 'Everything is up to date') }}</span>
          </div>
        </CmkIndent>
        <CmkIndent
          v-for="change in sitesAndChanges.pendingChanges"
          v-else
          :key="change.changeId"
          class="pending-changes"
          :class="{ 'red-text': change.user !== user_name && change.user !== null }"
        >
          <span class="pending-changes-change-text">
            {{ change.changeText }}
          </span>
          <br />
          <span class="pending-changes-which-sites">
            {{ change.whichSites }}
          </span>
          <br />
          <div
            class="pending-change-user"
            :class="{ 'grey-text': change.user === user_name || change.user === null }"
          >
            <span>{{ change.user }} </span>
            <span>{{ change.timestring }}</span>
          </div>
        </CmkIndent>
      </CmkCollapsible>
    </CmkScrollContainer>
  </DefaultPopup>
</template>

<style scoped>
.no-pending-changes {
  display: flex;
  align-items: center;
}

.site-activate-success {
  display: flex;
  align-items: center;
  width: 100%;
  margin-bottom: 6px;
}
.start-end-time {
  margin-left: 20px;
}
.site-name-activate-success {
  font-weight: bold;
  margin-right: 8px;
}
.site-version-activate-success {
  margin-left: auto;
}
.site-name-status-version {
  display: flex;
  align-items: center;
  width: 100%;
  margin-bottom: 6px;
}
.site-name {
  font-weight: bold;
  margin-right: 8px;
}
.site-status {
  margin-right: 8px;
}
.site-version {
  margin-left: auto;
}

.mainmenu-popout-title {
  display: flex;
  align-items: center;
  margin-top: 5px;
  margin-bottom: 15px;
  font-weight: bold;

  label {
    margin-right: 10px;
  }
}
.mainmenu-popout {
  display: flex;
  flex-direction: column;
  background-color: var(--ux-theme-2);
  padding: 20px;
}

.display-none {
  display: none;
}
.add-flex {
  flex: 2;
}

.container-pending-changes {
  flex: 5;
}

.cmk-button-submit {
  margin-right: 10px;
}

.collapsible-title {
  margin-top: 20px;
}

.cmk-indent {
  padding: 8px 6px 8px 6px !important;
  background-color: var(--ux-theme-4);
  margin: 0px !important;
  border-left: 0px !important;

  &:not(:last-of-type) {
    border-bottom: 2px solid var(--ux-theme-1);
  }
}

.pending-changes span {
  margin-bottom: 3px;
  margin-right: 5px;
  display: inline-block;
}
.pending-changes-activate-success {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}
.no-pending-changes-text {
  font-weight: bold;
}

.pending-changes-change-text {
  font-weight: bold;
}

.pending-changes-which-sites {
  font-style: italic;
}

.pending-change-user {
  display: flex;
  justify-content: space-between;
}

.collapsible-title {
  position: relative;
  height: auto;
  padding: 4px 10px 3px 9px;
  font-weight: bold;
  letter-spacing: 1px;
  background-color: var(--ux-theme-5);
  width: 100%;
  box-sizing: border-box;
  display: block;
  text-align: left;
}

.grey-text {
  color: rgb(150, 150, 150);
}
.red-text {
  color: var(--color-danger);
}
</style>
