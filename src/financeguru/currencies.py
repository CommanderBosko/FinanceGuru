"""Currencies offered by the Currency Converter tab.

This is the single source of truth for the dropdown contents, mirroring how
``categories.py`` seeds the category pickers. The list is restricted to codes
the Frankfurter rates API (see ``rates.py``) actually publishes — anything not
here can't be converted, so it isn't offered. Display names follow the
"<Currency> (<Country>)" convention the feature was specced with (e.g. "Pound
(England)"), sorted alphabetically by that display text so the picker groups
same-named currencies (the six "Dollar (...)" entries, etc.) together.
"""

# (ISO 4217 code, display name) — alphabetical by display name.
CURRENCIES = [
    ("THB", "Baht (Thailand)"),
    ("AUD", "Dollar (Australia)"),
    ("CAD", "Dollar (Canada)"),
    ("HKD", "Dollar (Hong Kong)"),
    ("NZD", "Dollar (New Zealand)"),
    ("SGD", "Dollar (Singapore)"),
    ("USD", "Dollar (United States)"),
    ("EUR", "Euro (European Union)"),
    ("HUF", "Forint (Hungary)"),
    ("CHF", "Franc (Switzerland)"),
    ("CZK", "Koruna (Czech Republic)"),
    ("ISK", "Krona (Iceland)"),
    ("SEK", "Krona (Sweden)"),
    ("DKK", "Krone (Denmark)"),
    ("NOK", "Krone (Norway)"),
    ("RON", "Leu (Romania)"),
    ("BGN", "Lev (Bulgaria)"),
    ("TRY", "Lira (Turkey)"),
    ("MXN", "Peso (Mexico)"),
    ("PHP", "Peso (Philippines)"),
    ("GBP", "Pound (England)"),
    ("ZAR", "Rand (South Africa)"),
    ("BRL", "Real (Brazil)"),
    ("MYR", "Ringgit (Malaysia)"),
    ("INR", "Rupee (India)"),
    ("IDR", "Rupiah (Indonesia)"),
    ("ILS", "Shekel (Israel)"),
    ("KRW", "Won (South Korea)"),
    ("JPY", "Yen (Japan)"),
    ("CNY", "Yuan (China)"),
    ("PLN", "Zloty (Poland)"),
]

# The rate table is fetched once relative to a fixed pivot currency and cached
# as a whole (see repositories.currency_rates); converting between any two
# listed currencies is then a cross-rate division, not a second fetch.
PIVOT_BASE = "USD"

# Preselected on first launch, before any conversion has set a preference.
DEFAULT_FROM = "USD"
DEFAULT_TO = "EUR"

# ISO 4217 currencies with no minor unit, among the ones offered here. Shown
# as whole numbers rather than through money.cents()'s 2-decimal convention,
# which is shaped for a USD-like ledger and reads oddly for these (e.g.
# "15234.00 JPY" instead of the conventional "15234 JPY").
ZERO_DECIMAL_CURRENCIES = {"JPY", "KRW", "ISK"}
