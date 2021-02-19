import json
import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional, Union
from urllib.parse import urljoin

import requests
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.cache import cache
from requests.auth import HTTPBasicAuth

from ...checkout import base_calculations
from ...core.taxes import TaxError

if TYPE_CHECKING:
    # flake8: noqa
    from ...checkout.models import Checkout, CheckoutLine
    from ...order.models import Order
    from ...product.models import Product, ProductVariant, ProductType

logger = logging.getLogger(__name__)
