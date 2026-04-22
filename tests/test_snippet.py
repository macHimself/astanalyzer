from pathlib import Path

from astanalyzer.engine.scan_runtime import extract_code_snippet


def test_extract_code_snippet_trims_leading_docstring_tail(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.py"
    file_path.write_text(
        'class Empty:\n'
        '    """\n'
        '    Returns True for:\n'
        '    - non-empty strings\n'
        '    - other objects -> True unless length check fails\n'
        '    """\n'
        '    def __call__(self, actual, node):\n'
        '        if actual is None:\n'
        '            return False\n'
        '        try:\n'
        '            return len(actual) > 0\n'
        '        except Exception:\n'
        '            return True\n'
        '\n'
        'class REGEX:\n'
        '    pass\n',
        encoding="utf-8",
    )

    snippet, snippet_start, snippet_end, snippet_truncated = extract_code_snippet(
        file_path=file_path,
        start_line=10,
        end_line=12,
        context=4,
    )

    assert snippet is not None
    assert snippet_start is not None
    assert snippet_end is not None
    assert snippet_truncated is True

    assert "def __call__(self, actual, node):" in snippet
    assert "if actual is None:" in snippet
    assert "return False" in snippet
    assert "except Exception:" in snippet

    lines = snippet.splitlines()
    nonempty_lines = [line.strip() for line in lines if line.strip()]

    assert nonempty_lines
    assert nonempty_lines[0] != '"""'
    assert nonempty_lines[0] != "'''"

    assert snippet_start <= 7
    assert snippet_end >= 12


def test_extract_code_snippet_trims_leading_docstring_tail_when_snippet_starts_inside_docstring(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "sample.py"
    file_path.write_text(
        'class Empty:\n'
        '    """\n'
        '    Returns True for:\n'
        '    - non-empty strings\n'
        '    - other objects -> True unless length check fails\n'
        '    """\n'
        '    def __call__(self, actual, node):\n'
        '        if actual is None:\n'
        '            return False\n'
        '        try:\n'
        '            return len(actual) > 0\n'
        '        except Exception:\n'
        '            return True\n'
        '\n'
        'class REGEX:\n'
        '    pass\n',
        encoding="utf-8",
    )

    snippet, snippet_start, snippet_end, snippet_truncated = extract_code_snippet(
        file_path=file_path,
        start_line=10,
        end_line=12,
        context=4,
    )

    assert snippet is not None
    assert snippet_start is not None
    assert snippet_end is not None
    assert snippet_truncated is True

    assert "def __call__(self, actual, node):" in snippet
    assert "if actual is None:" in snippet
    assert "return False" in snippet
    assert "except Exception:" in snippet

    nonempty_lines = [line.strip() for line in snippet.splitlines() if line.strip()]
    assert nonempty_lines
    assert nonempty_lines[0] not in {'"""', "'''"}


def test_extract_code_snippet_returns_basic_context_window(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.py"
    file_path.write_text(
        "\n".join(
            [
                "line1",
                "line2",
                "line3",
                "line4",
                "line5",
                "line6",
                "line7",
                "line8",
                "line9",
                "line10",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    snippet, snippet_start, snippet_end, snippet_truncated = extract_code_snippet(
        file_path=file_path,
        start_line=5,
        end_line=6,
        context=2,
    )

    assert snippet is not None
    assert snippet_start == 3
    assert snippet_end == 8
    assert snippet_truncated is True
    assert snippet == "line3\nline4\nline5\nline6\nline7\nline8\n"


def test_extract_code_snippet_returns_none_when_start_line_is_none(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.py"
    file_path.write_text("print('hello')\n", encoding="utf-8")

    snippet, snippet_start, snippet_end, snippet_truncated = extract_code_snippet(
        file_path=file_path,
        start_line=None,
        end_line=1,
        context=2,
    )

    assert snippet is None
    assert snippet_start is None
    assert snippet_end is None
    assert snippet_truncated is False


def test_extract_code_snippet_marks_truncated_when_snippet_does_not_start_at_file_top(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "sample.py"
    file_path.write_text(
        "".join(f"line{i}\n" for i in range(1, 31)),
        encoding="utf-8",
    )

    snippet, snippet_start, snippet_end, snippet_truncated = extract_code_snippet(
        file_path=file_path,
        start_line=20,
        end_line=20,
        context=2,
    )

    assert snippet is not None
    assert not snippet.startswith("# ... truncated ...\n")
    assert snippet_truncated is True
    assert snippet_start is not None
    assert snippet_start > 1
    assert snippet_end == 22


def test_extract_code_snippet_does_not_mark_truncated_when_starting_at_file_top(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "sample.py"
    file_path.write_text(
        "line1\nline2\nline3\nline4\n",
        encoding="utf-8",
    )

    snippet, snippet_start, snippet_end, snippet_truncated = extract_code_snippet(
        file_path=file_path,
        start_line=1,
        end_line=2,
        context=3,
    )

    assert snippet is not None
    assert snippet_truncated is False
    assert snippet_start == 1
    assert snippet_end == 4


def test_extract_code_snippet_backtracks_for_odd_triple_double_quote_state(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.py"
    file_path.write_text(
        "line1\n"
        "line2\n"
        '"""\n'
        "doc a\n"
        "doc b\n"
        '"""\n'
        "def target():\n"
        "    x = 1\n"
        "    y = 2\n"
        "    return x + y\n",
        encoding="utf-8",
    )

    snippet, snippet_start, snippet_end, snippet_truncated = extract_code_snippet(
        file_path=file_path,
        start_line=8,
        end_line=9,
        context=3,
    )

    assert snippet is not None
    assert snippet_start is not None
    assert snippet_end is not None
    assert snippet_truncated is True
    assert "def target():" in snippet
    assert "return x + y" in snippet
    assert snippet_start <= 6


def test_extract_code_snippet_backtracks_for_odd_triple_single_quote_state(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.py"
    file_path.write_text(
        "line1\n"
        "line2\n"
        "'''\n"
        "doc a\n"
        "doc b\n"
        "'''\n"
        "def target():\n"
        "    x = 1\n"
        "    y = 2\n"
        "    return x + y\n",
        encoding="utf-8",
    )

    snippet, snippet_start, snippet_end, snippet_truncated = extract_code_snippet(
        file_path=file_path,
        start_line=8,
        end_line=9,
        context=3,
    )

    assert snippet is not None
    assert snippet_start is not None
    assert snippet_end is not None
    assert snippet_truncated is True
    assert "def target():" in snippet
    assert "return x + y" in snippet
    assert snippet_start <= 6


def test_extract_code_snippet_keeps_match_lines_inside_returned_range(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.py"
    file_path.write_text(
        "".join(f"line{i}\n" for i in range(1, 21)),
        encoding="utf-8",
    )

    snippet, snippet_start, snippet_end, snippet_truncated = extract_code_snippet(
        file_path=file_path,
        start_line=9,
        end_line=12,
        context=2,
    )

    assert snippet is not None
    assert snippet_start == 7
    assert snippet_end == 14
    assert snippet_truncated is True

    returned_lines = {
        snippet_start + idx
        for idx, _line in enumerate(snippet.splitlines())
    }

    assert 9 in returned_lines
    assert 10 in returned_lines
    assert 11 in returned_lines
    assert 12 in returned_lines


def test_extract_code_snippet_handles_missing_file_gracefully(tmp_path: Path) -> None:
    file_path = tmp_path / "missing.py"

    snippet, snippet_start, snippet_end, snippet_truncated = extract_code_snippet(
        file_path=file_path,
        start_line=3,
        end_line=4,
        context=2,
    )

    assert snippet is None
    assert snippet_start is None
    assert snippet_end is None
    assert snippet_truncated is False


def test_extract_code_snippet_does_not_trim_valid_comment_or_code_start(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.py"
    file_path.write_text(
        "line1\n"
        "line2\n"
        "# useful comment\n"
        "def target():\n"
        "    if True:\n"
        "        return 1\n"
        "\n"
        "target()\n",
        encoding="utf-8",
    )

    snippet, snippet_start, snippet_end, snippet_truncated = extract_code_snippet(
        file_path=file_path,
        start_line=5,
        end_line=6,
        context=2,
    )

    assert snippet is not None
    assert "# useful comment" in snippet
    assert "def target():" in snippet
    assert "return 1" in snippet
    assert snippet_truncated is True


def test_extract_code_snippet_trims_docstring_tail_but_preserves_following_class(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.py"
    file_path.write_text(
        'class A:\n'
        '    """\n'
        '    Long description line 1\n'
        '    Long description line 2\n'
        '    End of description\n'
        '    """\n'
        '    def method(self):\n'
        '        pass\n'
        '\n'
        'class B:\n'
        '    """Real class docstring."""\n'
        '    pass\n',
        encoding="utf-8",
    )

    snippet, snippet_start, snippet_end, snippet_truncated = extract_code_snippet(
        file_path=file_path,
        start_line=7,
        end_line=8,
        context=3,
    )

    assert snippet is not None
    assert "def method(self):" in snippet
    assert "pass" in snippet
    assert snippet_truncated is True

    nonempty_lines = [line.strip() for line in snippet.splitlines() if line.strip()]
    assert nonempty_lines[0] not in {'"""', "'''"}


def test_extract_code_snippet_keeps_decorator_with_function(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.py"
    file_path.write_text(
        "line1\n"
        "@cached_property\n"
        "def value(self):\n"
        "    return 42\n"
        "\n"
        "x = 1\n",
        encoding="utf-8",
    )

    snippet, snippet_start, snippet_end, snippet_truncated = extract_code_snippet(
        file_path=file_path,
        start_line=3,
        end_line=4,
        context=1,
    )

    assert snippet is not None
    assert "@cached_property" in snippet
    assert "def value(self):" in snippet
    assert "return 42" in snippet
    assert snippet_start <= 2
    assert snippet_end >= 4
    assert snippet_truncated is True


def test_extract_code_snippet_does_not_trim_when_triple_quotes_are_inside_normal_string(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "sample.py"
    file_path.write_text(
        "def demo():\n"
        "    text = 'marker: \"\"\" inside ordinary string'\n"
        "    return text\n"
        "\n"
        "demo()\n",
        encoding="utf-8",
    )

    snippet, snippet_start, snippet_end, snippet_truncated = extract_code_snippet(
        file_path=file_path,
        start_line=2,
        end_line=3,
        context=1,
    )

    assert snippet is not None
    assert "marker: \"\"\" inside ordinary string" in snippet
    assert "return text" in snippet
    assert "def demo():" in snippet
    assert snippet_truncated is False


def test_extract_code_snippet_does_not_trim_when_triple_single_quotes_are_inside_normal_string(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "sample.py"
    file_path.write_text(
        'def demo():\n'
        '    text = "marker: \'\'\' inside ordinary string"\n'
        "    return text\n",
        encoding="utf-8",
    )

    snippet, snippet_start, snippet_end, snippet_truncated = extract_code_snippet(
        file_path=file_path,
        start_line=2,
        end_line=3,
        context=1,
    )

    assert snippet is not None
    assert "marker: ''' inside ordinary string" in snippet
    assert "return text" in snippet
    assert "def demo():" in snippet
    assert snippet_truncated is False


def test_extract_code_snippet_handles_long_docstring_above_match_without_starting_on_bare_triple_quote(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "sample.py"
    long_doc = "".join(f"    doc line {i}\n" for i in range(1, 31))
    file_path.write_text(
        "class Example:\n"
        '    """\n'
        f"{long_doc}"
        '    """\n'
        "    def target(self):\n"
        "        value = 1\n"
        "        return value\n",
        encoding="utf-8",
    )

    snippet, snippet_start, snippet_end, snippet_truncated = extract_code_snippet(
        file_path=file_path,
        start_line=34,
        end_line=35,
        context=3,
    )

    assert snippet is not None
    assert "def target(self):" in snippet
    assert "value = 1" in snippet
    assert "return value" in snippet
    assert snippet_truncated is True

    nonempty_lines = [line.strip() for line in snippet.splitlines() if line.strip()]
    assert nonempty_lines
    assert nonempty_lines[0] not in {'"""', "'''"}


def test_extract_code_snippet_preserves_class_header_when_match_is_near_class_start(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "sample.py"
    file_path.write_text(
        "class Service:\n"
        "    def run(self):\n"
        "        if True:\n"
        "            return 1\n",
        encoding="utf-8",
    )

    snippet, snippet_start, snippet_end, snippet_truncated = extract_code_snippet(
        file_path=file_path,
        start_line=2,
        end_line=4,
        context=1,
    )

    assert snippet is not None
    assert "class Service:" in snippet
    assert "def run(self):" in snippet
    assert "return 1" in snippet
    assert snippet_truncated is False


def test_extract_code_snippet_preserves_nearby_import_context_when_match_is_near_top_level_definition(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "sample.py"
    file_path.write_text(
        "from pathlib import Path\n"
        "import os\n"
        "\n"
        "def build():\n"
        "    return Path(os.getcwd())\n",
        encoding="utf-8",
    )

    snippet, snippet_start, snippet_end, snippet_truncated = extract_code_snippet(
        file_path=file_path,
        start_line=4,
        end_line=5,
        context=2,
    )

    assert snippet is not None
    assert snippet_truncated is True
    assert "import os" in snippet
    assert "def build():" in snippet
    assert "return Path(os.getcwd())" in snippet
    assert "from pathlib import Path" not in snippet
    assert snippet_start == 2
    assert snippet_end == 5


def test_extract_code_snippet_preserves_full_import_context_when_context_is_large_enough(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "sample.py"
    file_path.write_text(
        "from pathlib import Path\n"
        "import os\n"
        "\n"
        "def build():\n"
        "    return Path(os.getcwd())\n",
        encoding="utf-8",
    )

    snippet, snippet_start, snippet_end, snippet_truncated = extract_code_snippet(
        file_path=file_path,
        start_line=4,
        end_line=5,
        context=3,
    )

    assert snippet is not None
    assert snippet_truncated is False
    assert "from pathlib import Path" in snippet
    assert "import os" in snippet
    assert "def build():" in snippet
    assert "return Path(os.getcwd())" in snippet
    assert snippet_start == 1
    assert snippet_end == 5


def test_extract_code_snippet_keeps_target_lines_visible_after_docstring_trim(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.py"
    file_path.write_text(
        "class A:\n"
        '    """\n'
        "    first line\n"
        "    second line\n"
        "    third line\n"
        '    """\n'
        "    def method(self):\n"
        "        if True:\n"
        "            return 1\n"
        "        return 2\n",
        encoding="utf-8",
    )

    snippet, snippet_start, snippet_end, snippet_truncated = extract_code_snippet(
        file_path=file_path,
        start_line=8,
        end_line=9,
        context=3,
    )

    assert snippet is not None
    assert "def method(self):" in snippet
    assert "if True:" in snippet
    assert "return 1" in snippet
    assert snippet_start is not None
    assert snippet_start <= 7
    assert snippet_truncated is True


def test_extract_code_snippet_does_not_start_with_docstring_tail_text(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.py"
    file_path.write_text(
        "class Empty:\n"
        '    """\n'
        "    Returns True for:\n"
        "    - non-empty strings\n"
        "    - other objects -> True unless length check fails\n"
        '    """\n'
        "    def __call__(self, actual, node):\n"
        "        if actual is None:\n"
        "            return False\n"
        "        return True\n",
        encoding="utf-8",
    )

    snippet, snippet_start, snippet_end, snippet_truncated = extract_code_snippet(
        file_path=file_path,
        start_line=8,
        end_line=9,
        context=4,
    )

    assert snippet is not None
    lines = [line.strip() for line in snippet.splitlines() if line.strip()]
    assert lines
    assert lines[0] not in {
        "Returns True for:",
        "- non-empty strings",
        "- other objects -> True unless length check fails",
        '"""',
        "'''",
    }
    assert "def __call__(self, actual, node):" in snippet
    assert snippet_truncated is True


def test_extract_code_snippet_includes_match_even_when_context_is_zero(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.py"
    file_path.write_text(
        "a = 1\n"
        "b = 2\n"
        "c = a + b\n"
        "print(c)\n",
        encoding="utf-8",
    )

    snippet, snippet_start, snippet_end, snippet_truncated = extract_code_snippet(
        file_path=file_path,
        start_line=3,
        end_line=3,
        context=0,
    )

    assert snippet is not None
    assert "c = a + b" in snippet
    assert snippet_start == 3
    assert snippet_end == 3
    assert snippet_truncated is True


def test_extract_code_snippet_handles_match_at_end_of_file(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.py"
    file_path.write_text(
        "line1\n"
        "line2\n"
        "line3\n"
        "line4\n"
        "line5\n",
        encoding="utf-8",
    )

    snippet, snippet_start, snippet_end, snippet_truncated = extract_code_snippet(
        file_path=file_path,
        start_line=5,
        end_line=5,
        context=3,
    )

    assert snippet is not None
    assert "line5" in snippet
    assert snippet_end == 5
    assert snippet_truncated is True