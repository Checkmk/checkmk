<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { Api } from '@/lib/api-client'
import { CmkFetchError } from '@/lib/cmkFetch'
import usei18n from '@/lib/i18n'

import CmkAlertBox from '@/components/CmkAlertBox.vue'
import CmkButton from '@/components/CmkButton.vue'
import CmkButtonSubmit from '@/components/CmkButtonSubmit.vue'
import CmkDialog from '@/components/CmkDialog.vue'
import CmkIcon from '@/components/CmkIcon'

import { showLoadingTransition } from '@/loading-transition/loadingTransition'
import { useSiteStatus } from '@/main-menu/changes/useSiteStatus'

import type {
  ActivatePendingChangesResponse,
  ActivationStatusResponse,
  NumberOfPendingChangesResponse,
  PendingChanges,
  Site,
  SitesAndChanges
} from './ChangesInterfaces'
import DefaultPopup from './components/DefaultPopup.vue'
import ChangesActivating from './components/activation/ChangesActivating.vue'
import ChangesActivationResult from './components/activation/ChangesActivationResult.vue'
import PendingChangesList from './components/pending-changes/PendingChangesList.vue'
import SiteStatusList from './components/sites/SiteStatusList.vue'

const { _t } = usei18n()
const props = defineProps<{
  activate_changes_url: string
  user_has_activate_foreign: boolean
  user_name: string
}>()

const numberOfChangesLastActivation = ref<number>(0)
const selectedSites = ref<string[]>([])
const recentlyActivatedSites = ref<string[]>([])
const activationStatusCollapsible = ref<boolean>(true)
const restAPI = new Api(`api/1.0/`, [['Content-Type', 'application/json']])
const ajaxCall = new Api()
const activateChangesInProgress = ref<boolean>(false)
const alreadyMadeAjaxCall = ref<boolean>(false)

const sitesAndChanges = ref<SitesAndChanges>({
  sites: [],
  pendingChanges: []
})

const sitesRef = computed(() => sitesAndChanges.value.sites)
const { hasSitesWithChangesOrErrors } = useSiteStatus(sitesRef)

// eslint-disable-next-line @typescript-eslint/no-explicit-any
declare const cmk: any

const activationPollStartTime = ref<number | null>(null)
const restartInfoShown = ref(false)
const siteRestartWaitTime = 30000

async function pollActivationStatusUntilComplete(activationId: string) {
  try {
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
        void pollActivationStatusUntilComplete(activationId)
      }, 100)
    } else {
      numberOfChangesLastActivation.value = response.extensions.changes.length
      await fetchPendingChangesAjax()
      activateChangesInProgress.value = false
    }
  } catch (error) {
    if (error instanceof CmkFetchError) {
      const cmkError = error as CmkFetchError
      const statusCode = cmkError.getStatusCode()

      if (
        statusCode === 503 &&
        activationPollStartTime.value &&
        Date.now() - activationPollStartTime.value <= siteRestartWaitTime
      ) {
        if (!restartInfoShown.value) {
          restartInfoShown.value = true
        }

        setTimeout(() => {
          void pollActivationStatusUntilComplete(activationId)
        }, 1000)

        return
      }
    }

    activateChangesInProgress.value = false
    activationPollStartTime.value = null
    restartInfoShown.value = false

    throw new Error(`Polling of activation result failed: ${error}`)
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

  try {
    const activateChangesResponse = (await restAPI.post(
      `domain-types/activation_run/actions/activate-changes/invoke`,
      {
        redirect: false,
        sites: sitesAndChanges.value.sites
          .filter(
            (site) =>
              site.changes > 0 &&
              ['online', 'disabled'].includes(site.onlineStatus) &&
              selectedSites.value.includes(site.siteId) &&
              site.loggedIn
          )
          .map((site) => site.siteId),
        force_foreign_changes: true
      },
      { headers: [['If-Match', '*']] }
    )) as ActivatePendingChangesResponse
    activationPollStartTime.value = Date.now()
    void pollActivationStatusUntilComplete(activateChangesResponse.id)
    return
  } catch (error) {
    await fetchPendingChangesAjax()
    activateChangesInProgress.value = false
    throw new Error(`Activation failed: ${error}`)
  }
}

function setSelectedSites() {
  /**
   * selectedSites determines whether or not the site checkbox is checked.
   * If the site has changes after the ajax call, it will be added to the
   * selectedSites array.
   * Only sites that are logged in and online/disabled should have their checkboxes selected.
   */
  selectedSites.value = sitesAndChanges.value.sites
    .filter((site: Site) => site.changes > 0 && ['online', 'disabled'].includes(site.onlineStatus))
    .filter((site: Site) => site.loggedIn)
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

    sitesAndChanges.value = dataAsJson

    setSelectedSites()
  } catch (error) {
    throw new Error(`fetchPendingChangesAjax failed: ${error}`)
  }
}

function openActivateChangesPage() {
  cmk.popup_menu.close_popup()
  showLoadingTransition('table', _t('Activate pending changes'))
  window.open(props.activate_changes_url, 'main')
}

async function checkIfMenuActive(): Promise<void> {
  if (cmk.popup_menu.is_open('main_menu_changes')) {
    if (!alreadyMadeAjaxCall.value) {
      recentlyActivatedSites.value = []
      await fetchPendingChangesAjax()
      alreadyMadeAjaxCall.value = true
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
    (site) => ['online', 'disabled'].includes(site.onlineStatus) && site.changes > 0
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

function calcChangesHeight(): number {
  if (!activationStatusCollapsible.value) {
    return -0.78
  } else {
    return sitesAndChanges.value.sites.length > 5 ? 5 : sitesAndChanges.value.sites.length - 1
  }
}

async function pollNumberPendingChanges() {
  const response: NumberOfPendingChangesResponse = (await ajaxCall.get(
    'ajax_sidebar_get_number_of_pending_changes.py'
  )) as NumberOfPendingChangesResponse

  const l = document.getElementById('changes_label')

  if (l) {
    if (response.number_of_pending_changes === 0) {
      l.style.display = 'none'
      return
    }
    l.innerText =
      response.number_of_pending_changes > 9 ? '9+' : response.number_of_pending_changes.toString()
    l.style.display = 'inline'
  }

  setTimeout(() => {
    void pollNumberPendingChanges()
  }, 3000)
}

onMounted(async () => {
  // Fetch once on mount, then again when popup is opened to refresh data.
  // This avoids showing no changes when opening the menu for the first time,
  // while the ajax call is in progress.
  await pollNumberPendingChanges()
  await fetchPendingChangesAjax()
  void checkIfMenuActive()
})
</script>

<template>
  <DefaultPopup class="cmk-default-popup-mainmenu">
    <div class="cmk-default-popup-mainmenu__header">
      <h1>{{ _t('Activate pending changes') }}</h1>
    </div>
    <div class="cmk-div-mainmenu-container">
      <div class="cmk-div-buttons-container">
        <CmkButtonSubmit
          class="cmk-button-submit"
          :disabled="activateChangesButtonDisabled"
          @click="() => activateAllChanges()"
        >
          {{ _t('Activate pending changes') }}
        </CmkButtonSubmit>
        <CmkButton
          variant="secondary"
          class="cmk-button-secondary"
          @click="() => openActivateChangesPage()"
        >
          <CmkIcon variant="inline" name="frameurl" />
          {{ _t('Open full view') }}
        </CmkButton>
      </div>
      <CmkDialog
        :message="
          _t(
            `Changes are saved in a temporary environment first, letting you review and adjust them safely.
             Activate changes to apply them to live monitoring.`
          )
        "
        :dismissal_button="{
          title: _t('Do not show again'),
          key: 'changes-info'
        }"
      />
      <CmkAlertBox
        v-if="!user_has_activate_foreign && sitesAndChanges.pendingChanges.length > 0"
        variant="warning"
        class="cmk-alert-box"
      >
        {{ _t('Sorry, you are not allowed to activate changes of other users.') }}
      </CmkAlertBox>
      <ChangesActivating
        v-if="activateChangesInProgress"
        :activating-on-sites="
          recentlyActivatedSites.length > 1 ? recentlyActivatedSites : recentlyActivatedSites[0]
        "
        :restart-info="restartInfoShown"
      >
      </ChangesActivating>

      <ChangesActivationResult
        v-if="
          !activateChangesInProgress &&
          recentlyActivatedSites.length > 0 &&
          !sitesWithWarningsOrErrors
        "
        type="success"
        :title="
          numberOfChangesLastActivation === 1
            ? _t('Successfully activated 1 change')
            : _t('Successfully activated %{numberOfChangesLastActivation} changes', {
                numberOfChangesLastActivation
              })
        "
        :info="_t('Everything is up to date')"
        class="cmk-div-activation-result-container"
      >
      </ChangesActivationResult>

      <ChangesActivationResult
        v-if="
          noPendingChangesOrWarningsOrErrors &&
          !activateChangesInProgress &&
          recentlyActivatedSites.length === 0
        "
        type="success"
        :title="_t('No pending changes')"
        :info="_t('Everything is up to date')"
        class="cmk-div-activation-result-container"
      >
      </ChangesActivationResult>

      <div
        v-if="
          recentlyActivatedSites.length > 0 || sitesWithWarningsOrErrors || weHavePendingChanges
        "
        class="cmk-div-sites-and-pending-changes-container"
      >
        <ChangesActivationResult
          v-if="sitesWithWarningsOrErrors && !activateChangesInProgress"
          class="cmk-div-activation-result-container"
          type="warning"
          :title="_t('Problems detected during activation')"
          :info="_t('Some things may not be monitored properly.')"
        >
        </ChangesActivationResult>

        <SiteStatusList
          v-if="hasSitesWithChangesOrErrors"
          v-model="selectedSites"
          :sites="sitesAndChanges.sites"
          :open="activationStatusCollapsible"
          :activating="activateChangesInProgress"
          :recently-activated-sites="recentlyActivatedSites"
        ></SiteStatusList>
        <PendingChangesList
          v-if="weHavePendingChanges"
          v-model:pending-changes="sitesAndChanges.pendingChanges"
          v-model:number-of-foreign-changes="numberOfForeignChanges"
          class="pending-changes-container"
          :selected-sites="selectedSites"
          :user-name="props.user_name"
        />
      </div>
    </div>
  </DefaultPopup>
</template>

<style scoped>
/* stylelint-disable checkmk/vue-bem-naming-convention */
.cmk-default-popup-mainmenu {
  display: flex;
  width: 500px;
  height: calc(100vh - 64px);
  flex-direction: column;
  align-items: flex-start;
  border-top: 1px solid var(--default-nav-border-color);
  gap: 12px;

  .cmk-default-popup-mainmenu__header {
    height: 60px;
    min-height: 60px;
    z-index: +1;
    width: calc(100% - 2 * var(--spacing-double));
    display: flex;
    flex-direction: row;
    align-items: center;
    padding: 0 var(--spacing-double);
    border-top: 1px solid var(--ux-theme-3);
    border-bottom: 1px solid var(--ux-theme-3);

    h1 {
      margin: 0;
    }
  }
}

.cmk-div-mainmenu-container {
  display: flex;
  width: calc(100% - 2 * var(--spacing-double));
  height: 943px;
  flex-direction: column;
  align-items: flex-start;
  flex-shrink: 0;
  margin: var(--spacing-double);
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
  position: relative;
  box-sizing: border-box;
  width: 100%;
}

.cmk-div-activation-result {
  display: flex;
  padding: 0 29px;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 8px;
  align-self: stretch;
}

.pending-changes-container {
  width: 100%;
  height: calc(100vh - 178px - (48px * v-bind('calcChangesHeight()')));
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
  color: var(--font-color);
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

.cmk-scroll-pending-changes-container {
  width: inherit;
  display: flex;
  flex-direction: column;
}

.cmk-collapsible-pending-changes {
  width: 100%;
  height: calc(100% - 158px);
}

/* stylelint-disable-next-line selector-pseudo-class-no-unknown */
:deep(.cmk-collapsible__content) {
  height: 100%;
}

.cmk-indent {
  box-sizing: border-box;
  background-color: var(--default-bg-color);
  margin: 0 !important;
  border-left: 0 !important;

  &:not(:last-of-type) {
    border-bottom: 2px solid var(--ux-theme-1);
  }
}

.collapsible-title {
  position: relative;
  height: auto;
  margin-top: 16px;
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
