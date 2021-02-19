import logging
from dataclasses import asdict
from decimal import Decimal
from django.core.exceptions import ValidationError
from prices import Money, TaxedMoney, TaxedMoneyRange
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional, Union
from urllib.parse import urljoin

from ..base_plugin import BasePlugin, ConfigurationTypeField
from ..error_codes import PluginErrorCode
from ...checkout import base_calculations
from ...core.taxes import TaxError, TaxType, charge_taxes_on_shipping, zero_taxed_money
from ...discount import DiscountInfo
from ...product.models import Product, ProductType

if TYPE_CHECKING:
    # flake8: noqa
    from ...checkout.models import Checkout, CheckoutLine
    from ...order.models import Order, OrderLine
    from ..models import PluginConfiguration

logger = logging.getLogger(__name__)


class PCTaxPlugin(BasePlugin):
    PLUGIN_NAME = "PC Tax"
    PLUGIN_ID = "mirumee.taxes.pc"

    DEFAULT_CONFIGURATION = [
        {"name": "ohio_tax", "value": "7.8"}
    ]
    CONFIG_STRUCTURE = {
        "ohio_tax": {
            "type": ConfigurationTypeField.STRING,
            "help_text": "Example: 7.8",
            "label": "Ohio Tax Amount",
        }
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = {item["name"]: item["value"] for item in self.configuration}

    def calculate_checkout_line_total(
            self,
            checkout_line: "CheckoutLine",
            discounts: Iterable[DiscountInfo],
            previous_value: TaxedMoney,
    ) -> TaxedMoney:

        checkout = checkout_line.checkout
        sa = checkout.shipping_address

        # Apply taxes to Ohio
        if sa and sa.country == 'US' and sa.country_area == 'OH':
            tax = float(self.config['ohio_tax']) or 7.8
            base_total = previous_value
            line_price = float(base_total.net.amount)
            tax_amount = line_price * (tax / 100)
            gross = Money(amount=line_price + tax_amount,
                          currency='USD')
            return TaxedMoney(net=base_total.net,
                              gross=gross)

        return previous_value
