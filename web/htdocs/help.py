#!/usr/bin/python

import config

def ajax_switch_help():
    config.save_user_file("help", html.var("enabled", "") != "")
