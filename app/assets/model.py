# -*- coding: utf-8 -*-

import requests
import requests.exceptions
from multicall import Call, Multicall
from walrus import BooleanField, FloatField, IntegerField, Model, TextField
from web3.auto import w3
from web3.exceptions import ContractLogicError

from app.settings import (BLUECHIP_TOKEN_ADDRESSES, CACHE,
                          IGNORED_TOKEN_ADDRESSES, LOGGER, ROUTER_ADDRESS,
                          STABLE_TOKEN_ADDRESS, TOKENLISTS)


class Token(Model):
    """ERC20 token model."""

    __database__ = CACHE

    address = TextField(primary_key=True)
    name = TextField()
    symbol = TextField()
    decimals = IntegerField()
    logoURI = TextField()
    price = FloatField(default=0)
    stable = BooleanField(default=0)
    # To indicate if it's a liquid version of another token as swKAVA
    liquid_staked_address = TextField()

    # See: https://docs.1inch.io/docs/aggregation-protocol/api/swagger
    AGGREGATOR_ENDPOINT = "https://api.1inch.io/v4.0/10/quote"
    # See: https://docs.dexscreener.com/#tokens
    DEXSCREENER_ENDPOINT = "https://api.dexscreener.com/latest/dex/tokens/"
    # See: https://defillama.com/docs/api#operations-tag-coins
    DEFILLAMA_ENDPOINT = "https://coins.llama.fi/prices/current/"

    def defillama_price_in_stables(self):
        """Returns the price quoted from our llama defis."""
        # Peg it forever.
        if self.address == STABLE_TOKEN_ADDRESS:
            return 1.0

        chain_token = "kava:" + self.address.lower()
        res = requests.get(self.DEFILLAMA_ENDPOINT + chain_token).json()
        coins = res.get("coins", {})

        for (_, coin) in coins.items():
            return coin.get("price", 0)

        return 0

    def one_inch_price_in_stables(self):
        """Returns the price quoted from an aggregator in stables/USDC."""
        # Peg it forever.
        if self.address == STABLE_TOKEN_ADDRESS:
            return 1.0

        stablecoin = Token.find(STABLE_TOKEN_ADDRESS)

        res = requests.get(
            self.AGGREGATOR_ENDPOINT,
            params=dict(
                fromTokenAddress=self.address,
                toTokenAddress=stablecoin.address,
                amount=(1 * 10 ** self.decimals),
            ),
        ).json()

        amount = res.get("toTokenAmount", 0)

        return int(amount) / 10 ** stablecoin.decimals

    def dexscreener_price_in_stables(self):
        """Returns the price quoted from an aggregator in stables/USDC."""
        # Peg it forever.
        if self.address == STABLE_TOKEN_ADDRESS:
            return 1.0

        res = requests.get(self.DEXSCREENER_ENDPOINT + self.address).json()
        pairs = res.get("pairs") or []

        if len(pairs) == 0:
            return 0

        pairs_in_kava = [pair for pair in pairs if pair["chainId"] == "kava"]

        if len(pairs_in_kava) == 0:
            price = str(pairs[0].get("priceUsd") or 0).replace(",", "")
        else:
            price = str(pairs_in_kava[0].get("priceUsd") or 0).replace(",", "")

        # To avoid this kek...
        #   ValueError: could not convert string to float: '140344,272.43'

        return float(price)

    def aggregated_price_in_stables(self):
        price = self.dexscreener_price_in_stables()

        if price != 0 and self.address not in BLUECHIP_TOKEN_ADDRESSES:
            return price

        try:
            return self.defillama_price_in_stables()
        except (
                requests.exceptions.HTTPError,
                requests.exceptions.JSONDecodeError):
            return price

    def chain_price_in_stables(self):
        """Returns the price quoted from our router in stables/USDC."""
        # Peg it forever.
        if self.address == STABLE_TOKEN_ADDRESS:
            return 1.0

        stablecoin = Token.find(STABLE_TOKEN_ADDRESS)
        try:
            amount, is_stable = Call(
                ROUTER_ADDRESS,
                [
                    "getAmountOut(uint256,address,address)(uint256,bool)",
                    1 * 10 ** self.decimals,
                    self.address,
                    stablecoin.address,
                ],
            )()
        except ContractLogicError:
            return 0

        return amount / 10 ** stablecoin.decimals

    @classmethod
    def find(cls, address):
        """Loads a token from the database, of from chain if not found."""
        if address is None:
            return None

        try:
            return cls.load(address.lower())
        except KeyError:
            return cls.from_chain(address.lower())

    def _update_price(self):
        """Updates the token price in USD from different sources."""
        self.price = self.aggregated_price_in_stables()

        if self.price == 0:
            self.price = self.chain_price_in_stables()

        self.save()

    @classmethod
    def from_chain(cls, address, logoURI=None):
        address = address.lower()

        """Fetches and returns a token from chain."""
        token_multi = Multicall(
            [
                Call(address, ["name()(string)"], [["name", None]]),
                Call(address, ["symbol()(string)"], [["symbol", None]]),
                Call(address, ["decimals()(uint8)"], [["decimals", None]]),
            ]
        )

        data = token_multi()

        # TODO: Add a dummy logo...
        token = cls.create(address=address, **data)
        token._update_price()

        LOGGER.debug("Fetched %s:%s.", cls.__name__, address)

        return token

    @classmethod
    def from_tokenlists(cls):
        """Fetches and merges all the tokens from available tokenlists."""
        our_chain_id = w3.eth.chain_id

        for tlist in TOKENLISTS:
            try:
                res = requests.get(tlist).json()

                for token_data in res["tokens"]:
                    # Skip tokens from other chains...
                    if token_data.get("chainId", None) != our_chain_id:
                        LOGGER.debug("Token not in chain: %s",
                                     token_data["symbol"])
                        continue

                    token_data["address"] = token_data["address"].lower()

                    if token_data["address"] in IGNORED_TOKEN_ADDRESSES:
                        continue
                    if token_data["liquid_staked_address"]:
                        token_data["liquid_staked_address"] = token_data[
                            "liquid_staked_address"
                        ].lower()
                    token = cls.create(**token_data)
                    token.stable = 1 if "stablecoin" \
                        in token_data["tags"][0] else 0
                    token._update_price()

                    LOGGER.debug("Loaded %s:%s.", cls.__name__,
                                 token_data["address"])
            except Exception as error:
                LOGGER.error(error)
                continue
