# -*- coding: utf-8 -*-

import json
from multiprocessing.pool import ThreadPool

import falcon
from app.assets import Token
from app.gauges import Gauge
from app.misc import JSONEncoder
from app.settings import CACHE, LOGGER, reset_multicall_pool_executor
from web3 import Web3

from .model import Pair


class Pairs(object):

    """Handles liquidity pools/pairs and related operations."""

    CACHE_KEY = "pairs:json"
    ADDRESSES_CACHE_KEY = "pairs:addresses"

    @classmethod
    def sync(cls):

        addresses = Pair.chain_addresses()

        previous_addresses_str = CACHE.get(cls.ADDRESSES_CACHE_KEY)
        previous_addresses = (
            json.loads(previous_addresses_str)
            if previous_addresses_str
            else []
        )

        if set(addresses) == set(previous_addresses):
            LOGGER.info("Addresses haven't changed...")

        CACHE.set(cls.ADDRESSES_CACHE_KEY, json.dumps(addresses))

        with ThreadPool(4) as pool:
            LOGGER.debug(
                "Syncing %s pairs using %s threads...",
                len(addresses),
                pool._processes,
            )
            pool.map(Pair.from_chain, addresses)
            pool.close()
            pool.join()

        Pairs.recache()

        reset_multicall_pool_executor()

    @classmethod
    def serialize(cls):

        """
        Serializes the list of Pair objects along with related Token
        and Gauge data into a list of dictionaries.
        """

        pairs = []

        for pair in Pair.all():

            if pair is None or pair._data is None:
                continue

            data = pair._data

            token0 = (
                Token.find(pair.token0_address.decode("utf-8"))
                if isinstance(pair.token0_address, bytes)
                else Token.find(pair.token0_address)
            )
            token1 = (
                Token.find(pair.token1_address.decode("utf-8"))
                if isinstance(pair.token1_address, bytes)
                else Token.find(pair.token1_address)
            )

            if token0:
                data["token0"] = token0.to_dict()
            if token1:
                data["token1"] = token1.to_dict()

            if pair.gauge_address:
                gauge = Gauge.find(pair.gauge_address)

                if gauge and gauge._data is not None:
                    data["gauge"] = gauge._data
                    data["gauge"]["bribes"] = []

                    for (token_addr, reward_ammount) in gauge.rewards:
                        data["gauge"]["bribes"].append(
                            dict(
                                token=Token.find(token_addr).to_dict(),
                                reward_ammount=float(reward_ammount),
                            )
                        )

            pairs.append(data)

        return pairs

    @classmethod
    def recache_price_and_gauge_data(cls):
        cls.recache()

    @classmethod
    def recache(cls):

        """
        Updates the cache with the serialized pairs data.
        """

        pairs = json.dumps(dict(data=cls.serialize()), cls=JSONEncoder)

        CACHE.set(cls.CACHE_KEY, pairs)
        LOGGER.debug("Cache updated for %s.", cls.CACHE_KEY)

        return pairs

    def resync(self, pair_address, gauge_address):

        """Resyncs a pair based on it's address or gauge address."""

        if Web3.isAddress(gauge_address):
            old_pair = Pair.get(
                Pair.gauge_address == str(gauge_address).lower()
            )
            Pair.from_chain(old_pair.address)
        elif Web3.isAddress(pair_address):
            Pair.from_chain(pair_address)
        else:
            return

        reset_multicall_pool_executor()
        Pairs.recache()

    def on_get(self, req, resp):

        """
        Fetches gauge data from the blockchain given an address,
        and updates or creates the corresponding Gauge object in the database.
        """

        self.resync(
            req.get_param("pair_address"), req.get_param("gauge_address")
        )

        pairs = CACHE.get(self.CACHE_KEY) or Pairs.recache()

        resp.status = falcon.HTTP_200
        resp.text = pairs
