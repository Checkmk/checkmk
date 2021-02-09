#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from functools import lru_cache, wraps


# Used as decorator wrapper for functools.lru_cache in order to bind the cache to an instance method
# rather than the class method.
def instance_method_lru_cache(*cache_args, **cache_kwargs):
    def cache_decorator(func):
        @wraps(func)
        def cache_factory(self, *args, **kwargs):
            instance_cache = lru_cache(*cache_args, **cache_kwargs)(func)
            instance_cache = instance_cache.__get__(self, self.__class__)
            setattr(self, func.__name__, instance_cache)
            return instance_cache(*args, **kwargs)

        return cache_factory

    return cache_decorator
