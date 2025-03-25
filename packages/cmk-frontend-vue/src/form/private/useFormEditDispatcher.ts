/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import { h, inject, type Component } from 'vue'
import type { InjectionKey } from 'vue'

export const dispatcherKey = Symbol() as InjectionKey<Component>

export function useFormEditDispatcher() {
  // we do all this stuff to resolve our circular dependencies: FormEdit needs
  // FormDictionary to render a dictionary, but FormDictionary also needs FormEdit to
  // render an arbitrary Form.
  // FormEdit has two responsibilities: providing the FormEditDispatcher to all child
  // components via vue dependency injection, and rendering the form (using FormEditDispatcher).
  // FormDictionary can then request the provided dependency (FormEditDispatcher) and use this
  // to render arbitrary forms, without the need to import FormEdit or FormEditDispatcher.
  return {
    FormEditDispatcher: inject(
      dispatcherKey,
      h(
        'span',
        {
          style: 'background-color: red'
        },
        ['Composite form components can only be used with FormEdit as their root element.']
      )
    )
  }
}
