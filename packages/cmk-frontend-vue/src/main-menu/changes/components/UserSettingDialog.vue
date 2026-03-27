<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref, watch } from 'vue'

import { Api } from '@/lib/api-client'
import usei18n from '@/lib/i18n'

import CmkAlertBox from '@/components/CmkAlertBox.vue'
import CmkDialog from '@/components/CmkDialog.vue'

const { _t } = usei18n()

// eslint-disable-next-line @typescript-eslint/naming-convention
declare let global_csrf_token: string

const props = defineProps<{
  activateChangesUrl: string
  changesAction: string
  userName: string
}>()

const restAPI = new Api('', [['Content-Type', 'application/json']])

const currentChangesAction = ref<string>(props.changesAction)
watch(
  () => props.changesAction,
  (val) => {
    currentChangesAction.value = val
  }
)

const successSlideout = ref<boolean>(false)
const successFullPage = ref<boolean>(false)
const error = ref<string | null>(null)
const loading = ref<boolean>(false)

async function setChangesAction(action: 'full_page' | 'slideout') {
  loading.value = true
  error.value = null
  try {
    await restAPI.put(`ajax_set_change_action.py`, {
      _csrf_token: encodeURIComponent(global_csrf_token),
      action
    })

    if (action === 'full_page') {
      successFullPage.value = true
    } else {
      successSlideout.value = true
    }
    currentChangesAction.value = action
  } catch (e) {
    error.value = (e as Error).message
  }
  loading.value = false
}

function goToFullPage() {
  location.href = `index.py?start_url=${encodeURI(props.activateChangesUrl)}`
}
</script>
<template>
  <CmkDialog
    v-if="!currentChangesAction && !loading"
    :title="_t('Working with a complex environment?')"
    :message="
      _t(
        `In complex environments, activation issues are more common and may require closer review.\n` +
          `The full \'Activation changes\' page gives you better visibility before activating.`
      )
    "
    :buttons="[
      {
        title: _t('Keep quick activation'),
        variant: 'optional',
        onclick: () => setChangesAction('slideout')
      },
      {
        title: _t('Set full activation page as default'),
        variant: 'optional',
        onclick: () => setChangesAction('full_page')
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
