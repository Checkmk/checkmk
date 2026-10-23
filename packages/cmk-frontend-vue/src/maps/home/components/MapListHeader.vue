<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<!--
The map list's own page header: what this page is, and what can be done to the
list as a whole.

``maps.py`` renders no heading and no page menu (see cmk/maps/gui/_pages.py) --
the SPA routes between the list, a map and the image library client side, and
server chrome cannot follow that. So the app owns its chrome, the way the
dashboard does. It is laid out like the global settings page Maps' own settings
open in: breadcrumb, title, then one bar with the list's controls on the left
and the page's actions on the right.

Adding a map is what this page exists for, so it is the one button. Importing
one, the image library and the settings are reached rarely enough not to spend
the bar's width on -- they sit in the overflow menu.
-->
<script setup lang="ts">
import CmkBreadcrumb from 'cmk-ui-library/components/CmkBreadcrumb'
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { DropdownMenuItem, DropdownMenuSeparator } from 'reka-ui'

import { useAuth, useNavigation } from '@/maps/services/context'
import { useMapsBreadcrumbRoot } from '@/maps/shared/breadcrumb'
import MapsOverflowMenu from '@/maps/shared/components/MapsOverflowMenu.vue'
import { useMapsPageLinks } from '@/maps/shared/pageLinks'

const emit = defineEmits<{
  create: []
  import: []
}>()

const { _t } = usei18n()
const auth = useAuth()
const nav = useNavigation()
const links = useMapsPageLinks()

// The list is where the SPA starts, so its own level is the last one: below it
// the views route client side and carry their breadcrumb themselves.
const breadcrumb = [
  ...useMapsBreadcrumbRoot(),
  { title: _t('Maps'), link: nav.href({ view: 'home' }) }
]
</script>

<template>
  <div class="maps-map-list-header">
    <CmkBreadcrumb :items="breadcrumb" />
    <CmkHeading>{{ _t('Maps') }}</CmkHeading>

    <div class="maps-map-list-header__bar">
      <slot />

      <div class="maps-map-list-header__actions">
        <CmkButton
          v-if="auth.canCreateMaps.value"
          variant="primary"
          :icon="{ name: 'new', size: 'small' }"
          @click="emit('create')"
        >
          {{ _t('Add map') }}
        </CmkButton>

        <MapsOverflowMenu
          v-if="auth.canCreateMaps.value || auth.canConfigure.value"
          :label="_t('More actions')"
        >
          <DropdownMenuItem
            v-if="auth.canCreateMaps.value"
            class="maps-overflow-menu__item"
            @select="emit('import')"
          >
            {{ _t('Import map…') }}
          </DropdownMenuItem>
          <template v-if="auth.canConfigure.value">
            <DropdownMenuSeparator
              v-if="auth.canCreateMaps.value"
              class="maps-overflow-menu__separator"
            />
            <DropdownMenuItem
              class="maps-overflow-menu__item"
              @select="nav.navigate({ view: 'admin', tab: 'icons' })"
            >
              {{ _t('Images') }}
            </DropdownMenuItem>
            <!-- Checkmk pages, not SPA views: a full navigation out of the app. -->
            <DropdownMenuItem as-child class="maps-overflow-menu__item">
              <a :href="links.settings">{{ _t('Maps settings') }}</a>
            </DropdownMenuItem>
          </template>
        </MapsOverflowMenu>
      </div>
    </div>
  </div>
</template>

<style scoped>
.maps-map-list-header {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
}

/* The list's controls and the page's actions are two groups, so even a narrow
   bar keeps twice the gap between them that their own items have. */
.maps-map-list-header__bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--dimension-4) var(--dimension-10);
}

.maps-map-list-header__actions {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
  margin-left: auto;
}
</style>
