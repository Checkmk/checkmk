/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { describe, expect, it } from 'vitest'
import { defineComponent, ref } from 'vue'

import FolderContextMenu from '@/maps/map/foldertree/components/FolderContextMenu.vue'

import { aFolderNode } from '../../support/fixtures'

/**
 * A right-click opens the menu and leaves the focus where it was, so the case
 * mounts it the way the map view does -- open, with nothing inside it focused --
 * and closes it by taking the menu away.
 */
const hostComponent = defineComponent({
  components: { FolderContextMenu },
  setup() {
    const open = ref(true)
    const folder = aFolderNode({
      path: '/main/web',
      title: 'Web servers',
      kind: 'folder',
      host_count: 3
    })
    return { open, folder }
  },
  template: `<FolderContextMenu
    v-if="open"
    :folder="folder"
    :x="10"
    :y="10"
    checkmk-url="http://checkmk/site"
    :can-command="true"
    @close="open = false"
  />`
})

describe('FolderContextMenu', () => {
  it('closes on Escape without the operator having to tab into it first', async () => {
    const user = userEvent.setup()
    render(hostComponent)
    expect(screen.getByRole('button', { name: /Folder actions/ })).toBeInTheDocument()

    await user.keyboard('{Escape}')

    expect(screen.queryByRole('button', { name: /Folder actions/ })).toBeNull()
  })
})
