# coding: utf-8
import importlib
from .. import MockApp


def load():
    """Load tariffs from migrations to mitigate real DB."""
    from market.tariff.models import Tariff
    from dbmail.models import MailTemplate
    mock_app = MockApp({
        ("tariff", "Tariff"): Tariff,
        ("dbmail", "MailTemplate"): MailTemplate
    })

    init_data = importlib.import_module('market.tariff.migrations.0002_initial_data')

    init_data.mail_forward(mock_app, None)
    init_data.tariff_forward(mock_app, None)
