"""Utility functions and decorators."""

import asyncio
import pprint, traceback, functools
import datetime


########################################################################################################################
# A singleton decorator.
def singleton(class_):
    instances = {}

    @functools.wraps(class_)
    def getinstance(*args, **kwargs):
        if class_ not in instances:
            instances[class_] = class_(*args, **kwargs)
        return instances[class_]

    return getinstance


# Example code to dump the exception as it occurs.
def exceptionCatcherForAsyncDecorator():
    def deco(func):
        @functools.wraps(func)
        async def wrapped(*args):
            print('wrap function invoked')
            try:
                return await func(*args)
            except Exception as E:
                print(f'Exception occured at: {datetime.datetime.now()}\n {pprint.pformat(traceback.format_exc())}')
                raise #re-raise exception to allow process in calling function
        return wrapped
    return deco


########################################################################################################################
# Example of one decorator for both async and non-async code
def dec(fn):
    if asyncio.iscoroutinefunction(fn):
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            print(fn, args, kwargs)  # <function foo at 0x10952d598> () {}
            await asyncio.sleep(5)
            print("done with wrapper, going to call fn")
            return await fn()

        return wrapper
    else:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            print(fn, args, kwargs)  # <function bar at 0x108fb5a60> () {}
            time.sleep(5)
            print("done with wrapper, going to call fn")
            return fn()

        return wrapper


########################################################################################################################
# Wrap functionality with pre and post functions.
class WrapAll(object):
    def __init__(self, pre=lambda _: None, post=lambda _: None):
        self.pre = lambda : pre(self)
        self.pre_val = None
        self.result = None
        self.post = lambda : post(self)

    def __call__(self, fn):
        if asyncio.iscoroutinefunction(fn):
            async def wrap(*args, **kwargs):
                self.pre_val = self.pre()
                self.result = await fn(*args, *kwargs)
                self.post()
                return self.result
        else:
            def wrap(*args, **kwargs):
                self.pre_val = self.pre()
                self.result = fn(*args, *kwargs)
                self.post()
                return self.result
        return wrap

#Ex: Timer

timer = dict(
    pre=lambda self: time.time(),
    post=lambda self: print('used {}'.format(time.time()-self.pre_val))
)

@WrapAll(**timer)
def add(x, y):
    return x + y

@WrapAll(**timer)
async def async_add(x, y):
    future = asyncio.Future()
    future.set_result(x+y)
    await future
    return future.result()

# Ex: logger
import asyncio
import logging

FORMAT = '%(message)s'
logging.basicConfig(format=FORMAT)

logger = dict(
    post=lambda self: logging.warning('subtracting {}'.format(self.result))
)

@WrapAll(**logger)
def sub(x, y):
    return x - y

@WrapAll(**logger)
async def async_sub(x, y):
    future = asyncio.Future()
    future.set_result(x-y)
    await future
    return future.result()

#Ex:
########################################################################################################################
