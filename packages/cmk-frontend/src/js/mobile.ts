/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/* eslint-disable import-x/no-namespace -- Needed for exports */
import type {
  KnownClickAction,
  KnownTSFunction
} from 'cmk-shared-typing/typescript/legacy_frontend_hooks'

import {
  type ClickAction,
  init_click_action_dispatcher,
  prevent_hash_link_navigation,
  register_click_actions
} from './modules/click_action_dispatcher'
import * as forms from './modules/forms'
import {
  type CallableFunction,
  init_callable_ts_functions,
  register_callable_functions
} from './modules/ts_function_dispatcher'

// NOTE: We use an up-to-date version of jQuery from the package-lock.json together
// with a patched version of jQuery mobile to make it compatible with jQuery:
// https://github.com/jquery/jquery-mobile/issues/8662#issuecomment-687738965
require('script-loader!jquery')
require('script-loader!../jquery/jquery.mobile-1.4.5.min.js')

prevent_hash_link_navigation()

/* Disable data-ajax per default, as it makes problems in most
   of our cases */
$(document).ready(function () {
  $('a').attr('data-ajax', 'false')
  $('form').attr('data-ajax', 'false')
  $('div.error').addClass('ui-shadow')
  $('div.success').addClass('ui-shadow')
  $('div.really').addClass('ui-shadow')
  $('div.warning').addClass('ui-shadow')
})

$(document).bind('mobileinit', function () {
  $['mobile'].ajaxEnabled = false
  $['mobile'].hashListeningEnabled = false
})

// Never allow the mobile page to be opened in an iframe. Redirect top page to the current content page.
// This will result in a full screen mobile interface page.
if (top != self) {
  window.top!.location.href = location.toString()
}

$(document).ready(function () {
  $('a:not(.results_button)').click(function (event) {
    event.preventDefault()
    window.location.href = $(this).attr('href') as string
  })
})

register_callable_functions({
  confirm_dialog_form_submit: (_node, options) =>
    forms.confirm_dialog_form_submit(options.dialog_options, options.form_id, options.cancel_url),
  enable_submit_buttons_on_nonempty_input: (_node, options) =>
    forms.enable_submit_buttons_on_nonempty_input(
      document.getElementById(options.input_id) as HTMLInputElement,
      options.button_ids
    ),
  mobile_disable_ajax_links: (_node, options) => {
    $(options.selector).attr('data-ajax', 'false')
  },
  mobile_dataset_table_init: () => {
    $('table.dataset > tbody > tr.data > td')
      .addClass('ui-shadow')
      .not('.state')
      .addClass('nonstatus')
    $('table.dataset > tbody > tr.data a').attr('data-ajax', 'false')
  },
  mobile_filter_form_init: () => {
    const filter_form = document.getElementById('form_filter') as HTMLFormElement
    const results_button = document.getElementsByClassName('results_button')[0] as HTMLElement
    forms.enable_select2_dropdowns(filter_form)
    results_button.onclick = (event) => {
      event.preventDefault()
      filter_form.submit()
    }
  },
  mobile_command_form_init: () => {
    $(document).ready(function () {
      $('.command_group').has('x').trigger('expand')
      $('x').children().css('background-color', '#f84')
    })
  }
} satisfies Partial<Record<KnownTSFunction, CallableFunction>>)

register_click_actions({
  reload_page: () => location.reload()
} satisfies Partial<Record<KnownClickAction, ClickAction>>)

$(document).ready(function () {
  init_callable_ts_functions(document)
  init_click_action_dispatcher()
})

export const cmk_export = {
  cmk: {
    forms: forms
  }
}
