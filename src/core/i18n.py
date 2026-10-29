"""Localization engine for Quest for Aethelgard."""

from __future__ import annotations

from typing import Any

from src.locales.en import TRANSLATIONS_EN
from src.locales.es import TRANSLATIONS_ES


class LocalizationManager:
    def __init__(self) -> None:
        self.locale: str = "en"
        self._catalogs = {
            "en": TRANSLATIONS_EN,
            "es": TRANSLATIONS_ES,
        }

    def set_language(self, locale: str) -> None:
        if locale in self._catalogs:
            self.locale = locale

    def toggle_language(self) -> str:
        self.locale = "es" if self.locale == "en" else "en"
        return self.locale

    def t(self, key: str, **kwargs: Any) -> str:
        catalog = self._catalogs.get(self.locale, TRANSLATIONS_EN)
        pattern = catalog.get(key, TRANSLATIONS_EN.get(key, key))
        if kwargs:
            try:
                return pattern.format(**kwargs)
            except Exception:
                return pattern
        return pattern

    def random_choice(self, key: str, rng: Any) -> str:
        """Choose a localized line from a translation pool using a supplied RNG."""
        catalog = self._catalogs.get(self.locale, TRANSLATIONS_EN)
        options = catalog.get(key, TRANSLATIONS_EN.get(key, key))
        if isinstance(options, (list, tuple)):
            return rng.choice(options) if options else key
        return options


i18n = LocalizationManager()
t = i18n.t
t_choice = i18n.random_choice
