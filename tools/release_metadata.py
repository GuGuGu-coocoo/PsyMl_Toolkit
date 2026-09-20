"""Release label rules shared by the packaging tools.

``src/psyml/__init__.py`` remains the only maintained version constant; the
release label is its ``v``-prefixed form. An explicit ``--label`` stays
available for regenerating historical documents, which are then marked as
historical (or as a development QA document for ``*.dev*`` labels) instead of
being mistaken for the current release.
"""

from __future__ import annotations

from psyml import __version__ as CORE_VERSION

CURRENT_LABEL = "v" + CORE_VERSION


def default_label() -> str:
    """The label of the current release derived from the single core version."""
    return CURRENT_LABEL


def label_version(label: str) -> str:
    """The version part of a release label, without an optional ``v`` prefix."""
    return label.strip().lstrip("vV")


def is_current_label(label: str) -> bool:
    return label.strip() == CURRENT_LABEL


def is_development_label(label: str) -> bool:
    """PEP 440-style development label, for example ``v0.3.0.dev1``."""
    return ".dev" in label_version(label)


def notice_for_label(label: str) -> str | None:
    """The document banner for a non-current label, or ``None`` for current."""
    if is_current_label(label):
        return None
    if is_development_label(label):
        return (
            f"<b>开发版 QA 文档（{label}）：</b>本文件由当前开发源码生成，"
            f"描述尚未发布的功能，不适用于 {CURRENT_LABEL} 下载包；"
            "发布版请以下载包内 PDF 为准。"
        )
    return (
        f"<b>历史版本文档（{label}）：</b>本文件按显式指定的历史标签生成，"
        f"不是当前正式版本 {CURRENT_LABEL} 的分发文档；"
        "请以下载包内对应版本的 PDF 为准。"
    )
