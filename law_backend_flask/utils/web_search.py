#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
零密钥联网搜索工具。
"""

from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET
from typing import Dict, List
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


DEFAULT_WEB_SEARCH_TIMEOUT = 15
DEFAULT_WEB_RESULT_LIMIT = 3
DEFAULT_WEB_SEARCH_PROVIDERS = ("sogou", "bing_rss")
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
)


def is_web_search_requested(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "use", "on"}


def get_web_search_timeout() -> int:
    try:
        return max(3, int(os.environ.get("WEB_SEARCH_TIMEOUT_SECONDS", str(DEFAULT_WEB_SEARCH_TIMEOUT))))
    except ValueError:
        return DEFAULT_WEB_SEARCH_TIMEOUT


def get_web_result_limit() -> int:
    try:
        return max(1, min(int(os.environ.get("WEB_SEARCH_RESULT_LIMIT", str(DEFAULT_WEB_RESULT_LIMIT))), 8))
    except ValueError:
        return DEFAULT_WEB_RESULT_LIMIT


def get_web_search_providers() -> List[str]:
    raw = os.environ.get("WEB_SEARCH_PROVIDER") or ",".join(DEFAULT_WEB_SEARCH_PROVIDERS)
    providers = []
    for item in re.split(r"[\s,]+", raw):
        provider = item.strip().lower()
        if provider and provider not in providers:
            providers.append(provider)
    return providers or list(DEFAULT_WEB_SEARCH_PROVIDERS)


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def _display_source_name(link: str, provider: str) -> str:
    domain = (urlparse(link).netloc or "").lower()
    if domain.startswith("www."):
        domain = domain[4:]
    return f"{provider} · {domain}" if domain else provider


def _build_result(title: str, link: str, snippet: str, provider: str) -> Dict[str, str]:
    return {
        "title": _clean_text(title),
        "link": (link or "").strip(),
        "snippet": _clean_text(snippet),
        "provider": provider,
        "source": _display_source_name(link, provider)
    }


def _search_sogou(query: str, top_k: int) -> List[Dict[str, str]]:
    response = requests.get(
        os.environ.get("WEB_SEARCH_SOGOU_URL", "https://www.sogou.com/web"),
        params={"query": query},
        headers={"User-Agent": DEFAULT_USER_AGENT},
        timeout=get_web_search_timeout()
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    results: List[Dict[str, str]] = []
    seen_links = set()

    for item in soup.select(".vrwrap"):
        title_node = item.select_one("h3 a")
        source_node = item.select_one("[data-url]")
        snippet_node = item.select_one('div[id^="cacheresult_summary_"], .str-text-info, .base-ellipsis')

        title = title_node.get_text(" ", strip=True) if title_node else ""
        link = ""
        if source_node and source_node.get("data-url"):
            link = source_node.get("data-url")
        elif title_node and title_node.get("href", "").startswith("http"):
            link = title_node.get("href")
        snippet = snippet_node.get_text(" ", strip=True) if snippet_node else ""

        if not title or not link or link in seen_links:
            continue

        seen_links.add(link)
        results.append(_build_result(title, link, snippet, "搜狗搜索"))
        if len(results) >= top_k:
            break

    return results


def _search_bing_rss(query: str, top_k: int) -> List[Dict[str, str]]:
    response = requests.get(
        os.environ.get("WEB_SEARCH_BING_URL", "https://cn.bing.com/search"),
        params={
            "q": query,
            "format": "rss",
            "count": max(top_k, 10),
            "mkt": os.environ.get("WEB_SEARCH_BING_MARKET", "zh-CN")
        },
        headers={"User-Agent": DEFAULT_USER_AGENT},
        timeout=get_web_search_timeout()
    )
    response.raise_for_status()

    root = ET.fromstring(response.text)
    results: List[Dict[str, str]] = []
    seen_links = set()

    for item in root.findall("./channel/item"):
        title = item.findtext("title", default="")
        link = item.findtext("link", default="")
        snippet = item.findtext("description", default="")
        if not title or not link or link in seen_links:
            continue

        seen_links.add(link)
        results.append(_build_result(title, link, snippet, "必应搜索"))
        if len(results) >= top_k:
            break

    return results


def search_web(query: str, top_k: int | None = None) -> List[Dict[str, str]]:
    normalized_query = _clean_text(query)
    if not normalized_query:
        return []

    limit = max(1, min(int(top_k or get_web_result_limit()), 8))

    for provider in get_web_search_providers():
        try:
            if provider == "sogou":
                results = _search_sogou(normalized_query, limit)
            elif provider in {"bing", "bing_rss"}:
                results = _search_bing_rss(normalized_query, limit)
            else:
                continue

            if results:
                return results
        except Exception:
            continue

    return []


def format_web_search_context(results: List[Dict[str, str]], max_length: int = 320) -> str:
    blocks = []
    for index, item in enumerate(results, start=1):
        snippet = str(item.get("snippet") or "").strip()
        if len(snippet) > max_length:
            snippet = snippet[:max_length].rstrip() + "..."

        blocks.append(
            f"[网页{index}] 标题: {item.get('title')} | 来源: {item.get('source')}\n"
            f"链接: {item.get('link')}\n"
            f"摘要: {snippet or '无摘要'}"
        )

    return "\n\n".join(blocks)
