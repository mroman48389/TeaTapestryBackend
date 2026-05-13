from fastapi.middleware.gzip import GZipMiddleware
from fastapi import FastAPI

# Optimization: Compress HTTP responses before sending them to the browser.
# This will increase load times because our JSON has a lot of repetitive fields.
# Reduces bandwidth usage, which will help with free hosting tiers, bandwidth
# limits, scaling, and rate-limiting synergy.
#
# These needs to go after CORS but before routes
#
# Small responses don't benefit from compression and waste CPU, so start 
# compressing if the payload is 500 B or larger.
def configure_gzip(app: FastAPI):
    app.add_middleware(GZipMiddleware, minimum_size = 500)