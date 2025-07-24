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
import CmkScrollContainer from '@/components/CmkScrollContainer.vue'
import CmkAlertBox from '@/components/CmkAlertBox.vue'
import CmkCheckbox from '@/components/CmkCheckbox.vue'
import CmkBadge from '@/components/CmkBadge.vue'
import CmkZebra from '@/components/CmkZebra.vue'
import CmkDialog from '@/components/CmkDialog.vue'

const { t } = usei18n('changes-app')
const props = defineProps<{
  activate_changes_url: string
  user_has_activate_foreign: boolean
  user_name: string
}>()

const numberOfChangesLastActivation = ref<number>(0)
const selectedSites = ref<Array<string>>([])
const recentlyActivatedSites = ref<Array<string>>([])
const activationStatusCollapsible = ref<boolean>(true)
const pendingChangesCollapsible = ref<boolean>(true)
const restAPI = new Api(`api/1.0/`, [['Content-Type', 'application/json']])
const ajaxCall = new Api()
const activateChangesInProgress = ref<boolean>(false)
const activationStartAndEndTimes = ref<string>('')
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

interface StatusPerSiteResponse {
  site: string
  phase: 'initialized' | 'queued' | 'started' | 'sync' | 'activate' | 'finishing' | 'done'
  state: 'warning' | 'success' | 'error'
  status_text: string
  status_details: string
  start_time: string
  end_time: string
}

// We only really care about the status_per_site & is_running. The rest is not used in the UI
interface ActivationExtensionsResponse {
  sites: Array<string>
  is_running: boolean
  force_foreign_changes: boolean
  time_started: string
  changes: Array<object>
  status_per_site: Array<StatusPerSiteResponse>
}

// We only really care about the extensions. The rest is not used in the UI
interface ActivationStatusResponse {
  links: Array<object>
  domainType: string
  id: string
  title: string
  members: object
  extensions: ActivationExtensionsResponse
}

// We only really care about the id. The rest is not used in the UI
interface ActivatePendingChangesResponse {
  links: Array<object>
  domainType: string
  id: string
  title: string
  members: object
  extensions: object
}

// Site information as returned by the ajax call
// The lastActivationStatus is added when activating changes
interface Site {
  siteId: string
  siteName: string
  onlineStatus: string
  changes: number
  version: string
  lastActivationStatus: StatusPerSiteResponse | undefined
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
  sites: Array<Site>
  pendingChanges: Array<PendingChanges>
}

const sitesAndChanges = ref<SitesAndChanges>({
  sites: [],
  pendingChanges: []
})

// eslint-disable-next-line @typescript-eslint/no-explicit-any
declare const cmk: any

function storeLastActivationStatus() {
  sitesAndChanges.value.sites.forEach((site) => {
    if (site.lastActivationStatus) {
      localStorage.setItem(
        `lastActivationStatus-${site.siteId}`,
        JSON.stringify(site.lastActivationStatus)
      )
    }
  })
}

function loadLastActivationStatus(sites: Array<Site>): Array<Site> {
  return sites.map((site: Site) => {
    const lastActivationStatus = localStorage.getItem(`lastActivationStatus-${site.siteId}`)
    if (lastActivationStatus) {
      return {
        ...site,
        lastActivationStatus: JSON.parse(lastActivationStatus)
      }
    }
    return {
      ...site,
      lastActivationStatus: undefined // No activation status available
    }
  })
}

function activateChangesComplete(starttime: number): void {
  activateChangesInProgress.value = false
  // Fetches pending changes & preserve the current activation status
  void fetchPendingChangesAjax()

  // We are currently using the time from the activation status response but
  // This doesn't take into account the browser time zone.
  const starttimeFormatted = new Date(starttime).toLocaleTimeString('en-GB', {
    hour12: false
  })
  activationStartAndEndTimes.value = `Start: ${starttimeFormatted} | End: ${new Date().toLocaleTimeString('en-GB', { hour12: false })}`
  storeLastActivationStatus()
}

async function getActivationStatus(activationId: string) {
  const response = (await restAPI.get(
    `objects/activation_run/${activationId}`
  )) as ActivationStatusResponse

  const statusPerSite = response.extensions.status_per_site
  sitesAndChanges.value.sites.forEach((site) => {
    const siteStatus = statusPerSite.find((status) => status.site === site.siteId)
    if (siteStatus) {
      site.lastActivationStatus = siteStatus
      recentlyActivatedSites.value.push(site.siteId)
    }
  })

  if (response.extensions.is_running) {
    setTimeout(() => {
      void getActivationStatus(activationId)
    }, 100)
  } else {
    numberOfChangesLastActivation.value = response.extensions.changes.length
  }
}

async function activateAllChanges() {
  // Activate changes button should be disabled if there are no pending changes
  // so this shouldn't be necessary.
  if (sitesAndChanges.value.pendingChanges.length === 0) {
    return
  }

  activateChangesInProgress.value = true
  recentlyActivatedSites.value = []

  const starttime = Date.now()
  try {
    const activateChangesResponse = (await restAPI.post(
      `domain-types/activation_run/actions/activate-changes/invoke`,
      {
        redirect: false,
        sites: sitesAndChanges.value.sites
          .filter(
            (site) =>
              site.changes > 0 &&
              site.onlineStatus === 'online' &&
              selectedSites.value.includes(site.siteId)
          )
          .map((site) => site.siteId),
        force_foreign_changes: true
      },
      { headers: [['If-Match', '*']] }
    )) as ActivatePendingChangesResponse
    void getActivationStatus(activateChangesResponse.id)
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

function setSelectedSites() {
  /**
   * selectedSites determines whether or not the site checkbox is checked.
   * If the site has changes after the ajax call, it will be added to the
   * selectedSites array.
   */
  selectedSites.value = sitesAndChanges.value.sites
    .filter((site: Site) => site.changes > 0)
    .map((site: Site) => site.siteId)
}

async function fetchPendingChangesAjax(): Promise<void> {
  try {
    const dataAsJson = (await ajaxCall.get(
      'ajax_sidebar_get_sites_and_changes.py'
    )) as SitesAndChanges

    if (Array.isArray(dataAsJson.pendingChanges)) {
      dataAsJson.pendingChanges = dataAsJson.pendingChanges
        .sort((a, b) => b.time - a.time)
        .map((change: PendingChanges) => ({
          ...change,
          timestring: new Date(change.time * 1000).toLocaleString()
        }))
    }

    dataAsJson.sites = loadLastActivationStatus(dataAsJson.sites)

    const currentSites = sitesAndChanges.value.sites
    sitesAndChanges.value = {
      ...dataAsJson,
      sites: dataAsJson.sites.map((newSite) => {
        const oldSite = currentSites.find((s) => s.siteId === newSite.siteId)
        return oldSite && oldSite.lastActivationStatus
          ? {
              ...newSite,
              lastActivationStatus: oldSite.lastActivationStatus
            }
          : newSite
      })
    }

    setSelectedSites()
  } catch (error) {
    throw new Error(`fetchPendingChangesAjax failed: ${error}`)
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
      recentlyActivatedSites.value = []
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
  if (selectedSites.value.length === 0) {
    return true
  }
  return !sitesAndChanges.value.sites.some(
    (site) => site.onlineStatus === 'online' && site.changes > 0
  )
})

const weHavePendingChanges = computed((): boolean => {
  return sitesAndChanges.value.pendingChanges.length > 0
})

const sitesWithWarningsOrErrors = computed((): boolean => {
  return sitesAndChanges.value.sites.some(
    (site) =>
      site.lastActivationStatus &&
      (site.lastActivationStatus.state === 'warning' || site.lastActivationStatus.state === 'error')
  )
})

const noPendingChangesOrWarningsOrErrors = computed((): boolean => {
  return sitesAndChanges.value.sites.every(
    (site) =>
      site.changes === 0 &&
      (!site.lastActivationStatus ||
        (site.lastActivationStatus.state !== 'warning' &&
          site.lastActivationStatus.state !== 'error'))
  )
})

const numberOfForeignChanges = computed((): number => {
  // Count the number of pending changes that are foreign (not by the current user)
  return sitesAndChanges.value.pendingChanges.filter((change) => change.user !== props.user_name)
    .length
})

function siteRequiresAttention(site: Site): boolean {
  return (
    site.changes > 0 ||
    (site.lastActivationStatus && ['error', 'warning'].includes(site.lastActivationStatus.state)) ||
    site.onlineStatus !== 'online' ||
    recentlyActivatedSites.value.includes(site.siteId)
  )
}

function toggleSelectedSite(siteId: string) {
  if (selectedSites.value.includes(siteId)) {
    selectedSites.value.splice(selectedSites.value.indexOf(siteId), 1)
  } else {
    selectedSites.value.push(siteId)
  }
}

function calcChangesHeight(): number {
  if (!activationStatusCollapsible.value) {
    return -0.78
  } else {
    return sitesAndChanges.value.sites.length > 5 ? 5 : sitesAndChanges.value.sites.length - 1
  }
}

onMounted(() => {
  void checkIfMenuActive()
})
</script>

<template>
  <DefaultPopup class="cmk-default-popup-mainmenu">
    <div class="cmk-div-mainmenu-container">
      <div class="cmk-div-popup-title-container">
        <h1>{{ t('activate-pending-changes', 'Activate pending changes') }}</h1>
      </div>
      <div class="cmk-div-buttons-container">
        <CmkButtonSubmit
          class="cmk-button-submit"
          :disabled="activateChangesButtonDisabled"
          @click="() => activateAllChanges()"
        >
          {{ t('activate-changes-on-all-sites', 'Activate pending changes') }}
        </CmkButtonSubmit>
        <CmkButton
          variant="secondary"
          class="cmk-button-secondary"
          @click="() => openActivateChangesPage()"
        >
          <CmkIcon variant="inline" name="frameurl" />
          {{ t('open-full-view', 'Open full view') }}
        </CmkButton>
      </div>
      <CmkDialog
        :message="
          t(
            'changes-info-message',
            'Changes are saved in a temporary environment first, letting you review and adjust them safely.\n' +
              'Activate changes to apply them to live monitoring.'
          )
        "
        :dismissal_button="{
          title: t('Do not show again', 'Do not show again'),
          key: 'changes-info'
        }"
      />
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
      <div v-if="activateChangesInProgress" class="cmk-div-activation-result-container">
        <div class="cmk-div-activation-result">
          <span class="cmk-span-activation-result-text">{{
            t('activating-changes', 'Activating changes...')
          }}</span>
          <span class="cmk-span-activation-result-text">{{
            t(
              'safely-navigate-away',
              "You can safely navigate away - we'll keep working in the background"
            )
          }}</span>
          <CmkProgressbar max="unknown"></CmkProgressbar>
        </div>
      </div>

      <div
        v-if="!activateChangesInProgress && recentlyActivatedSites.length > 0"
        class="cmk-div-activation-result-container"
      >
        <div class="cmk-div-activation-result">
          <CmkIcon variant="plain" size="xxlarge" name="save" />
          <span class="cmk-span-activation-result-text">{{
            t(
              'successfully-activated-changes',
              `Successfully activated ${numberOfChangesLastActivation} changes`
            )
          }}</span>
          <span>{{ t('everything-is-up-to-date', 'Everything is up to date') }}</span>
        </div>
      </div>

      <div
        v-if="
          noPendingChangesOrWarningsOrErrors &&
          !activateChangesInProgress &&
          recentlyActivatedSites.length === 0
        "
        class="cmk-div-activation-result-container"
      >
        <div class="cmk-div-activation-result">
          <CmkIcon variant="plain" size="xxlarge" name="save" />
          <span class="cmk-span-activation-result-text">{{
            t('no-pending-changes', 'No pending changes')
          }}</span>
          <span>{{ t('everything-is-up-to-date', 'Everything is up to date') }}</span>
        </div>
      </div>

      <div
        v-if="
          recentlyActivatedSites.length > 0 || sitesWithWarningsOrErrors || weHavePendingChanges
        "
        class="cmk-div-sites-and-pending-changes-container"
      >
        <div
          v-if="sitesWithWarningsOrErrors && !activateChangesInProgress"
          class="cmk-div-activation-result-container"
        >
          <div class="cmk-div-activation-result">
            <CmkIcon variant="plain" size="xxlarge" name="validation-error" />
            <span class="cmk-span-activation-result-text">{{
              t('problems-detected', 'Problems detected during activation')
            }}</span>
            <span>{{
              t('some-things-may-not-be-monitored', 'Some things may not be monitored properly.')
            }}</span>
          </div>
        </div>

        <div class="sites-container" :class="{ 'add-flex': sitesAndChanges.sites.length === 1 }">
          <CmkCollapsibleTitle
            :title="'Sites'"
            class="collapsible-title"
            :open="activationStatusCollapsible"
            @toggle-open="activationStatusCollapsible = !activationStatusCollapsible"
          />

          <CmkCollapsible
            :open="activationStatusCollapsible"
            class="cmk-collapsible-sites"
            :class="[{ 'display-none': !activationStatusCollapsible }]"
          >
            <CmkScrollContainer height="auto" class="cmk-scroll-sites-container">
              <template v-for="(site, idx) in sitesAndChanges.sites" :key="site.siteId">
                <CmkZebra :num="idx">
                  <template v-if="siteRequiresAttention(site)">
                    <CmkIndent>
                      <div class="cmk-div-site-status-container">
                        <div class="cmk-div-site-status-info">
                          <div class="cmk-div-checkbox-site-status">
                            <CmkCheckbox
                              :model-value="selectedSites.includes(site.siteId)"
                              @update:model-value="toggleSelectedSite(site.siteId)"
                            />
                            <div class="cmk-div-site-online-status">
                              <CmkBadge
                                :color="statusColor(site.onlineStatus)"
                                size="small"
                                class="cmk-div-site-online-status-badge"
                                >{{ site.onlineStatus }}</CmkBadge
                              >
                              <span class="cmk-span-site-name">{{ site.siteName }}</span>
                            </div>
                          </div>
                          <div
                            v-if="!recentlyActivatedSites.includes(site.siteId)"
                            class="cmk-div-site-status-changes"
                          >
                            <template v-if="site.changes > 0">
                              <span class="cmk-span-changes-text">{{
                                t('changes', 'Changes:')
                              }}</span>
                              <CmkBadge color="warning" size="small">{{ site.changes }}</CmkBadge>
                            </template>
                            <span v-else class="cmk-span-changes-text">{{
                              t('no-changes', 'No Changes')
                            }}</span>
                          </div>
                          <div
                            v-if="
                              recentlyActivatedSites.includes(site.siteId) &&
                              site.lastActivationStatus !== undefined
                            "
                            class="cmk-div-site-status-changes"
                          >
                            <div
                              v-if="activateChangesInProgress"
                              class="cmk-progress-bar-site-activation-in-progress"
                            >
                              <CmkProgressbar max="unknown"></CmkProgressbar>
                            </div>
                            <div v-else>
                              {{ site.lastActivationStatus.status_text }}
                            </div>
                          </div>
                        </div>
                        <div
                          v-if="site.lastActivationStatus?.state === 'warning'"
                          class="cmk-div-site-activate-warning"
                        >
                          <CmkIcon variant="inline" name="validation-error" />
                          <div class="cmk-div-warning-or-error-message">
                            <span v-if="site.lastActivationStatus?.state === 'warning'">{{
                              t('changes-activated-with-warning', 'Warning')
                            }}</span>
                            <span class="grey-text">{{
                              site.lastActivationStatus.status_details
                            }}</span>
                          </div>
                        </div>
                        <div
                          v-if="site.lastActivationStatus?.state === 'error'"
                          class="cmk-div-site-activate-error"
                        >
                          <CmkIcon variant="inline" name="alert_crit" />
                          <div class="cmk-div-warning-or-error-message">
                            <span v-if="site.lastActivationStatus.state === 'error'">{{
                              t('changes-failed-to-activate', 'Error')
                            }}</span>
                            <span class="grey-text">{{
                              site.lastActivationStatus.status_details
                            }}</span>
                          </div>
                        </div>
                      </div>
                    </CmkIndent>
                  </template>
                </CmkZebra>
              </template>
            </CmkScrollContainer>
          </CmkCollapsible>
        </div>
        <div
          v-if="weHavePendingChanges && recentlyActivatedSites.length === 0"
          class="pending-changes-container"
        >
          <CmkCollapsibleTitle
            :title="`Changes`"
            class="collapsible-title"
            :open="pendingChangesCollapsible"
            @toggle-open="pendingChangesCollapsible = !pendingChangesCollapsible"
          />

          <CmkCollapsible :open="pendingChangesCollapsible" class="cmk-collapsible-pending-changes">
            <CmkIndent class="cmk-indent-foreign-changes-container">
              <div class="cmk-div-foreign-changes-text">
                {{ t(`foreign-changes`, `Foreign changes: `) }}
              </div>
              <div class="cmk-div-foreign-changes-text">
                {{ numberOfForeignChanges }}
              </div>
            </CmkIndent>

            <CmkIndent
              v-if="selectedSites.length === 0"
              class="cmk-indent-no-sites-selected-container"
            >
              <div class="cmk-div-no-sites-selected">
                {{ t(`no-sites-selected`, `You haven't selected any sites`) }}
              </div>
            </CmkIndent>
            <CmkScrollContainer
              v-if="selectedSites.length > 0"
              class="cmk-scroll-pending-changes-container"
              height="auto"
            >
              <div
                v-for="(change, idx) in sitesAndChanges.pendingChanges"
                :key="change.changeId"
                class="cmk-div-pending-changes-container"
              >
                <CmkZebra :num="idx">
                  <CmkIndent
                    v-if="
                      change.whichSites === 'All sites' || selectedSites.includes(change.whichSites)
                    "
                    class="cmk-indent-pending-change-container"
                    :class="{ 'red-text': change.user !== user_name && change.user !== null }"
                  >
                    <span class="cmk-span-pending-change-text">{{ change.changeText }}</span>

                    <div
                      class="cmk-div-pending-change-details"
                      :class="{ 'grey-text': change.user === user_name || change.user === null }"
                    >
                      <div class="cmk-div-user-sites-timestamp">
                        <span>{{ change.user }}</span>
                        <span>|</span>
                        <span>{{ change.whichSites }}</span>
                      </div>
                      <span>{{ change.timestring }}</span>
                    </div>
                  </CmkIndent>
                </CmkZebra>
              </div>
            </CmkScrollContainer>
          </CmkCollapsible>
        </div>
      </div>
    </div>
  </DefaultPopup>
</template>

<style scoped>
.cmk-default-popup-mainmenu {
  display: flex;
  width: 484px;
  height: calc(100vh - 64px);
  padding: 32px;
  flex-direction: column;
  align-items: flex-start;
  gap: 12px;
}

.cmk-div-mainmenu-container {
  display: flex;
  width: 484px;
  height: 943px;
  flex-direction: column;
  align-items: flex-start;
  flex-shrink: 0;
}

.cmk-div-popup-title-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  align-self: stretch;
  margin-bottom: 19px;
}

.cmk-div-buttons-container {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.cmk-div-sites-and-pending-changes-container {
  width: 100%;
  display: flex;
  flex-direction: column;
  height: calc(100vh - 178px);
}

.cmk-div-activation-result-container {
  display: flex;
  padding: 20px 0px;
  flex-direction: column;
  align-items: flex-start;
  gap: 13px;
  height: 76px;
  align-self: stretch;
  background-color: var(--ux-theme-4);
  margin-top: 20px;
}

.cmk-div-activation-result {
  display: flex;
  padding: 0px 29px;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 8px;
  align-self: stretch;
}

.cmk-span-activation-result-text {
  font-weight: bold;
}

.cmk-progress-bar-site-activation-in-progress {
  width: 100%;
}

.cmk-div-site-activate-warning,
.cmk-div-site-activate-error {
  display: flex;
  padding: 2px 8px;
  justify-content: left;
  align-items: center;
  gap: 4px;
  align-self: stretch;
  border-radius: 4px;
}

.cmk-div-warning-or-error-message {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 4px 0px 4px 0px;
}

.cmk-div-site-activate-error {
  background: rgba(234, 57, 8, 0.15); /* TODO: Which colour should be used? */
}

.cmk-div-site-activate-warning {
  background: rgba(255, 202, 40, 0.15); /* TODO: add var */
}

.cmk-indent-foreign-changes-container {
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  gap: 6px;
  border-bottom: 2px solid var(--ux-theme-4) !important;
}

.pending-changes-container {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: calc(100vh - 178px - (48px * v-bind('calcChangesHeight()')));
}

.cmk-div-site-status-container {
  display: flex;
  width: inherit;
  padding: 0 16px 0 3px;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
}

.cmk-div-site-status-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  align-self: stretch;
  width: 100%;
}

.cmk-div-checkbox-site-status {
  display: flex;
  align-items: center;
  gap: 4px;
}

.cmk-div-site-online-status {
  display: flex;
  padding: 0 8px;
  justify-content: center;
  align-items: center;
  gap: 10px;
}

.cmk-div-site-online-status-badge {
  padding: 0 5px;
}

.cmk-div-site-status-changes {
  display: flex;
  align-items: center;
  gap: 4px;
  width: 50%;
  justify-content: flex-end;
}
.cmk-span-changes-text {
  color: var(--font-color-dimmed);
  font-size: 12px;
  font-style: normal;
  font-weight: 400;
  line-height: normal;
  letter-spacing: 0.36px;
}
.cmk-span-changes-number {
  display: flex;
  padding: 0 8px;
  justify-content: center;
  align-items: center;
  gap: 10px;
  border-radius: 80px;
  background: #ffc31c;
  color: #000;
  font-size: 10px;
  font-style: normal;
  font-weight: 700;
  line-height: normal;
  letter-spacing: 0.3px;
}

.sites-container {
  display: flex;
  flex-direction: column;
  width: 100%;
  max-height: calc(
    (48px * (v-bind('sitesAndChanges.sites.length > 5? 5: sitesAndChanges.sites.length ') + 1))
  );
}

.cmk-span-site-name {
  color: var(---font-color);
  font-size: 12px;
  font-style: normal;
  font-weight: 700;
  line-height: normal;
  letter-spacing: 0.36px;
  max-width: 200px;
  white-space: nowrap;
  text-overflow: ellipsis;
  overflow: hidden;
}

.display-none {
  display: none;
}
.add-flex {
  flex: 2;
}

.cmk-button-submit {
  margin-right: 10px;
}

.collapsible-title {
  margin-top: 16px;
}

.cmk-scroll-sites-container {
  width: inherit;
}

.cmk-collapsible-sites {
  width: 100%;
  height: calc(100% - 44px);
}

.cmk-scroll-pending-changes-container {
  width: inherit;
  display: flex;
  flex-direction: column;
}

.cmk-collapsible-pending-changes {
  width: 100%;
  height: calc(100% - 158px);
}

:deep(.cmk-collapsible__content) {
  height: 100%;
}

.cmk-indent {
  box-sizing: border-box;
  background-color: var(--default-bg-color);
  margin: 0px !important;
  border-left: 0px !important;

  &:not(:last-of-type) {
    border-bottom: 2px solid var(--ux-theme-1);
  }
}

.cmk-div-pending-change-details {
  display: flex;
  justify-content: space-between;
  align-items: center;
  align-self: stretch;
  color: var(--font-color-dimmed);
  font-size: 12px;
  font-style: normal;
  font-weight: 400;
  line-height: normal;
  letter-spacing: 0.36px;
}

.cmk-div-user-sites-timestamp {
  display: flex;
  align-items: center;
  gap: 4px;
}

.cmk-div-no-sites-selected {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  color: var(--font-color-dimmed);
  font-size: 12px;
  font-style: normal;
  font-weight: 400;
  line-height: normal;
  letter-spacing: 0.36px;
  margin-top: 15px;
  margin-bottom: 15px;
}

.cmk-div-pending-changes-container {
  display: flex;
  width: 100%;
  padding: 0px;
  flex-direction: column;
  align-items: flex-start;
}

.cmk-indent-no-sites-selected-container {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
}

.cmk-indent-pending-change-container {
  display: flex;
  width: 100%;
  padding: 8px !important;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  box-sizing: border-box;
}

.cmk-span-pending-change-text {
  display: flex;
  align-items: flex-start;
  gap: 7px;
  align-self: stretch;
  color: var(--font-color);
  font-size: 12px;
  font-style: normal;
  font-weight: 700;
  line-height: normal;
  letter-spacing: 0.36px;
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
  color: var(--font-color-dimmed);
}

.red-text {
  color: var(--color-danger);
}
</style>
