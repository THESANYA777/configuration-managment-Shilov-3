import unittest

from src.translator import ConfigError, translate


class TranslatorTests(unittest.TestCase):
    """Проверка всех конструкций языка и их вложенности."""

    def test_numbers_and_octal_conversion(self) -> None:
        self.assertEqual(translate("count = 0010;"), {"count": 8})

    def test_empty_and_nested_arrays(self) -> None:
        source = "empty = #(); nested = #(0001, #(0002, 0003));"
        self.assertEqual(
            translate(source),
            {"empty": [], "nested": [1, [2, 3]]},
        )

    def test_reference_and_nested_reference(self) -> None:
        source = "base = #(0001, 0002); copy = ?[base]; all = #(?[copy]);"
        self.assertEqual(
            translate(source),
            {"base": [1, 2], "copy": [1, 2], "all": [[1, 2]]},
        )

    def test_names_comments_and_whitespace(self) -> None:
        source = "% заголовок\n_alpha = 0007; % пояснение\n"
        self.assertEqual(translate(source), {"_alpha": 7})

    def test_unknown_reference(self) -> None:
        with self.assertRaisesRegex(ConfigError, "неизвестная"):
            translate("value = ?[missing];")

    def test_duplicate_name(self) -> None:
        with self.assertRaisesRegex(ConfigError, "уже объявлена"):
            translate("value = 0001; value = 0002;")

    def test_invalid_number(self) -> None:
        with self.assertRaisesRegex(ConfigError, "восьмеричное"):
            translate("value = 0089;")

    def test_missing_semicolon(self) -> None:
        with self.assertRaisesRegex(ConfigError, "ожидалось ';'"):
            translate("value = 0001")

    def test_invalid_name(self) -> None:
        with self.assertRaises(ConfigError):
            translate("Invalid = 0001;")

    def test_trailing_comma(self) -> None:
        with self.assertRaises(ConfigError):
            translate("value = #(0001,);")


if __name__ == "__main__":
    unittest.main()