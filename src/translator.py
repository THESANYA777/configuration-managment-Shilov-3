import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


NUMBER_PATTERN = re.compile(r"00[0-7]+(?![0-9])")
NAME_PATTERN = re.compile(r"[_a-z]+")
NAME_FULL_PATTERN = re.compile(r"[_a-z]+\Z")


@dataclass(frozen=True)
class Token:
    """Лексема с позицией в исходном тексте."""

    kind: str
    text: str
    line: int
    column: int


class ConfigError(Exception):
    """Ошибка в исходной конфигурации."""

    def __init__(self, message: str, line: int, column: int) -> None:
        super().__init__(f"{line}:{column}: {message}")


def tokenize(source: str) -> list[Token]:
    """Разбить исходный текст на лексемы."""

    tokens: list[Token] = []
    index = 0
    line = 1
    column = 1

    while index < len(source):
        char = source[index]

        if char == "\n":
            index += 1
            line += 1
            column = 1
            continue

        if char.isspace():
            index += 1
            column += 1
            continue

        if char == "%":
            end = source.find("\n", index)
            index = len(source) if end == -1 else end
            continue

        start_line = line
        start_column = column

        if char in "#(),;=?[]":
            tokens.append(Token(char, char, line, column))
            index += 1
            column += 1
            continue

        if char.isdigit():
            match = NUMBER_PATTERN.match(source, index)
            if match is None:
                raise ConfigError(
                    "ожидалось восьмеричное число вида 00[0-7]+",
                    line,
                    column,
                )
            text = match.group()
            tokens.append(Token("NUMBER", text, line, column))
            index += len(text)
            column += len(text)
            continue

        if char == "_" or "a" <= char <= "z":
            match = NAME_PATTERN.match(source, index)
            assert match is not None
            text = match.group()
            tokens.append(Token("NAME", text, line, column))
            index += len(text)
            column += len(text)
            continue

        raise ConfigError(f"недопустимый символ {char!r}", line, column)

    tokens.append(Token("EOF", "", line, column))
    return tokens


class Parser:
    """Разбор объявлений констант и выражений."""

    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.position = 0
        self.constants: dict[str, Any] = {}

    def current(self) -> Token:
        """Вернуть текущую лексему."""

        return self.tokens[self.position]

    def expect(self, kind: str) -> Token:
        """Прочитать лексему требуемого типа."""

        token = self.current()
        if token.kind != kind:
            raise ConfigError(
                f"ожидалось {kind!r}, получено {token.kind!r}",
                token.line,
                token.column,
            )
        self.position += 1
        return token

    def parse(self) -> dict[str, Any]:
        """Прочитать все объявления."""

        while self.current().kind != "EOF":
            name = self.expect("NAME")
            self.expect("=")
            value = self.parse_value()
            self.expect(";")

            if name.text in self.constants:
                raise ConfigError(
                    f"константа {name.text!r} уже объявлена",
                    name.line,
                    name.column,
                )
            self.constants[name.text] = value

        return self.constants

    def parse_value(self) -> Any:
        """Прочитать число, массив или вычисление константы."""

        token = self.current()

        if token.kind == "NUMBER":
            self.position += 1
            return int(token.text, 8)

        if token.kind == "#":
            return self.parse_array()

        if token.kind == "?":
            self.expect("?")
            self.expect("[")
            name = self.expect("NAME")
            self.expect("]")

            if name.text not in self.constants:
                raise ConfigError(
                    f"неизвестная константа {name.text!r}",
                    name.line,
                    name.column,
                )
            return self.constants[name.text]

        raise ConfigError(
            "ожидалось число, массив или ?[имя]",
            token.line,
            token.column,
        )

    def parse_array(self) -> list[Any]:
        """Прочитать массив с возможными вложенными значениями."""

        self.expect("#")
        self.expect("(")
        values: list[Any] = []

        if self.current().kind != ")":
            values.append(self.parse_value())
            while self.current().kind == ",":
                self.expect(",")
                values.append(self.parse_value())

        self.expect(")")
        return values


def translate(source: str) -> dict[str, Any]:
    """Преобразовать конфигурацию в объект для сериализации."""

    return Parser(tokenize(source)).parse()


def main() -> int:
    """Прочитать аргументы командной строки и записать JSON."""

    argument_parser = argparse.ArgumentParser(
        description="Перевод конфигурационного файла в JSON."
    )
    argument_parser.add_argument("--input", required=True, type=Path)
    argument_parser.add_argument("--output", required=True, type=Path)
    args = argument_parser.parse_args()

    try:
        source = args.input.read_text(encoding="utf-8")
        result = translate(source)
        args.output.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except (OSError, ConfigError) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())