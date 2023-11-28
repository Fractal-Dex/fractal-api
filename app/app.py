# -*- coding: utf-8 -*-

from __future__ import absolute_import

import sys
from logging import StreamHandler

import bjoern
import falcon
from app.assets import Assets
from app.circulating import CirculatingSupply
from app.configuration import Configuration
from app.pairs import Pairs
from app.settings import (CORS_ALLOWED_DOMAINS, LOGGER, PORT,
                          honeybadger_handler)
from app.supply import Supply
from app.frac import FracPrice
from app.venfts import Accounts
from falcon_compression.middleware import CompressionMiddleware
from requestlogger import ApacheFormatter, WSGILogger

middleware = [
    CompressionMiddleware(),
]

if CORS_ALLOWED_DOMAINS:
    middleware.append(
        falcon.CORSMiddleware(
            allow_origins=CORS_ALLOWED_DOMAINS,
        ),
    )

app_config = dict(
    middleware=middleware, cors_enable=bool(CORS_ALLOWED_DOMAINS)
)
app = falcon.App(**app_config)
app.add_error_handler(Exception, honeybadger_handler)
app.req_options.auto_parse_form_urlencoded = True
app.req_options.strip_url_path_trailing_slash = True
app.add_route("/api/v1/accounts", Accounts())
app.add_route("/api/v1/assets", Assets())
app.add_route("/api/v1/configuration", Configuration())
app.add_route("/api/v1/pairs", Pairs())
app.add_route("/api/v1/supply", Supply())
app.add_route("/api/v1/circulating-supply", CirculatingSupply())
app.add_route("/api/v1/frac-price", FracPrice())
wsgi = WSGILogger(app, [StreamHandler(sys.stdout)], ApacheFormatter())


def main():

    LOGGER.info("Starting on port %s ...", PORT)
    bjoern.run(wsgi, "", PORT, reuse_port=True)


if __name__ == "__main__":
    main()
