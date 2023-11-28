# -*- coding: utf-8 -*-

from datetime import timedelta

import falcon
from app.assets import Token
from app.settings import (CACHE, DEFAULT_TOKEN_ADDRESS, LOGGER,
                          VARA_CACHE_EXPIRATION)


class VaraPrice(object):
    """
    Handles the retrieval and caching of the Vara price.

    The class manages the caching and retrieval of the Vara price information.
    This endpoint provides a quick way to fetch the up-to-date
    Vara token price.
    """

    CACHE_KEY = "vara:json"
    CACHE_TIME = timedelta(minutes=5)

    @classmethod
    def sync(cls):
        cls.recache()

    @classmethod
    def recache(cls):
        """
        Updates and returns the Vara token price.

        This method fetches the fresh price of the Vara token from the database
        and caches it for quick retrieval in subsequent requests.
        """

        try:
            token = Token.find(DEFAULT_TOKEN_ADDRESS)

            if token:

                LOGGER.debug("Token: %s", token)
                LOGGER.debug("VARA price: %s", token.price)

                CACHE.set(cls.CACHE_KEY, str(token.price))
                CACHE.expire(cls.CACHE_KEY, VARA_CACHE_EXPIRATION)

                LOGGER.debug("Cache updated for %s.", cls.CACHE_KEY)
                return str(token.price)

        except AttributeError as e:
            LOGGER.error(
                "Error accessing token attributes: %s", e, exc_info=True
            )
            return None

        return "0"

    def on_get(self, req, resp):
        """
        Retrieves and returns the Vara token price.

        This method gets the Vara price from the cache. If the price isn't in
        the cache, it calls the recache() method to get fresh data.
        """
        vara_price = CACHE.get(self.CACHE_KEY) or VaraPrice.recache()

        if vara_price:
            resp.text = vara_price
            resp.status = falcon.HTTP_200
        else:
            LOGGER.warning("Vara price not found in cache!")
            resp.status = falcon.HTTP_204
