<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import type {
  ActivatePendingChangesResponse,
  ActivationStatusResponse,
  ChangesProps,
  PendingChange,
  Site,
  SitesAndChanges
} from 'cmk-shared-typing/typescript/changes'
import { computed, onMounted, ref } from 'vue'

import { Api } from '@/lib/api-client'
import { CmkFetchError } from '@/lib/cmkFetch'
import usei18n from '@/lib/i18n'
import { untranslated } from '@/lib/i18n/i18n'

import CmkAlertBox from '@/components/CmkAlertBox.vue'
import CmkButton from '@/components/CmkButton.vue'
import CmkButtonSubmit from '@/components/CmkButtonSubmit.vue'
import CmkDialog from '@/components/CmkDialog.vue'
import CmkHtml from '@/components/CmkHtml.vue'
import CmkIcon from '@/components/CmkIcon'
import CmkHeading from '@/components/typography/CmkHeading.vue'

import { useSiteStatus } from '@/main-menu/changes/useSiteStatus'

import ChangesStatusBar from './components/ChangesStatusBar.vue'
import DefaultPopup from './components/DefaultPopup.vue'
import UserSettingDialog from './components/UserSettingDialog.vue'
import ChangesActivating from './components/activation/ChangesActivating.vue'
import ChangesActivationResult from './components/activation/ChangesActivationResult.vue'
import PendingChangesList from './components/pending-changes/PendingChangesList.vue'
import SiteStatusList from './components/sites/SiteStatusList.vue'

const { _t, _tn } = usei18n()
const props = defineProps<ChangesProps>()

type RecentlyActivatedSite = readonly [siteId: string, status: string]

const numberOfChangesLastActivation = ref<number>(0)
const selectedSites = ref<string[]>([])
const recentlyActivatedSites = ref<RecentlyActivatedSite[]>([])
const activationStatusCollapsible = ref<boolean>(true)
const restAPI = new Api(`api/1.0/`, [['Content-Type', 'application/json']])
const ajaxCall = new Api()
const activateChangesInProgress = ref<boolean>(false)
const alreadyMadeAjaxCall = ref<boolean>(false)
const defaultActivationError = {
  title: _t('Activation of changes failed'),
  detail: _t('Open the full activation page for more details.')
}
const activationError = ref<{
  title: ReturnType<typeof _t>
  detail: ReturnType<typeof _t>
} | null>(null)

function getActivationErrorFromFetchError(error: CmkFetchError): {
  title: ReturnType<typeof _t>
  detail: ReturnType<typeof _t>
} {
  const splitToken = ': '
  const splitIndex = error.message.indexOf(splitToken)
  if (splitIndex > 0) {
    const title = error.message.slice(0, splitIndex).trim()
    const detail = error.message.slice(splitIndex + splitToken.length).trim()
    if (title && detail) {
      return {
        title: untranslated(title),
        detail: untranslated(detail)
      }
    }
  }

  return defaultActivationError
}

const sitesAndChanges = ref<SitesAndChanges>({
  sites: [],
  pendingChanges: [],
  licenseMessage: null,
  licenseIsBlocking: false
})

const sitesRef = computed(() => sitesAndChanges.value.sites)
const pendingChangesRef = computed(() => sitesAndChanges.value.pendingChanges)
const userCanActivateForeignRef = computed(() => props.user_has_activate_foreign)

const {
  siteSelectionIsDisabled,
  allSitesWithChangesAreNotSelectable,
  sitesWithStatusProblems,
  sitesWithActivationIssues
} = useSiteStatus(sitesRef, pendingChangesRef, userCanActivateForeignRef)

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

    if (response.extensions.is_running) {
      setTimeout(() => {
        void pollActivationStatusUntilComplete(activationId)
      }, 100)
    } else {
      const statusPerSite = response.extensions.status_per_site
      sitesAndChanges.value.sites.forEach((site) => {
        const siteStatus = statusPerSite.find((status) => status.site === site.siteId)
        if (siteStatus) {
          site.lastActivationStatus = siteStatus
          recentlyActivatedSites.value.push([site.siteId, siteStatus.state])
        }
      })
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
    if (error instanceof CmkFetchError) {
      const cmkError = error as CmkFetchError
      const statusCode = cmkError.getStatusCode()

      if ([401, 403, 409, 422, 423, 503].includes(statusCode)) {
        activationError.value = getActivationErrorFromFetchError(cmkError)
        activateChangesInProgress.value = false
        return
      }
    }
    await fetchPendingChangesAjax()
    activateChangesInProgress.value = false
    activationError.value = defaultActivationError
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
    .filter((site: Site) => site.changes > 0)
    .filter((site: Site) => !siteSelectionIsDisabled(site))
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
        .map((change: PendingChange) => ({
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
  window.open(props.activate_changes_url, 'main')
}

async function checkIfMenuActive(): Promise<void> {
  if (cmk.popup_menu.is_open('main_menu_changes')) {
    if (!alreadyMadeAjaxCall.value) {
      recentlyActivatedSites.value = []
      activationError.value = null
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

const showNotAllowedMessage = computed((): boolean => {
  /**
   * If all sites (with changes) have at least one foreign change and the user
   * does not have permission to activate foreign changes, show the message.
   */

  if (props.user_has_activate_foreign) {
    return false
  }

  const { sites, pendingChanges } = sitesAndChanges.value
  const sitesWithPendingChanges = sites.filter((site) => site.changes > 0)

  if (sitesWithPendingChanges.length === 0) {
    return false
  }

  return sitesWithPendingChanges.every((site) =>
    pendingChanges.some(
      (change) =>
        change.foreignChange &&
        (change.whichSites.includes(site.siteId) || change.whichSites.includes('All sites'))
    )
  )
})

const userCanActivateSelectedSites = computed((): boolean => {
  return selectedSites.value.every((siteId) => {
    const site = sitesAndChanges.value.sites.find((s) => s.siteId === siteId)
    if (site) {
      const siteHasForeignChanges = sitesAndChanges.value.pendingChanges.some(
        (change) =>
          (change.whichSites.includes(site.siteId) || change.whichSites.includes('All sites')) &&
          change.foreignChange
      )
      if (siteHasForeignChanges && !props.user_has_activate_foreign) {
        return false
      }
    }
    return true
  })
})

const activateChangesButtonDisabled = computed((): boolean => {
  if (sitesAndChanges.value.licenseIsBlocking) {
    return true
  }
  if (!userCanActivateSelectedSites.value) {
    return true
  }
  if (activateChangesInProgress.value) {
    return true
  }
  if (selectedSites.value.length === 0) {
    return true
  }
  if (allSitesWithChangesAreNotSelectable.value) {
    return true
  }
  return !sitesAndChanges.value.sites.some(
    (site) => ['online', 'disabled'].includes(site.onlineStatus) && site.changes > 0
  )
})

const activateChangesButtonTooltip = computed((): string => {
  if (!activateChangesButtonDisabled.value) {
    return ''
  }
  if (sitesAndChanges.value.pendingChanges.length === 0) {
    return _t('No changes available for activation')
  }
  return ''
})

const sitesWithWarningsOrErrors = computed((): boolean => {
  return sitesAndChanges.value.sites.some(
    (site) =>
      site.lastActivationStatus &&
      (site.lastActivationStatus.state === 'warning' || site.lastActivationStatus.state === 'error')
  )
})

const sitesWithErrors = computed((): boolean => {
  return sitesAndChanges.value.sites.some(
    (site) => site.lastActivationStatus && site.lastActivationStatus.state === 'error'
  )
})

const numberOfForeignChanges = computed((): number => {
  // Count the number of pending changes that are foreign (not by the current user)
  return sitesAndChanges.value.pendingChanges.filter((change) => change.user !== props.user_name)
    .length
})

const recentlyActivatedSiteIds = computed((): string[] => {
  return recentlyActivatedSites.value.map(([siteId]) => siteId)
})

const activationSuccessTitle = computed((): string => {
  const numberOfSuccessfullyActivatedSites = recentlyActivatedSites.value.filter(
    ([, status]) => status === 'success' || status === 'warning'
  ).length
  const numberOfChanges = numberOfChangesLastActivation.value

  return _t(
    'Successfully activated %{numberOfChanges} pending %{changeWord} on %{numberOfSuccessfullyActivatedSites} %{siteWord}',
    {
      numberOfChanges,
      numberOfSuccessfullyActivatedSites,
      changeWord: _tn('change', 'changes', numberOfChanges),
      siteWord: _tn('site', 'sites', numberOfSuccessfullyActivatedSites)
    }
  )
})

onMounted(async () => {
  // Fetch once on mount, then again when popup is opened to refresh data.
  // This avoids showing no changes when opening the menu for the first time,
  // while the ajax call is in progress.
  await fetchPendingChangesAjax()
  void checkIfMenuActive()
})
</script>

<template>
  <DefaultPopup class="cmk-default-popup-mainmenu">
    <div class="cmk-default-popup-mainmenu__header">
      <CmkHeading type="h1">{{ _t('Quick activation of pending changes') }}</CmkHeading>
    </div>
    <div class="cmk-div-mainmenu-container">
      <div class="cmk-div-buttons-container">
        <CmkButtonSubmit
          class="cmk-button-submit"
          :disabled="activateChangesButtonDisabled"
          :title="activateChangesButtonTooltip"
          @click="() => activateAllChanges()"
        >
          {{ _t('Activate pending changes') }}
        </CmkButtonSubmit>
        <CmkButton
          variant="secondary"
          class="cmk-button-secondary"
          :href="props.activate_changes_url"
          target="main"
          @click="() => openActivateChangesPage()"
        >
          <CmkIcon variant="inline" name="frameurl" />
          {{ _t('Open full view') }}
        </CmkButton>
      </div>
      <UserSettingDialog v-if="!new_installation" :activate-changes-url="activate_changes_url" />
      <CmkDialog
        v-else
        :message="
          _t(`Changes are saved without affecting live monitoring, allowing you to review and adjust them safely.
              Click 'Activate pending changes' to apply them.`)
        "
        :dismissal_button="{
          title: _t('Do not show again'),
          key: 'changes-info'
        }"
      />
      <CmkAlertBox v-if="showNotAllowedMessage" variant="warning" class="cmk-alert-box">
        {{ _t('Sorry, you are not allowed to activate changes of other users.') }}
      </CmkAlertBox>

      <CmkAlertBox
        v-if="activationError"
        variant="error"
        class="cmk-alert-box"
        :heading="activationError.title"
      >
        {{ activationError.detail }}
      </CmkAlertBox>

      <CmkAlertBox
        v-if="sitesAndChanges.licenseMessage !== null"
        variant="warning"
        class="cmk-alert-box"
      >
        <CmkHtml :html="sitesAndChanges.licenseMessage" />
      </CmkAlertBox>
      <ChangesActivating
        v-if="activateChangesInProgress"
        :activating-on-sites="
          recentlyActivatedSiteIds.length > 1
            ? recentlyActivatedSiteIds
            : recentlyActivatedSiteIds[0]
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
        :title="activationSuccessTitle"
        :info="_t('Everything is up to date')"
        class="cmk-div-activation-result-container"
      >
      </ChangesActivationResult>
      <CmkDialog
        v-if="sitesWithWarningsOrErrors && !activateChangesInProgress"
        :title="_t('Problems detected during activation')"
        :message="_t('Some things may not be monitored properly.')"
        :buttons="[
          {
            title: _t('Open full view'),
            variant: sitesWithErrors ? 'danger' : 'warning',
            onclick: () => openActivateChangesPage()
          }
        ]"
        :variant="sitesWithErrors ? 'error' : 'warning'"
      />

      <ChangesStatusBar
        v-if="!activateChangesInProgress"
        :activate-changes-url="props.activate_changes_url"
        :pending-changes="sitesAndChanges.pendingChanges.length"
        :activation-issues="sitesWithActivationIssues.length"
        :site-problems="sitesWithStatusProblems.length"
      />

      <div class="cmk-div-sites-and-pending-changes-container">
        <SiteStatusList
          v-model="selectedSites"
          :sites="sitesAndChanges.sites"
          :open="activationStatusCollapsible"
          :activating="activateChangesInProgress"
          :recently-activated-sites="recentlyActivatedSiteIds"
          :pending-changes="sitesAndChanges.pendingChanges"
          :user-has-activate-foreign="props.user_has_activate_foreign"
        ></SiteStatusList>
        <PendingChangesList
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
div.cmk-dialog {
  width: 100%;
}

div.cmk-alert-box {
  box-sizing: border-box;
  width: 100%;
}

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
  flex-direction: column;
  align-items: flex-start;
  flex: 1;
  min-height: 0;
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
  flex: 1 1 0;
  min-height: 0;
  overflow: hidden;
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
  flex: 1;
  min-height: 0;
  overflow: hidden;
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
  flex: 0 0 auto;
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
