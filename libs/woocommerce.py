"""
WooCommerce API Wrapper

A simple wrapper for WooCommerce REST API v3.
"""

import requests
from woocommerce import API
from typing import Any
import urllib3
import logging

# Configure logger for this module
logger = logging.getLogger(__name__)

# Disable SSL warnings for verify=False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class WooCommerce:
    """Simple WooCommerce API client using the official woocommerce library."""

    def __init__(self, url: str, consumer_key: str, consumer_secret: str, version: str = "wc/v3"):
        """
        Initialize WooCommerce API client.
        """
        self.wcapi = API(
            url=url,
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            version=version,
            query_string_auth=True
        )
        self.version = version
        # The official library doesn't have a simple 'verify=False' global setting, 
        # but we can monkeypatch the session or handle it via the underlying requests.
        # For most local setups, query_string_auth=True is the key.
        self.headers = {}

    def _full_api_url(self, endpoint: str) -> str:
        """Construct the full WooCommerce API URL for logging."""
        return f"{self.wcapi.url}/wp-json/{self.version}/{endpoint}"

    def get(self, endpoint: str, params: dict | None = None) -> Any:
        """Make a GET request to the WooCommerce API."""
        url = self._full_api_url(endpoint)
        logger.info(f"WooCommerce GET: {url} | Params: {params}")
        try:
            # The official library's API.get returns a response object
            response = self.wcapi.get(endpoint, params=params)
            # logger.info(f"Actual Request URL: {response.url}")
            
            # The official library's response object has a .data attribute for the JSON body
            # and .status_code for the HTTP status.
            if response.status_code >= 400:
                raise Exception(f"HTTP Error: {response.status_code} - {response.content}")
            
            return response.json()
        except Exception as e:
            raise Exception(f"WooCommerce GET error: {e}")

    def post(self, endpoint: str, params: dict | None = None) -> Any:
        """Make a POST request to the WooCommerce API."""
        url = self._full_api_url(endpoint)
        logger.info(f"WooCommerce POST: {url} | Data: {params}")
        try:
            response = self.wcapi.post(endpoint, data=params)
            if response.status_code >= 400:
                raise Exception(f"HTTP Error: {response.status_code} - {response.content}")
            return response.json()
        except Exception as e:
            raise Exception(f"WooCommerce POST error: {e}")

    def put(self, endpoint: str, params: dict | None = None) -> Any:
        """Make a PUT request to the WooCommerce API."""
        url = self._full_api_url(endpoint)
        logger.info(f"WooCommerce PUT: {url} | Data: {params}")
        try:
            response = self.wcapi.put(endpoint, data=params)
            if response.status_code >= 400:
                raise Exception(f"HTTP Error: {response.status_code} - {response.content}")
            return response.json()
        except Exception as e:
            raise Exception(f"WooCommerce PUT error: {e}")

    def delete(self, endpoint: str, params: dict | None = None) -> Any:
        """Make a DELETE request to the WooCommerce API."""
        url = self._full_api_url(endpoint)
        logger.info(f"WooCommerce DELETE: {url} | Params: {params}")
        try:
            response = self.wcapi.delete(endpoint, params=params)
            if response.status_code >= 400:
                raise Exception(f"HTTP Error: {response.status_code} - {response.content}")
            return response.json()
        except Exception as e:
            raise Exception(f"WooCommerce DELETE error: {e}")
