# -*- coding: utf-8 -*-

import falcon
from app.settings import (CACHE, DEFAULT_TOKEN_ADDRESS, LOGGER,
                          SUPPLY_CACHE_EXPIRATION, TREASURY_ADDRESS,
                          VE_ADDRESS)
from multicall import Call, Multicall


class CirculatingSupply:
    """Handles supply info"""

    CACHE_KEY = "circulating:string"

    @classmethod
    def sync(cls):
        cls.recache()

    @classmethod
    def recache(cls):

        supply_multicall = Multicall(
            [
                Call(
                    DEFAULT_TOKEN_ADDRESS,
                    "decimals()(uint256)",
                    [["token_decimals", None]],
                ),
                Call(
                    VE_ADDRESS,
                    "decimals()(uint256)",
                    [["lock_decimals", None]],
                ),
                Call(
                    DEFAULT_TOKEN_ADDRESS,
                    "totalSupply()(uint256)",
                    [["raw_total_supply", None]],
                ),
                Call(
                    DEFAULT_TOKEN_ADDRESS,
                    ["balanceOf(address)(uint256)", VE_ADDRESS],
                    [["raw_locked_supply", None]],
                ),
                Call(
                    DEFAULT_TOKEN_ADDRESS,
                    ["balanceOf(address)(uint256)", TREASURY_ADDRESS],
                    [["raw_treasury_supply", None]],
                ),
            ]
        )

        data = supply_multicall()

        token_multiplier = 10 ** data["token_decimals"]
        lock_multiplier = 10 ** data["lock_decimals"]

        data["total_supply"] = data["raw_total_supply"] / token_multiplier
        data["locked_supply"] = (
            data["raw_locked_supply"] / lock_multiplier
        ) + (data["raw_treasury_supply"] / token_multiplier)
        data["circulating_supply"] = (
            data["total_supply"] - data["locked_supply"]
        )

        serializable_tokens = data["circulating_supply"]
        CACHE.set(cls.CACHE_KEY, serializable_tokens)
        CACHE.expire("circulating:string", SUPPLY_CACHE_EXPIRATION)

        LOGGER.debug("Cache updated for %s.", cls.CACHE_KEY)
        return data["circulating_supply"]

    def on_get(self, req, resp):
        """Caches and returns our supply info"""
        supply_data = CACHE.get(self.CACHE_KEY)

        if supply_data:
            resp.text = supply_data
            resp.status = falcon.HTTP_200
        else:
            LOGGER.warning("Supply not found in cache!")
            resp.status = falcon.HTTP_204
