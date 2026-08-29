from __future__ import annotations

import re
from io import BytesIO
from typing import Any, Dict, List, Optional

import pdfplumber

from src.core.services.cv.skill_catalog import COMMON_TITLES, SKILL_CATALOG, TITLE_HINTS
from src.infrastructure.di.inject import inject

_EMAIL_RE = re.compile(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}", re.I)
_PHONE_RE = re.compile(r"(?:\+\d{1,3}[\s\-]?)?(?:\(?\d{2,4}\)?[\s\-]?)?\d{3,4}[\s\-]?\d{3,4}")
_YEARS_RE = re.compile(r"(\d{1,2})\s*\+?\s*(?:years?|yrs?)\b", re.I)
_LOCATION_RE = re.compile(
    r"(?:location|based in|lives? in|residing in)\s*[:\-]?\s*([A-Za-z ,\-]+)",
    re.I,
)


@inject
class CvParserService:
    def extract_text(self, pdf_bytes: bytes) -> str:
        pages: List[str] = []
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                pages.append(text)
        return "\n".join(pages).strip()

    def parse(self, raw_text: str) -> Dict[str, Any]:
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        lowered = raw_text.lower()
        skills = self._extract_skills(lowered)
        titles = self._extract_titles(lowered)
        return {
            "full_name": self._extract_name(lines),
            "headline": self._extract_headline(lines, titles),
            "email": self._first(_EMAIL_RE.findall(raw_text)),
            "phone": self._extract_phone(raw_text),
            "location": self._extract_location(raw_text, lines),
            "years_experience": self._extract_years(raw_text),
            "skills": skills,
            "titles": titles,
            "education": self._extract_education(raw_text),
        }

    def suggested_tags(self, parsed: Dict[str, Any]) -> List[str]:
        titles = parsed.get("titles") or []
        skills = parsed.get("skills") or []
        headline = (parsed.get("headline") or "").strip()
        tags: List[str] = []
        if titles:
            tags.append(titles[0])
        elif headline and len(headline) < 70:
            tags.append(headline)
        for skill in skills:
            if skill.lower() not in {t.lower() for t in tags}:
                tags.append(skill)
            if len(tags) >= 8:
                break
        return tags or ["software engineer"]

    def suggested_keywords(self, parsed: Dict[str, Any]) -> str:
        return " ".join(self.suggested_tags(parsed)[:4])

    def _extract_skills(self, lowered: str) -> List[str]:
        found = []
        for skill in sorted(SKILL_CATALOG, key=len, reverse=True):
            pattern = r"(?<![a-z0-9])" + re.escape(skill) + r"(?![a-z0-9])"
            if re.search(pattern, lowered):
                found.append(skill)
        # Keep original catalog casing-ish: title-case short tokens, else as catalog
        unique = []
        seen = set()
        for skill in found:
            key = skill.lower()
            if key in seen:
                continue
            seen.add(key)
            unique.append(skill)
        return unique[:40]

    def _extract_titles(self, lowered: str) -> List[str]:
        found = []
        for title in COMMON_TITLES:
            if title in lowered:
                found.append(title)
        if found:
            return self._dedupe(found)[:8]
        hinted = []
        for line in lowered.splitlines():
            if any(hint in line for hint in TITLE_HINTS) and 8 < len(line) < 80:
                hinted.append(line.strip(" -•|\t"))
        return self._dedupe(hinted)[:8]

    def _extract_name(self, lines: List[str]) -> Optional[str]:
        for line in lines[:8]:
            if "@" in line or _PHONE_RE.search(line):
                continue
            words = line.split()
            if 1 < len(words) <= 5 and line.replace(" ", "").isalpha():
                return line
            if 1 < len(words) <= 4 and all(w[:1].isupper() for w in words if w.isalpha()):
                return line
        return lines[0] if lines else None

    def _extract_headline(self, lines: List[str], titles: List[str]) -> Optional[str]:
        if titles:
            return titles[0].title()
        for line in lines[1:12]:
            lowered = line.lower()
            if any(hint in lowered for hint in TITLE_HINTS) and len(line) < 90:
                return line
        return None

    def _extract_phone(self, text: str) -> Optional[str]:
        for match in _PHONE_RE.findall(text):
            digits = re.sub(r"\D", "", match)
            if 8 <= len(digits) <= 15:
                return match.strip()
        return None

    def _extract_location(self, text: str, lines: List[str]) -> Optional[str]:
        match = _LOCATION_RE.search(text)
        if match:
            return match.group(1).strip(" ,")
        for line in lines[:15]:
            if "," in line and 6 < len(line) < 60 and "@" not in line:
                if any(ch.isalpha() for ch in line):
                    return line
        return None

    def _extract_years(self, text: str) -> Optional[int]:
        years = [int(v) for v in _YEARS_RE.findall(text) if 1 <= int(v) <= 45]
        return max(years) if years else None

    def _extract_education(self, text: str) -> List[str]:
        degrees = []
        patterns = (
            r"ph\.?d\.?", r"master(?:'s)?", r"mba", r"bachelor(?:'s)?",
            r"b\.?sc\.?", r"m\.?sc\.?", r"b\.?s\.?", r"m\.?s\.?",
            r"associate", r"diploma",
        )
        lowered = text.lower()
        for pattern in patterns:
            if re.search(rf"\b{pattern}\b", lowered):
                degrees.append(re.sub(r"\\.?\\?", "", pattern).replace("(?:'s)?", "").replace("(?:", "").replace(")", ""))
        pretty = []
        mapping = {
            "ph.d": "PhD", "phd": "PhD", "master": "Master's", "mba": "MBA",
            "bachelor": "Bachelor's", "b.sc": "B.Sc", "m.sc": "M.Sc",
            "b.s": "B.S", "m.s": "M.S", "associate": "Associate", "diploma": "Diploma",
        }
        for item in degrees:
            key = re.sub(r"[^a-z.]", "", item.lower())
            pretty.append(mapping.get(key, item))
        return self._dedupe(pretty)[:6]

    @staticmethod
    def _first(items: List[str]) -> Optional[str]:
        return items[0] if items else None

    @staticmethod
    def _dedupe(items: List[str]) -> List[str]:
        seen = set()
        result = []
        for item in items:
            key = item.strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            result.append(item.strip())
        return result
