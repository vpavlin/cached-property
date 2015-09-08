# -*- coding: utf-8 -*-

__author__ = 'Daniel Greenfeld'
__email__ = 'pydanny@gmail.com'
__version__ = '1.2.0'
__license__ = 'BSD'

from time import time
import threading
import json


class cached_property(object):
    """
    A property that is only computed once per instance and then replaces itself
    with an ordinary attribute. Deleting the attribute resets the property.
    Source: https://github.com/bottlepy/bottle/commit/fa7733e075da0d790d809aa3d2f53071897e6f76
    """  # noqa

    def __init__(self, func):
        self.__doc__ = getattr(func, '__doc__')
        self.func = func

    def __get__(self, obj, cls):
        if obj is None:
            return self
        value = obj.__dict__[self.func.__name__] = self.func(obj)
        return value


class threaded_cached_property(object):
    """
    A cached_property version for use in environments where multiple threads
    might concurrently try to access the property.
    """

    def __init__(self, func):
        self.__doc__ = getattr(func, '__doc__')
        self.func = func
        self.lock = threading.RLock()

    def __get__(self, obj, cls):
        if obj is None:
            return self

        obj_dict = obj.__dict__
        name = self.func.__name__
        with self.lock:
            try:
                # check if the value was computed before the lock was acquired
                return obj_dict[name]
            except KeyError:
                # if not, do the calculation and release the lock
                return obj_dict.setdefault(name, self.func(obj))


class cached_property_with_ttl(object):
    """
    A property that is only computed once per instance and then replaces itself
    with an ordinary attribute. Setting the ttl to a number expresses how long
    the property will last before being timed out.
    """

    def __init__(self, ttl=None, store=None):
        if callable(ttl):
            func = ttl
            ttl = None
        else:
            func = None
        self.ttl = ttl
        self.store = local_store(store)

        self._prepare_func(func)

    def __call__(self, func):
        self._prepare_func(func)
        return self

    def __get__(self, obj, cls):
        if obj is None:
            return self

        now = time()
        name = self.__name__
        obj_dict = obj.__dict__
        try:
            value, last_updated = self.store.load_store(name)
            if not last_updated:
                value, last_updated = obj_dict[name]
        except KeyError:
            pass
        else:
            ttl_expired = self.ttl and self.ttl < now - last_updated
            if not ttl_expired:
                return value

        value = self.func(obj)
        value_t = (value, now)
        obj_dict[name] = value_t
        self.store.update_store(value_t, name)

        return value

    def __delete__(self, obj):
        obj.__dict__.pop(self.__name__, None)
        self.store.update_store(None, self.__name__)

    def __set__(self, obj, value):
        value_t = (value, time())
        obj.__dict__[self.__name__] = value_t
        self.store.update_store(value_t, self.__name__)

    def _prepare_func(self, func):
        self.func = func
        if func:
            self.__doc__ = func.__doc__
            self.__name__ = func.__name__
            self.__module__ = func.__module__

# Aliases to make cached_property_with_ttl easier to use
cached_property_ttl = cached_property_with_ttl
timed_cached_property = cached_property_with_ttl


class threaded_cached_property_with_ttl(cached_property_with_ttl):
    """
    A cached_property version for use in environments where multiple threads
    might concurrently try to access the property.
    """

    def __init__(self, ttl=None, store=None):
        super(threaded_cached_property_with_ttl, self).__init__(ttl, store)
        self.lock = threading.RLock()

    def __get__(self, obj, cls):
        with self.lock:
            return super(threaded_cached_property_with_ttl, self).__get__(obj,
                                                                          cls)

# Alias to make threaded_cached_property_with_ttl easier to use
threaded_cached_property_ttl = threaded_cached_property_with_ttl
timed_threaded_cached_property = threaded_cached_property_with_ttl

class local_store(object):
    """
    Stores the given values in a file JSON format to provide caching accross
    script runs (for example when a property contains some remote content)
    """
    def __init__(self, store):
        self.store = store

    def update_store(self, obj, name):
        """Loads store if it exists and adds new property or
           updates existing one with new value"""
        if self.store:
            data = {}
            try:
                with open(self.store, "r") as fp:
                    data = json.load(fp)
            except:
                pass
            with open(self.store, "w") as fp:
                data[name] = (obj)
                json.dump(data, fp)

    def load_store(self, name):
        """Loads cached value from the store"""
        ret = (None, None)
        if self.store:
            try:
                with open(self.store, "r") as fp:
                    data = json.load(fp)
                    ret = data[name]
            except:
                pass
        return ret
