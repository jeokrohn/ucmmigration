from unittest import TestCase
from ucmexport import Proxy
import logging
from test import TAR_FILE

from typing import Optional


class ProxyTestCase(TestCase):
    proxy: Optional[Proxy] = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.proxy = Proxy(tar=TAR_FILE)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.proxy = None

    def setUp(self) -> None:
        logging.basicConfig(level=logging.DEBUG)
