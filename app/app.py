# -*- coding: utf-8 -*-

from __future__ import absolute_import

import sys
from logging import StreamHandler
from app.circulating import CirculatingSupply

import falcon
from falcon_compression.middleware import CompressionMiddleware
from requestlogger import ApacheFormatter, WSGILogger

from app.assets import Assets
from app.configuration import Configuration
from app.pairs import Pairs
from app.settings import (CORS_ALLOWED_DOMAINS, LOGGER, PORT,
                          honeybadger_handler)
from app.supply import Supply
from app.venfts import Accounts

middleware = [
    CompressionMiddleware(),
]

if CORS_ALLOWED_DOMAINS:
    middleware.append(
        falcon.CORSMiddleware(allow_origins=CORS_ALLOWED_DOMAINS,),
    )

app_config = dict(middleware=middleware,
                  cors_enable=bool(CORS_ALLOWED_DOMAINS),)

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

# TODO: Remove when no longer needed for backward-compat...
app.add_route("/api/v1/baseAssets", Assets())
app.add_route("/api/v1/routeAssets", Configuration())
app.add_route("/api/v1/updatePairs", Pairs())

# Wrap the app in a WSGI logger to make it more verbose...
wsgi = WSGILogger(app, [StreamHandler(sys.stdout)], ApacheFormatter())


def main():
    LOGGER.info("Starting on port %s ...", PORT)

    import bjoern

    bjoern.run(wsgi, "", PORT, reuse_port=True)
