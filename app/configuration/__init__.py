# -*- coding: utf-8 -*-

import json

import falcon
from versiontools import Version

from app import __version__
from app.pairs import Pair, Token
from app.settings import (CACHE, DEFAULT_TOKEN_ADDRESS,
                          ROUTE_TOKEN_ADDRESSES, STABLE_TOKEN_ADDRESS,
                          )


class Configuration(object):
    """Returns a app configuration object"""

    def on_get(self, req, resp):
        default_token = Token.find(DEFAULT_TOKEN_ADDRESS)
        stable_token = Token.find(STABLE_TOKEN_ADDRESS)

        route_token_addresses = set(ROUTE_TOKEN_ADDRESSES) - {
            DEFAULT_TOKEN_ADDRESS,
            STABLE_TOKEN_ADDRESS,
        }

        route_tokens = [default_token, stable_token]
        for token_address in route_token_addresses:
            route_tokens.append(Token.find(token_address))

        route_token_data = [token._data for token in route_tokens]

        pairs = [p for p in Pair.all()]

        if pairs:
            tvl = sum(map(lambda p: (p.tvl or 0), pairs))
            max_apr = max(map(lambda p: (p.apr or 0), pairs))
        else:
            tvl = None
            max_apr = None
        resp.status = falcon.HTTP_200
        resp.text = json.dumps(
            dict(
                data=route_token_data,
                meta=dict(
                    tvl=tvl,
                    max_apr=max_apr,
                    default_token=default_token._data,
                    stable_token=stable_token._data,
                    cache=(CACHE.connection is not None),
                    version=str(Version(*__version__)),
                ),
            )
        )
