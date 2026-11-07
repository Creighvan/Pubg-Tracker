"""Guards against a broken translations.py (deleted keys, renamed placeholders)."""
import ast
import glob
import os
import re
import string

import translations

TABLE = translations.TRANSLATIONS
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _code_files():
    for path in glob.glob(os.path.join(ROOT, "**", "*.py"), recursive=True):
        rel = os.path.relpath(path, ROOT)
        if rel.startswith(("tests", "test_", "venv", ".git")) or rel == "translations.py":
            continue
        yield rel, open(path, encoding="utf-8", errors="ignore").read()


def _fields(text):
    return {name.split(".")[0].split("[")[0] for _, name, _, _ in string.Formatter().parse(text) if name}


def test_every_language_has_every_english_key():
    english = set(TABLE["en"])
    for lang, strings in TABLE.items():
        missing = sorted(english - set(strings))
        assert not missing, f"{lang} is missing {len(missing)} keys, e.g. {missing[:5]}"


def test_english_still_has_its_full_set_of_texts():
    assert len(TABLE["en"]) >= 250, f"English has only {len(TABLE['en'])} texts - translations.py was truncated"


def test_every_key_the_code_asks_for_exists():
    english = set(TABLE["en"])
    used = {}
    for rel, src in _code_files():
        for key in re.findall(r"get_translation\([^,()]+,\s*[\"']([a-z0-9_]+)[\"']", src):
            used.setdefault(key, rel)
    missing = {k: f for k, f in used.items() if k not in english}
    assert not missing, f"keys used in code but missing from translations.py: {dict(list(missing.items())[:8])}"


def test_placeholders_agree_across_languages():
    for key, text in TABLE["en"].items():
        for lang, strings in TABLE.items():
            if key in strings:
                assert _fields(strings[key]) == _fields(text), f"{lang}.{key}: placeholders differ from English"


def _wired_command_functions():
    """Names bot.py imports from commands/*.py (old, unused copies elsewhere are not checked)."""
    tree = ast.parse(open(os.path.join(ROOT, "bot.py"), encoding="utf-8", errors="ignore").read())
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("commands"):
            names.update(alias.name for alias in node.names)
    return names


def _live_nodes(rel, tree, wired):
    """The parts of a file that really run: all of bot.py and modules/, and only the wired command functions."""
    if not rel.startswith("commands"):
        return [tree]
    return [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in wired]


def test_code_supplies_every_placeholder_the_text_needs():
    """For every get_translation(lang, "key").format(a=..., b=...) call, the text's {placeholders} must be supplied."""
    problems = []
    wired = _wired_command_functions()
    for rel, src in _code_files():
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        for root in _live_nodes(rel, tree, wired):
            for node in ast.walk(root):
                if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "format"):
                    continue
                inner = node.func.value
                if not (isinstance(inner, ast.Call) and getattr(inner.func, "attr", getattr(inner.func, "id", "")) == "get_translation"):
                    continue
                if len(inner.args) < 2 or not isinstance(inner.args[1], ast.Constant):
                    continue
                key = inner.args[1].value
                if key not in TABLE["en"] or any(kw.arg is None for kw in node.keywords):
                    continue  # unknown keys are reported by another test; **kwargs can't be checked
                needed = _fields(TABLE["en"][key])
                supplied = {kw.arg for kw in node.keywords}
                if not needed <= supplied:
                    problems.append(f"{rel}:{node.lineno}: {key} needs {sorted(needed - supplied)}")
    assert not problems, problems
