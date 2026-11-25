"""Сборка и сериализация XML.

Разбор XML в проекте выполняется только через ``defusedxml`` (модуль ``formats``),
поэтому здесь из стандартной библиотеки берутся исключительно безопасные
примитивы сборки дерева: они не читают внешние данные и не разбирают разметку.
Сериализация берётся из ``defusedxml``. Это единственное место в проекте,
где вообще упоминается ``xml.etree``.
"""

from xml.etree.ElementTree import Element, SubElement
from defusedxml.ElementTree import tostring

__all__ = ["Element", "SubElement", "tostring"]