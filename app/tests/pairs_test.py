# -*- coding: utf-8 -*-

from app.pairs import Pair
from app.tests.helpers import AppTestCase


class PairsTestCase(AppTestCase):
    def test_get(self):
        result = self.simulate_get("/api/v1/pairs")

        self.assertEqual(type(result.json["data"]), list)

    def test_get_with_pair_address(self):
        pair = next(Pair.all())
        result = self.simulate_get(
            "/api/v1/pairs?pair_address={}".format(pair.address)
        )

        self.assertEqual(type(result.json["data"]), list)
