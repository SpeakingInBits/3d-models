"""Find the models in this repo and read the parameters from the top of each script.

Nothing in a model's script needs to change for it to show up here. Any folder with a script that
has a main() and an OUT folder is a model, and any constant set to a plain value above the first
function is a parameter. Constants worked out from other constants are left alone, so they follow
whatever the parameters are set to.
"""

import ast
import io
import re
import sys
import tokenize
from dataclasses import dataclass
from pathlib import Path

FROZEN = getattr(sys, "frozen", False)  # True in the installed app, which has the models bundled
ROOT = Path(sys._MEIPASS) / "models" if FROZEN else Path(__file__).resolve().parent.parent
WORDS = {"W": "width", "H": "height", "T": "thickness", "R": "radius", "L": "length", "D": "depth",
         "BB": "billboard", "QR": "QR"}
DIAMETERS = {"MAGSAFE_D", "WATCH_D", "FOOT_D", "CUP_D", "CUP_BOTTOM_D", "CUP_HOLE_D",
             "BASKET_HOLE_D"}  # D means depth everywhere else


@dataclass
class Param:
    name: str
    kind: str  # length, angle, ratio, count, flag or text
    default: object
    section: str
    note: str

    @property
    def label(self):
        words = [WORDS.get(word, word.lower()) for word in self.name.split("_")]
        if self.name in DIAMETERS:
            words[-1] = "diameter"
        label = " ".join(words)
        return label[0].upper() + label[1:]


@dataclass
class Model:
    title: str
    summary: str
    script: Path
    params: list

    @property
    def key(self):
        return self.script.parent.name

    @property
    def preview(self):
        """The default model's picture, if it has one."""
        for name in ("preview_angle.png", "preview_stand.png"):
            path = self.script.parent / "out" / name
            if path.exists():
                return path
        return None

    @property
    def stickers_file(self):
        """The default model's sticker sizes. Only models with sticker spots write this."""
        return self.script.parent / "out" / "stickers.json"


def plain_value(node):
    """The value of a literal or sum like 4 / 3, or None if it depends on anything else."""
    allowed = (ast.Constant, ast.BinOp, ast.UnaryOp, ast.operator, ast.unaryop)
    if not all(isinstance(part, allowed) for part in ast.walk(node)):
        return None
    return eval(compile(ast.Expression(node), "<parameter>", "eval"))


def kind_of(name, value):
    if isinstance(value, bool):
        return "flag"
    if isinstance(value, str):
        return "text"
    if re.search("ANGLE|TILT|OVERHANG", name):
        return "angle"
    if "ASPECT" in name:
        return "ratio"
    return "count" if isinstance(value, int) else "length"  # the scripts work in millimetres


def assignments(tree):
    """(name, value node, line) of each constant set above the first function or class."""
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            return
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name):
            yield target.id, node.value, node.end_lineno
        elif isinstance(target, ast.Tuple) and isinstance(node.value, ast.Tuple):
            for name, value in zip(target.elts, node.value.elts):
                yield name.id, value, node.end_lineno


def read_params(source, tree):
    comments = {token.start[0]: token.string.lstrip("# ").strip()
                for token in tokenize.generate_tokens(io.StringIO(source).readline)
                if token.type == tokenize.COMMENT}
    sections = {line: re.sub("^-+ *", "", text) for line, text in comments.items()
                if re.match("-{5,}", text)}
    params = []
    for name, node, line in assignments(tree):
        value = plain_value(node)
        if value is None or name == "OUT":
            continue
        section = max((l for l in sections if l < line), default=None)
        title = sections[section] if section else "general"
        params.append(Param(name, kind_of(name, value), value, title[0].upper() + title[1:],
                            comments.get(line, "")))
    return params


def read_title(folder):
    readme = folder / "README.md"
    if readme.exists():
        for line in readme.read_text(encoding="utf-8").splitlines():
            if line.startswith("# "):
                return line[2:].strip()
    return folder.name.replace("-", " ").capitalize()


def find_models():
    models = []
    for script in sorted(ROOT.glob("*/*.py")):
        if script.parent.name == "configurator" or script.name == "render.py":
            continue
        source = script.read_text(encoding="utf-8")
        tree = ast.parse(source)
        has_main = any(isinstance(n, ast.FunctionDef) and n.name == "main" for n in tree.body)
        if not has_main or "OUT" not in [name for name, _, _ in assignments(tree)]:
            continue
        summary = (ast.get_docstring(tree) or "").split("\n\n")[0].replace("\n", " ")
        models.append(Model(read_title(script.parent), summary, script, read_params(source, tree)))
    return models
