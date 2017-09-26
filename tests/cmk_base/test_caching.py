import cmk_base.caching

def test_cache_manager():
    cache = cmk_base.caching.CacheManager()


def test_create_dict_cache():
    mgr = cmk_base.caching.CacheManager()

    assert not mgr.exists("test_dict")
    cache = mgr.get_dict("test_dict")
    assert mgr.exists("test_dict")

    assert isinstance(cache, dict)
    assert isinstance(cache, cmk_base.caching.DictCache)
    assert isinstance(cache, cmk_base.caching.Cache)


def test_create_set_cache():
    mgr = cmk_base.caching.CacheManager()

    assert not mgr.exists("test")
    cache = mgr.get_set("test")
    assert mgr.exists("test")

    assert isinstance(cache, set)
    assert isinstance(cache, cmk_base.caching.SetCache)
    assert isinstance(cache, cmk_base.caching.Cache)


def test_create_list_cache():
    mgr = cmk_base.caching.CacheManager()

    assert not mgr.exists("test")
    cache = mgr.get_list("test")
    assert mgr.exists("test")

    assert isinstance(cache, list)
    assert isinstance(cache, cmk_base.caching.ListCache)
    assert isinstance(cache, cmk_base.caching.Cache)


def test_clear_all():
    mgr = cmk_base.caching.CacheManager()

    list_cache = mgr.get_list("test_list")
    assert list_cache.is_empty()

    list_cache.append("123")
    list_cache += [ "1", "2" ]
    assert not list_cache.is_empty()


    dict_cache = mgr.get_dict("test_dict")
    assert dict_cache.is_empty()

    dict_cache["asd"] = 1
    dict_cache.update({"a": 1, "b": 3})
    assert not dict_cache.is_empty()


    set_cache = mgr.get_set("test_set")
    assert set_cache.is_empty()

    set_cache.add("1")
    set_cache.add("1")
    assert not set_cache.is_empty()

    mgr.clear_all()
    assert list_cache.is_empty()
    assert dict_cache.is_empty()
    assert set_cache.is_empty()


def test_populated():
    mgr = cmk_base.caching.CacheManager()

    cache = mgr.get_set("test1")
    assert not cache.is_populated()
    cache.set_populated()
    assert cache.is_populated()

    cache = mgr.get_dict("test2")
    assert not cache.is_populated()
    cache.set_populated()
    assert cache.is_populated()

    cache = mgr.get_list("test3")
    assert not cache.is_populated()
    cache.set_populated()
    assert cache.is_populated()
