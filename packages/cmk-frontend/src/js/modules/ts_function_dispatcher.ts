/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type CallableFunctionArguments = { [key: string]: any }
export type CallableFunction = (
  node: HTMLElement,
  options: CallableFunctionArguments
) => void | Promise<void>

const SELECTOR = '*[data-cmk_call_ts_function]'
const registry: { [name: string]: CallableFunction } = {}
const processed = new WeakSet<HTMLElement>()

function call_ts_function(container: HTMLElement) {
  if (processed.has(container)) return
  processed.add(container)

  const data = container.dataset
  const function_name: string = data.cmk_call_ts_function!
  const ts_function = registry[function_name]
  if (ts_function === undefined) {
    console.error(`Unknown callable TS function: ${function_name}`)
    return
  }
  try {
    const args: CallableFunctionArguments = data.cmk_call_ts_arguments
      ? JSON.parse(data.cmk_call_ts_arguments)
      : {}
    const result = ts_function(container, args)
    if (result instanceof Promise) {
      result.catch((e) => console.error(`${function_name} failed:`, e))
    }
  } catch (e) {
    console.error(`${function_name} failed:`, e)
  }
}

export function register_callable_functions(functions: { [name: string]: CallableFunction }) {
  Object.assign(registry, functions)
}

export function init_callable_ts_functions(element: Element | Document) {
  if (element instanceof HTMLElement && element.matches(SELECTOR)) {
    call_ts_function(element)
  }
  element.querySelectorAll<HTMLElement>(SELECTOR).forEach((container) => {
    call_ts_function(container)
  })
}
