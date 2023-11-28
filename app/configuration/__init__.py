# -*- coding: utf-8 -*-

import json
import math

import falcon
import requests
from app import __version__
from app.misc import JSONEncoder
from app.pairs import Pair, Token
from app.settings import (CACHE, DEFAULT_TOKEN_ADDRESS, LOGGER,
                          ROUTE_TOKEN_ADDRESSES, STABLE_TOKEN_ADDRESS)
from versiontools import Version


class Configuration(object):
    """Returns a app configuration object"""

    @classmethod
    def sync(cls):
        cls.dexscreener_volume_data()

    @staticmethod
    def dexscreener_volume_data():
        try:

            DEXSCREENER_ENDPOINT = (
                "https://api.dexscreener.com/latest/dex/pairs/kava/"
            )
            CACHE_KEY = "volume:json"

            volume_m5 = 0
            volume_h1 = 0
            volume_h6 = 0
            volume_h24 = 0
            pairs_addresses = [p.address for p in Pair.all()]
            n = math.ceil(len(pairs_addresses) / (len(pairs_addresses) % 30))

            pairs_addresses = [
                pairs_addresses[i: i + n]
                for i in range(0, len(pairs_addresses), n)
            ]
            if pairs_addresses:
                for sub_pair_group in pairs_addresses:

                    res = requests.get(
                        DEXSCREENER_ENDPOINT + ",".join(sub_pair_group)
                    ).json()

                    pairs = res.get("pairs")

                    if pairs:
                        volume_m5 += sum(
                            map(lambda p: (p["volume"]["m5"] or 0), pairs)
                        )
                        volume_h1 += sum(
                            map(lambda p: (p["volume"]["h1"] or 0), pairs)
                        )
                        volume_h6 += sum(
                            map(lambda p: (p["volume"]["h6"] or 0), pairs)
                        )
                        volume_h24 += sum(
                            map(lambda p: (p["volume"]["h24"] or 0), pairs)
                        )

                data = dict(
                    volume_m5=volume_m5,
                    volume_h1=volume_h1,
                    volume_h6=volume_h6,
                    volume_h24=volume_h24,
                )
                CACHE.set(CACHE_KEY, json.dumps(data, cls=JSONEncoder))
                return data
            return dict(
                volume_m5=None, volume_h1=None, volume_h6=None, volume_h24=None
            )
        except Exception as e:
            LOGGER.error(e)
            return dict(
                volume_m5=None, volume_h1=None, volume_h6=None, volume_h24=None
            )

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

        if CACHE.get("volume:json"):
            volume = json.loads(CACHE.get("volume:json").decode("utf-8"))
        else:
            volume = self.dexscreener_volume_data()

        resp.status = falcon.HTTP_200

        resp.text = json.dumps(
            dict(
                data=route_token_data,
                meta=dict(
                    tvl=tvl,
                    max_apr=max_apr,
                    volume=volume,
                    default_token=default_token._data,
                    stable_token=stable_token._data,
                    cache=(CACHE.connection is not None),
                    version=str(Version(*__version__)),
                ),
            )
        )
