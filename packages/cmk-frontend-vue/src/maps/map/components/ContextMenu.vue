<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed, nextTick, onMounted, ref } from 'vue'

import type { MapElement, ObjectState } from '@/maps/types/api'
import { objectTypeLabel } from '@/maps/utils/dropdownOptions'
import { buildCheckmkViewUrl } from '@/maps/utils/mapNavigation'
import { getEffectiveObjectType, getMapElementName } from '@/maps/utils/naming'
import { sanitizeTemplateHtml } from '@/maps/utils/sanitize'
import { interpolateTemplate } from '@/maps/utils/template'

const { _t } = usei18n()

const props = defineProps<{
  object: MapElement
  state?: ObjectState
  x: number
  y: number
  checkmkUrl?: string | null
  showEdit?: boolean
  editMode?: boolean
  template?: string | null
}>()

const emit = defineEmits<{
  close: []
  edit: []
  duplicate: []
  delete: []
  straighten: []
  detach: []
}>()

// Menu keyboard support: the invoking element is a canvas object, so focus
// moves into the menu on open (there is no DOM element to restore it to).
const menuEl = ref<HTMLElement | null>(null)

function menuItems(): HTMLElement[] {
  return Array.from(menuEl.value?.querySelectorAll<HTMLElement>('[role="menuitem"]') ?? [])
}

onMounted(async () => {
  await nextTick()
  ;(menuItems()[0] ?? menuEl.value)?.focus()
})

function onMenuKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    e.preventDefault()
    emit('close')
    return
  }
  const items = menuItems()
  if (items.length === 0) {
    return
  }
  const idx = items.indexOf(document.activeElement as HTMLElement)
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    items[(idx + 1) % items.length]?.focus()
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    items[(idx - 1 + items.length) % items.length]?.focus()
  } else if (e.key === 'Home') {
    e.preventDefault()
    items[0]?.focus()
  } else if (e.key === 'End') {
    e.preventDefault()
    items[items.length - 1]?.focus()
  }
}

// A bent line can be straightened back to a direct two-point line.
const lineHasBend = computed(
  () =>
    props.object.type === 'line' &&
    props.object.mid_x !== null &&
    props.object.mid_x !== undefined &&
    props.object.mid_y !== null &&
    props.object.mid_y !== undefined
)

// Show detach only for a bound line and only where the user can edit.
const lineHasBinding = computed(
  () =>
    props.object.type === 'line' &&
    (!!props.object.start_ref || !!props.object.end_ref) &&
    (props.showEdit || props.editMode)
)

const renderedTemplate = computed(() =>
  props.template
    ? sanitizeTemplateHtml(interpolateTemplate(props.template, props.object, props.state))
    : null
)

// "Show problem services" is only useful when the host actually has problem
// services to drill into.
const _OK_STATES = new Set(['UP', 'OK', 'PENDING'])
const isProblematic = computed(
  () => props.state !== undefined && !_OK_STATES.has(props.state.state)
)

const displayName = computed(() => getMapElementName(props.object) ?? '')

const site = computed(() => props.state?.site_id ?? null)

const hostUrl = computed(() => {
  if (!props.object.host_name) {
    return null
  }
  return buildCheckmkViewUrl(
    props.checkmkUrl,
    'hoststatus',
    { host: props.object.host_name },
    { site: site.value }
  )
})

const serviceUrl = computed(() => {
  if (!props.object.host_name || !props.object.service_description) {
    return null
  }
  return buildCheckmkViewUrl(
    props.checkmkUrl,
    'service',
    { host: props.object.host_name, service: props.object.service_description },
    { site: site.value }
  )
})

const groupUrl = computed(() => {
  if (!props.object.group_name) {
    return null
  }
  const view = props.object.type === 'hostgroup' ? 'hostgroup' : 'servicegroup'
  return buildCheckmkViewUrl(
    props.checkmkUrl,
    view,
    { [view]: props.object.group_name },
    { site: site.value }
  )
})

const aggregationUrl = computed(() => {
  if (props.object.type !== 'aggregation' || !props.object.aggregation_id) {
    return null
  }
  return buildCheckmkViewUrl(
    props.checkmkUrl,
    'aggr_single',
    { aggr_name: props.object.aggregation_id, po_aggr_expand: '1' },
    { site: site.value }
  )
})

const aggregationOverviewUrl = computed(() => {
  if (props.object.type !== 'aggregation') {
    return null
  }
  return buildCheckmkViewUrl(props.checkmkUrl, 'aggr_all', {}, { site: site.value })
})

const hostServicesUrl = computed(() => {
  if (props.object.type !== 'host' || !props.object.host_name) {
    return null
  }
  if (!isProblematic.value) {
    return null
  }
  // When the host itself is down/unreachable, services can't be checked independently
  const hostState = props.state?.state
  if (hostState === 'DOWN' || hostState === 'UNREACHABLE') {
    return null
  }
  return buildCheckmkViewUrl(
    props.checkmkUrl,
    'host',
    {
      host: props.object.host_name,
      filled_in: 'filter',
      _active: 'serviceregex;svcstate;host;siteopt',
      st1: 'on',
      st2: 'on',
      st3: 'on',
      stp: 'on'
    },
    { site: site.value }
  )
})
</script>

<template>
  <div
    ref="menuEl"
    class="maps-context-menu"
    role="menu"
    :aria-label="displayName"
    tabindex="-1"
    :style="{ left: `${x}px`, top: `${y}px` }"
    @keydown="onMenuKeydown"
  >
    <div class="maps-context-menu__header">
      <p class="maps-context-menu__name">
        {{ displayName }}
      </p>
      <p class="maps-context-menu__type">
        {{ objectTypeLabel(getEffectiveObjectType(object), _t) }}
      </p>
    </div>

    <!-- eslint-disable-next-line vue/no-v-html -- content is sanitized via sanitizeTemplateHtml -->
    <div v-if="renderedTemplate" class="maps-context-menu__template" v-html="renderedTemplate" />

    <a
      v-if="hostUrl"
      :href="hostUrl"
      target="_blank"
      rel="noopener noreferrer"
      role="menuitem"
      class="maps-context-menu__item"
    >
      <svg
        class="maps-context-menu__icon"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        stroke-width="2"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25"
        />
      </svg>
      <span>{{ _t('Host in Checkmk') }}</span>
    </a>
    <a
      v-if="hostServicesUrl"
      :href="hostServicesUrl"
      target="_blank"
      rel="noopener noreferrer"
      role="menuitem"
      class="maps-context-menu__item"
    >
      <svg
        class="maps-context-menu__icon"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        stroke-width="2"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
        />
      </svg>
      <span>{{ _t('Problem services') }}</span>
    </a>
    <a
      v-if="serviceUrl"
      :href="serviceUrl"
      target="_blank"
      rel="noopener noreferrer"
      role="menuitem"
      class="maps-context-menu__item"
    >
      <svg
        class="maps-context-menu__icon"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        stroke-width="2"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25"
        />
      </svg>
      <span>{{ _t('Service in Checkmk') }}</span>
    </a>
    <a
      v-if="groupUrl"
      :href="groupUrl"
      target="_blank"
      rel="noopener noreferrer"
      role="menuitem"
      class="maps-context-menu__item"
    >
      <svg
        class="maps-context-menu__icon"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        stroke-width="2"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25"
        />
      </svg>
      <span>{{ _t('Group in Checkmk') }}</span>
    </a>
    <a
      v-if="aggregationUrl"
      :href="aggregationUrl"
      target="_blank"
      rel="noopener noreferrer"
      role="menuitem"
      class="maps-context-menu__item"
    >
      <svg
        class="maps-context-menu__icon"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        stroke-width="2"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25"
        />
      </svg>
      <span>{{ _t('Aggregation tree in Checkmk') }}</span>
    </a>
    <a
      v-if="aggregationOverviewUrl"
      :href="aggregationOverviewUrl"
      target="_blank"
      rel="noopener noreferrer"
      role="menuitem"
      class="maps-context-menu__item"
    >
      <svg
        class="maps-context-menu__icon"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        stroke-width="2"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5"
        />
      </svg>
      <span>{{ _t('All aggregations in Checkmk') }}</span>
    </a>

    <div
      v-if="
        !hostUrl && !hostServicesUrl && !serviceUrl && !groupUrl && !aggregationUrl && !checkmkUrl
      "
      class="maps-context-menu__empty"
    >
      {{ _t('No Checkmk URL configured') }}
    </div>

    <!-- Operational actions (ack, downtime, force-check, comment, notifications)
             live exclusively in the detail drawer to avoid two competing paths
             for the same operation. In view mode right-click is navigation only;
             edit/duplicate/delete are gated on edit mode via showEdit. -->

    <div class="maps-context-menu__footer" role="none">
      <button
        v-if="lineHasBinding"
        role="menuitem"
        class="maps-context-menu__item"
        @click="$emit('detach')"
      >
        <svg
          class="maps-context-menu__icon"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          stroke-width="2"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25"
          />
        </svg>
        {{ _t('Detach from object') }}
      </button>
      <button
        v-if="showEdit && lineHasBend"
        role="menuitem"
        class="maps-context-menu__item"
        @click="$emit('straighten')"
      >
        <svg
          class="maps-context-menu__icon"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          stroke-width="2"
        >
          <path stroke-linecap="round" stroke-linejoin="round" d="M4 18L20 6" />
        </svg>
        {{ _t('Remove bend') }}
      </button>
      <button
        v-if="showEdit"
        role="menuitem"
        class="maps-context-menu__item"
        @click="$emit('edit')"
      >
        <svg
          class="maps-context-menu__icon"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          stroke-width="2"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125"
          />
        </svg>
        {{ _t('Edit properties') }}
      </button>
      <button
        v-if="showEdit"
        role="menuitem"
        class="maps-context-menu__item"
        @click="$emit('duplicate')"
      >
        <svg
          class="maps-context-menu__icon"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          stroke-width="2"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M15.75 17.25v3.375c0 .621-.504 1.125-1.125 1.125h-9.75a1.125 1.125 0 01-1.125-1.125V7.875c0-.621.504-1.125 1.125-1.125H6.75a9.06 9.06 0 011.5.124m7.5 10.376h3.375c.621 0 1.125-.504 1.125-1.125V11.25c0-4.46-3.243-8.161-7.5-8.876a9.06 9.06 0 00-1.5-.124H9.375c-.621 0-1.125.504-1.125 1.125v3.5m7.5 10.375H9.375a1.125 1.125 0 01-1.125-1.125v-9.25m12 6.625v-1.875a3.375 3.375 0 00-3.375-3.375h-1.5a1.125 1.125 0 01-1.125-1.125v-1.5a3.375 3.375 0 00-3.375-3.375H9.75"
          />
        </svg>
        {{ _t('Duplicate') }}
      </button>
      <button
        v-if="showEdit"
        role="menuitem"
        class="maps-context-menu__item maps-context-menu__item--danger"
        @click="$emit('delete')"
      >
        <svg
          class="maps-context-menu__icon"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          stroke-width="2"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0"
          />
        </svg>
        {{ _t('Delete') }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.maps-context-menu {
  position: fixed;
  z-index: 50;
  min-width: 192px;
  padding: 6px 0;
  background: var(--maps-map-view-glass);
  backdrop-filter: blur(12px);
  border-radius: 12px;
  box-shadow:
    0 0 0 1px var(--default-border-color),
    0 25px 50px -12px rgb(0 0 0 / 60%);
}

.maps-context-menu__header {
  margin-bottom: var(--dimension-3);
  padding: var(--dimension-4) 14px;
  border-bottom: 1px solid var(--default-border-color);
}

.maps-context-menu__name {
  overflow: hidden;
  max-width: 208px;
  font-size: var(--font-size-normal);
  line-height: 16px;
  font-weight: var(--font-weight-bold);
  color: var(--font-color);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.maps-context-menu__type {
  margin-top: var(--dimension-2);
  font-size: var(--font-size-small);
  color: var(--font-color-dimmed);
}

.maps-context-menu__template {
  /* See HoverMenu: paint containment is what keeps a template inside its card. */
  contain: paint;
  margin-bottom: var(--dimension-3);
  padding: var(--dimension-4) 14px;
  font-size: var(--font-size-normal);
  line-height: 16px;
  color: var(--font-color);
  border-bottom: 1px solid var(--default-border-color);
}

.maps-context-menu__item {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
  width: 100%;
  padding: var(--dimension-4) 14px;
  font-size: var(--font-size-large);
  line-height: 20px;
  color: var(--font-color-dimmed);
  text-align: left;
  transition:
    color 0.15s,
    background-color 0.15s;
}

.maps-context-menu__item:hover {
  color: var(--font-color);
  background: var(--input-hover-bg-color);
}

.maps-context-menu:focus-visible,
.maps-context-menu__item:focus-visible {
  outline: 2px solid var(--color-corporate-green-50);
  outline-offset: 2px;
}

.maps-context-menu__item--danger {
  color: var(--color-light-red-40);
}

.maps-context-menu__item--danger:hover {
  color: var(--color-light-red-40);
  background: color-mix(in srgb, var(--color-light-red-50) 8%, transparent);
}

.maps-context-menu__icon {
  flex-shrink: 0;
  width: 14px;
  height: 14px;
}

.maps-context-menu__empty {
  padding: var(--dimension-4) 14px;
  font-size: var(--font-size-normal);
  line-height: 16px;
  font-style: italic;
  color: var(--font-color-dimmed);
}

.maps-context-menu__footer {
  margin-top: var(--dimension-3);
  padding-top: var(--dimension-3);
  border-top: 1px solid var(--default-border-color);
}
</style>
