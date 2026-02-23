<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type Ref, onMounted, ref } from 'vue'

import { cmkAjax } from '@/lib/ajax'
import usei18n from '@/lib/i18n'

import CmkHtml from '@/components/CmkHtml.vue'
import CmkIcon from '@/components/CmkIcon'
import CmkIconButton from '@/components/CmkIconButton.vue'

import { useInjectCmkToken } from '@/dashboard/composables/useCmkToken'
import { useSuppressEventOnPublicDashboard } from '@/dashboard/composables/useIsPublicDashboard'

import DashboardContentContainer from './DashboardContentContainer.vue'
import type { ContentProps } from './types.ts'

// eslint-disable-next-line @typescript-eslint/naming-convention
declare let global_csrf_token: string

const { _t } = usei18n()

const headers: string[] = [_t('Actions'), _t('Message'), _t('Sent on'), _t('Expires on')]

defineProps<ContentProps>()
const cmkToken = useInjectCmkToken()
const suppressEventOnPublicDashboard = useSuppressEventOnPublicDashboard()

type UserMessage = {
  id: string
  text: {
    content_type: string
    content: string
  }
  time: number
  valid_till: number
  acknowledged: boolean
  security: boolean
}

const messages: Ref<UserMessage[]> = ref([])
const fetchData = async (): Promise<void> => {
  let getMessagesEndpointUrl: string
  if (cmkToken === undefined) {
    getMessagesEndpointUrl = `ajax_get_user_messages.py`
  } else {
    const httpVarsString: string = new URLSearchParams({ 'cmk-token': cmkToken }).toString()
    getMessagesEndpointUrl = `get_user_messages_token_auth.py?${httpVarsString}`
  }
  messages.value = await cmkAjax(getMessagesEndpointUrl, {})
}

onMounted(async () => {
  await fetchData()
})

const acknowledgedMsgIds: Ref<string[]> = ref([])
const deletedMsgIds: Ref<string[]> = ref([])

async function postUserMessageAction(actionType: string, msg: UserMessage): Promise<void> {
  const csrfToken = global_csrf_token
  await cmkAjax(`ajax_user_message_action.py`, {
    action_type: actionType,
    msg_id: msg.id,
    _csrf_token: csrfToken
  })

  switch (actionType) {
    case 'acknowledge':
      acknowledgedMsgIds.value.push(msg.id)
      break
    case 'delete':
      deletedMsgIds.value.push(msg.id)
  }
}

function formatTimestamp(timestamp: number): string {
  // Return date and time in human readable format, e.g. "2025-06-17 10:38:04"
  const dateObject = new Date(timestamp * 1000)
  const date: number[] = [dateObject.getFullYear(), dateObject.getMonth() + 1, dateObject.getDate()]
  const time: number[] = [dateObject.getHours(), dateObject.getMinutes(), dateObject.getSeconds()]

  // Add leading zero to values < 10
  const dateStr: string[] = []
  date.forEach((val, i) => {
    dateStr[i] = (val < 10 ? '0' : '') + val
  })
  const timeStr: string[] = []
  time.forEach((val, i) => {
    timeStr[i] = (val < 10 ? '0' : '') + val
  })

  const dateHumanReadable = dateStr.join('-')
  const timeHumanReadable = timeStr.join(':')
  return `${dateHumanReadable} ${timeHumanReadable}`
}
</script>

<template>
  <DashboardContentContainer :effective-title="effectiveTitle" :general_settings="general_settings">
    <div
      @click.capture="suppressEventOnPublicDashboard"
      @auxclick.capture="suppressEventOnPublicDashboard"
      @mousedown.capture="suppressEventOnPublicDashboard"
      @keydown.capture="suppressEventOnPublicDashboard"
      @wheel.capture="suppressEventOnPublicDashboard"
    >
      <table v-if="messages!.length" class="db-content-user-messages__table">
        <tbody>
          <tr>
            <th v-for="(header, index) in headers" :key="index">{{ header }}</th>
          </tr>
          <tr
            v-for="msg in messages!.filter((msg_) => !deletedMsgIds.includes(msg_.id))"
            :key="msg.id"
          >
            <td class="db-content-user-messages__buttons">
              <CmkIcon
                v-if="msg.acknowledged || acknowledgedMsgIds.includes(msg.id)"
                name="checkmark"
                :title="_t('Acknowledged')"
                variant="inline"
                class="db-content-user-messages__icon-acknowledged"
              />
              <CmkIconButton
                v-else
                name="werk-ack"
                :title="_t('Acknowledge message')"
                variant="inline"
                size="xlarge"
                @click="postUserMessageAction('acknowledge', msg)"
              />
              <CmkIcon
                v-if="msg.security === true"
                name="delete"
                :title="_t('Cannot be deleted manually, must expire')"
                variant="inline"
                :colored="false"
              />
              <CmkIconButton
                v-else
                name="delete"
                :title="_t('Delete')"
                variant="inline"
                @click="postUserMessageAction('delete', msg)"
              />
            </td>
            <td>
              <span v-if="msg.text.content_type === 'text'">{{ msg.text.content }}</span>
              <!-- Due to its sanitization CmkHtml may render the given content differently than it
                   was rendered before by the backend code -->
              <CmkHtml v-else :html="msg.text.content" />
            </td>
            <td>{{ formatTimestamp(msg.time) }}</td>
            <td>{{ msg.valid_till ? formatTimestamp(msg.valid_till) : '-' }}</td>
          </tr>
        </tbody>
      </table>
      <div v-else class="db-content-user-messages__no-messages">
        {{ _t('Currently you have no received messages') }}
      </div>
    </div>
  </DashboardContentContainer>
</template>

<style scoped>
.db-content-user-messages__table {
  width: 100%;
  border-collapse: collapse;
  border-spacing: 0;
  empty-cells: show;

  tr {
    overflow: hidden;
    box-sizing: border-box;
    transition: all 0.15s ease-in;

    &:nth-child(even) {
      background-color: var(--even-tr-bg-color);
    }

    &:nth-child(odd) {
      background-color: var(--odd-tr-bg-color);
    }

    th {
      height: 26px;
      padding: 2px 8px;
      letter-spacing: 1px;
      text-align: left;
      vertical-align: middle;
      color: var(--font-color-dimmed);
      background-color: var(--odd-tr-bg-color);
    }

    td {
      height: 26px;
      padding: 2px 8px;
      text-overflow: ellipsis;
      vertical-align: middle;

      &.db-content-user-messages__buttons {
        width: 1%;
        white-space: nowrap;
      }
    }
  }
}

.db-content-user-messages__no-messages {
  padding: var(--spacing);
}

.db-content-user-messages__icon-acknowledged {
  margin-right: var(--spacing);
}
</style>
