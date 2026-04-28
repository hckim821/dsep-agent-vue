"""Re-derive wiki_pages.title from each page's first H1 in the actual markdown file.

Use this once after fixing connection charset to repair mojibake-corrupted titles.
"""
import io
import os
import re
import sys

# Windows 콘솔이 cp949여도 utf-8로 출력
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from wiki_pipeline.db import SessionLocal
from wiki_pipeline.wiki_repo import read_page
from app.models.wiki import WikiPage


def first_h1(md: str) -> str | None:
    m = re.search(r"^\s*#\s+(.+)$", md, re.MULTILINE)
    return m.group(1).strip() if m else None


def main() -> None:
    sess = SessionLocal()
    try:
        pages = sess.query(WikiPage).all()
        fixed = 0
        skipped = 0
        for pg in pages:
            content = read_page(pg.path)
            if not content:
                print(f"[skip] {pg.path}: file not found")
                skipped += 1
                continue
            title = first_h1(content)
            if not title:
                continue
            if title != pg.title:
                print(f"[fix ] {pg.path}\n        old: {pg.title!r}\n        new: {title!r}")
                pg.title = title
                fixed += 1
        sess.commit()
        print(f"\nDone — fixed {fixed} titles, {skipped} files missing.")
    finally:
        sess.close()


if __name__ == "__main__":
    main()
