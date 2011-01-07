import bi

pagehandlers.update({
    "bi_debug" :          bi.page_debug,
    "bi" :                bi.page_all,
    "bi_set_assumption" : bi.ajax_set_assumption,
})
