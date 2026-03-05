<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import { Api } from '@/lib/api-client'
import usei18n from '@/lib/i18n'
import usePersistentRef from '@/lib/usePersistentRef'

import CmkAlertBox from '@/components/CmkAlertBox.vue'
import CmkDialog from '@/components/CmkDialog.vue'

const { _t } = usei18n()

// eslint-disable-next-line @typescript-eslint/naming-convention
declare let global_csrf_token: string

const props = defineProps<{ activateChangesUrl: string }>()

const restAPI = new Api('', [['Content-Type', 'application/json']])

const dismissed = usePersistentRef(
  'user-settings-changes-dialog',
  false,
  (v) => v as boolean,
  'session'
)
const successSlideout = ref<boolean>(false)
const successFullPage = ref<boolean>(false)
const error = ref<string | null>(null)
const loading = ref<boolean>(false)

async function setFullPage() {
  dismiss()
  loading.value = true
  error.value = null
  try {
    await restAPI.put(`ajax_set_change_action_full_page.py`, {
      _csrf_token: encodeURIComponent(global_csrf_token)
    })
  } catch (e) {
    error.value = (e as Error).message
    undismiss()
  }

  loading.value = false
  successFullPage.value = true
}

function setQuickActivation() {
  successSlideout.value = true

  dismiss()
}

function goToFullPage() {
  location.href = `index.py?start_url=${encodeURI(props.activateChangesUrl)}`
}

function dismiss() {
  dismissed.value = true
}

function undismiss() {
  dismissed.value = false
}
</script>
<template>
  <CmkDialog
    v-if="!dismissed"
    :title="_t('Working with a complex environment?')"
    :message="
      _t(
        `In complex environments, activation issues are more common and may require closer review.\n` +
          `The full \'Activation changes\'-page gives you better visibility before activating.`
      )
    "
    :buttons="[
      {
        title: _t('Keep quick activation'),
        variant: 'optional',
        onclick: setQuickActivation
      },
      {
        title: _t('Set full activation page as default'),
        variant: 'optional',
        onclick: setFullPage
      }
    ]"
    class="mm-user-setting-dialog"
  ></CmkDialog>
  <CmkAlertBox v-if="loading" variant="loading">{{ _t('Applying user setting...') }}</CmkAlertBox>
  <CmkAlertBox
    v-if="successSlideout"
    variant="success"
    :title="_t('Preference saved.')"
    :dismissible="true"
  >
    {{ _t("Clicking on 'Changes' will continue to open the quick activation.") }}
    <br />
    {{ _t('You can change this at any time in your profile settings.') }}
  </CmkAlertBox>
  <CmkDialog
    v-if="successFullPage"
    variant="success"
    :title="_t('Preference saved.')"
    :message="
      _t(
        `Clicking on 'Changes' will now open the full 'Activate changes' page.\n` +
          `You can change this at any time in your profile settings.`
      )
    "
    :buttons="[
      {
        title: _t('Open full activation page'),
        variant: 'primary',
        onclick: goToFullPage
      }
    ]"
    class="mm-user-setting-dialog"
  ></CmkDialog>
  <CmkAlertBox v-if="error" variant="error" :title="_t('Could not apply user setting.')">
    {{ error }}
  </CmkAlertBox>
</template>
<style scoped>
.mm-user-setting-dialog {
  display: flex;
}
</style>
