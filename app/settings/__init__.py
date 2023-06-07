# -*- coding: utf-8 -*-

from __future__ import absolute_import
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor

import fakeredis
from honeybadger import honeybadger
from multicall import utils as multicall_utils
import redis.exceptions
from walrus import Database
from environ import Env

# Use a threaded executor...
multicall_utils.process_pool_executor = ThreadPoolExecutor()


env = Env()
if os.path.exists(".env"):
    Env.read_env(".env")


def reset_multicall_pool_executor():
    """Cleanup asyncio leftovers, replace executor to free memory!"""
    multicall_utils.process_pool_executor.shutdown(
        wait=True, cancel_futures=True
    )
    multicall_utils.process_pool_executor = ThreadPoolExecutor()


def honeybadger_handler(req, resp, exc, params):
    """Custom error handler for exception notifications."""
    if exc is None:
        return

    req_data = dict(
        remote_address=req.access_route,
        url=req.uri,
        method=req.method,
        content_type=req.content_type,
        headers=req.headers,
        params=req.params,
        query_string=req.query_string
    )

    honeybadger.notify(exc, context=dict(request=req_data))

    # Use default response handler...
    from ..app import app
    app._python_error_handler(req, resp, exc, params)


# Webserver setup
PORT = env.int("PORT", default=8000)

# Logger setup...
LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.StreamHandler(sys.stdout))
LOGGER.setLevel(env('LOGGING_LEVEL', default='DEBUG'))

# Tokenlists are split with a pipe char (unlikely to be used in URIs)
TOKENLISTS = env('TOKENLISTS', default='').split('|')
DEFAULT_TOKEN_ADDRESS = env('DEFAULT_TOKEN_ADDRESS').lower()
STABLE_TOKEN_ADDRESS = env('STABLE_TOKEN_ADDRESS').lower()
ROUTE_TOKEN_ADDRESSES = \
    env('ROUTE_TOKEN_ADDRESSES', default='').lower().split(',')
IGNORED_TOKEN_ADDRESSES = \
    env('IGNORED_TOKEN_ADDRESSES', default='').lower().split(',')
# Will be picked automatically by web3.py
WEB3_PROVIDER_URI = env('WEB3_PROVIDER_URI')

FACTORY_ADDRESS = env('FACTORY_ADDRESS')
VOTER_ADDRESS = env('VOTER_ADDRESS')
ROUTER_ADDRESS = env('ROUTER_ADDRESS')
VE_ADDRESS = env('VE_ADDRESS')
REWARDS_DIST_ADDRESS = env('REWARDS_DIST_ADDRESS')
WRAPPED_BRIBE_FACTORY_ADDRESS = env('WRAPPED_BRIBE_FACTORY_ADDRESS')

# Seconds to wait before running the chain syncup. `0` disables it!
SYNC_WAIT_SECONDS = env.int('SYNC_WAIT_SECONDS', default=0)

# Placeholder for our cache instance (Redis)
CACHE = None

try:
    CACHE = Database.from_url(env('REDIS_URL'))
    CACHE.ping()
except (ValueError, redis.exceptions.ConnectionError):
    LOGGER.debug('No Redis server found, using memory ...')
    # Patch walrus duh...
    # See: https://github.com/coleifer/walrus/issues/95
    db_class = Database
    db_class.__bases__ = (fakeredis.FakeRedis,)
    CACHE = db_class()
