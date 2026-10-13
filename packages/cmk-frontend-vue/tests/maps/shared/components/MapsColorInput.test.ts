/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { describe, expect, it } from 'vitest'

import MapsColorInput from '@/maps/shared/components/MapsColorInput.vue'

import { mapsGlobal } from '../../support/services'

function renderInput(props: Record<string, unknown> = {}) {
  return render(MapsColorInput, {
    props: { modelValue: '#ff0000', defaultColor: '#000000', ...props },
    global: mapsGlobal()
  })
}

/** The hex field; the colour picker beside it is an ``input[type=color]``. */
function hexField(): HTMLInputElement {
  return screen.getByRole('textbox')
}

describe('MapsColorInput – typing a colour', () => {
  it('stays editable while the field is empty, which is how retyping starts', async () => {
    // An empty field used to read as "no colour", which switches the input off
    // -- so selecting the value to type a new one disabled the very control
    // being typed in.
    const { emitted } = renderInput({ enableLabel: untranslated('Custom color') })

    await userEvent.clear(hexField())

    expect(hexField()).toBeEnabled()
    expect(emitted()['update:modelValue']).toBeUndefined()
  })

  it('keeps a half-typed value to itself', async () => {
    const { emitted } = renderInput({ enableLabel: untranslated('Custom color') })

    await userEvent.clear(hexField())
    await userEvent.type(hexField(), '#ff')

    expect(hexField()).toHaveValue('#ff')
    expect(emitted()['update:modelValue']).toBeUndefined()
  })

  it('hands the colour over once it is a colour', async () => {
    const { emitted } = renderInput({ enableLabel: untranslated('Custom color') })

    await userEvent.clear(hexField())
    await userEvent.type(hexField(), '#00ff00')

    expect(emitted()['update:modelValue']).toContainEqual(['#00ff00'])
  })

  // Without a switch there is nothing else to say "no colour" with, so the
  // emptied field has to mean it.
  it('clears the colour from an emptied field when there is no switch', async () => {
    const { emitted } = renderInput({ noneValue: 'transparent' })

    await userEvent.clear(hexField())

    expect(emitted()['update:modelValue']).toContainEqual(['transparent'])
  })
})
