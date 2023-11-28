# -*- coding: utf-8 -*-

from datetime import timedelta

import falcon
from app.assets import Token
from app.settings import (CACHE, DEFAULT_TOKEN_ADDRESS, LOGGER,
                          FRAC_CACHE_EXPIRATION)


class FracPrice(object):
    """
    Handles the retrieval and caching of the Frac price.

    The class manages the caching and retrieval of the Frac price information.
    This endpoint provides a quick way to fetch the up-to-date
    Frac token price.
    """

    CACHE_KEY = "frac:json"
    CACHE_TIME = timedelta(minutes=5)

    @classmethod
    def sync(cls):
        cls.recache()

    @classmethod
    def recache(cls):
        """
        Updates and returns the Frac token price.

        This method fetches the fresh price of the Frac token from the database
        and caches it for quick retrieval in subsequent requests.
        """

        try:
            token = Token.find(DEFAULT_TOKEN_ADDRESS)

            if token:

                LOGGER.debug("Token: %s", token)
                LOGGER.debug("Frac price: %s", token.price)

                CACHE.set(cls.CACHE_KEY, str(token.price))
                CACHE.expire(cls.CACHE_KEY, FRAC_CACHE_EXPIRATION)

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
        frac_price = CACHE.get(self.CACHE_KEY) or FracPrice.recache()

        if frac_price:
            resp.text = frac_price
            resp.status = falcon.HTTP_200
        else:
            LOGGER.warning("Vara price not found in cache!")
            resp.status = falcon.HTTP_204
