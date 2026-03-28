#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地知识库索引与检索工具。
"""

from __future__ import annotations

import io
import json
import os
import re
import shutil
import subprocess
import tempfile
from typing import Dict, List, Sequence

from docx import Document as DocxDocument
from flask import current_app
from pypdf import PdfReader
from sqlalchemy import and_, or_

from models import db, KnowledgeChunk
from utils import download_file


DEFAULT_CHUNK_SIZE = 900
DEFAULT_CHUNK_OVERLAP = 120
DEFAULT_MAX_CONTEXT_CHUNKS = 6


def get_chunk_size() -> int:
    try:
        return max(300, int(os.environ.get('KNOWLEDGE_CHUNK_SIZE', str(DEFAULT_CHUNK_SIZE))))
    except ValueError:
        return DEFAULT_CHUNK_SIZE


def get_chunk_overlap() -> int:
    try:
        return max(50, int(os.environ.get('KNOWLEDGE_CHUNK_OVERLAP', str(DEFAULT_CHUNK_OVERLAP))))
    except ValueError:
        return DEFAULT_CHUNK_OVERLAP


def get_max_context_chunks() -> int:
    try:
        return max(1, int(os.environ.get('KNOWLEDGE_MAX_CONTEXT_CHUNKS', str(DEFAULT_MAX_CONTEXT_CHUNKS))))
    except ValueError:
        return DEFAULT_MAX_CONTEXT_CHUNKS


def normalize_knowledge_types(knowledge_types: Sequence[str] | None) -> List[str]:
    valid_types = []
    for knowledge_type in knowledge_types or []:
        if knowledge_type in ('public', 'private') and knowledge_type not in valid_types:
            valid_types.append(knowledge_type)
    return valid_types


def _decode_text_bytes(file_bytes: bytes) -> str:
    for encoding in ('utf-8', 'utf-8-sig', 'gb18030', 'gbk'):
        try:
            return file_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    return file_bytes.decode('utf-8', errors='ignore')


def _extract_text_from_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_bytes))
    return '\n\n'.join((page.extract_text() or '').strip() for page in reader.pages)


def _extract_text_from_docx(file_bytes: bytes) -> str:
    document = DocxDocument(io.BytesIO(file_bytes))
    parts = []
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if text:
            parts.append(text)
    return '\n\n'.join(parts)


def _extract_text_from_doc(file_bytes: bytes) -> str:
    for command in ('antiword', 'catdoc'):
        executable = shutil.which(command)
        if not executable:
            continue

        with tempfile.NamedTemporaryFile(suffix='.doc', delete=False) as temp_file:
            temp_file.write(file_bytes)
            temp_path = temp_file.name

        try:
            result = subprocess.run(
                [executable, temp_path],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',
                timeout=30,
                check=False
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout
        finally:
            try:
                os.remove(temp_path)
            except OSError:
                pass

    raise ValueError('当前环境暂不支持 .doc 文件解析，请优先上传 PDF、DOCX、TXT 或 JSON 文件')


def extract_text_from_bytes(file_bytes: bytes, filename: str) -> str:
    extension = os.path.splitext(filename or '')[1].lower()

    if extension == '.pdf':
        return _extract_text_from_pdf(file_bytes)
    if extension == '.docx':
        return _extract_text_from_docx(file_bytes)
    if extension == '.doc':
        return _extract_text_from_doc(file_bytes)
    if extension in ('.txt', '.md'):
        return _decode_text_bytes(file_bytes)
    if extension == '.json':
        raw_text = _decode_text_bytes(file_bytes)
        try:
            parsed = json.loads(raw_text)
            return json.dumps(parsed, ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            return raw_text

    raise ValueError(f'暂不支持将 {extension or "未知类型"} 文件导入知识库')


def normalize_text(text: str) -> str:
    text = (text or '').replace('\r\n', '\n').replace('\r', '\n').replace('\x00', '')
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def chunk_text(text: str, chunk_size: int | None = None, overlap: int | None = None) -> List[str]:
    chunk_size = chunk_size or get_chunk_size()
    overlap = overlap or get_chunk_overlap()
    normalized = normalize_text(text)

    if not normalized:
        return []
    if len(normalized) <= chunk_size:
        return [normalized]

    chunks: List[str] = []
    start = 0
    text_length = len(normalized)

    while start < text_length:
        target_end = min(text_length, start + chunk_size)
        end = target_end

        if target_end < text_length:
            search_start = min(text_length, start + max(100, chunk_size // 2))
            boundary = max(
                normalized.rfind('\n\n', search_start, target_end),
                normalized.rfind('\n', search_start, target_end),
                normalized.rfind('。', search_start, target_end),
                normalized.rfind('！', search_start, target_end),
                normalized.rfind('？', search_start, target_end),
                normalized.rfind('；', search_start, target_end),
                normalized.rfind('.', search_start, target_end)
            )
            if boundary > start:
                end = boundary + 1

        chunk = normalized[start:end].strip()
        if chunk and (not chunks or chunk != chunks[-1]):
            chunks.append(chunk)

        if end >= text_length:
            break

        next_start = max(end - overlap, start + 1)
        if next_start <= start:
            next_start = end
        start = next_start

    return chunks


def load_minio_file_bytes(minio_path: str) -> bytes:
    file_obj = download_file(minio_path)
    if not file_obj:
        raise ValueError('文件下载失败，未能从对象存储读取文件内容')

    try:
        file_bytes = file_obj.read()
    finally:
        try:
            file_obj.close()
        except Exception:
            pass

    if not file_bytes:
        raise ValueError('文件内容为空，无法导入知识库')

    return file_bytes


def index_user_file_to_knowledge(user_file, owner_user, knowledge_types: Sequence[str]) -> Dict[str, int]:
    normalized_types = normalize_knowledge_types(knowledge_types)
    if not normalized_types:
        raise ValueError('未提供有效的知识库类型')

    file_bytes = load_minio_file_bytes(user_file.minio_path)
    raw_text = extract_text_from_bytes(file_bytes, user_file.filename)
    clean_text = normalize_text(raw_text)
    if not clean_text:
        raise ValueError('文件解析成功，但未提取到可用文本')

    chunks = chunk_text(clean_text)
    if not chunks:
        raise ValueError('文件内容过短，无法切分为知识片段')

    KnowledgeChunk.query.filter(
        KnowledgeChunk.user_file_id == user_file.id,
        KnowledgeChunk.knowledge_type.in_(normalized_types)
    ).delete(synchronize_session=False)

    for knowledge_type in normalized_types:
        for chunk_index, chunk in enumerate(chunks):
            db.session.add(KnowledgeChunk(
                user_file_id=user_file.id,
                owner_user_id=owner_user.id,
                knowledge_type=knowledge_type,
                filename=user_file.filename,
                file_category=user_file.file_category,
                chunk_index=chunk_index,
                content=chunk,
                content_preview=chunk[:200]
            ))

    db.session.flush()
    current_app.logger.info(
        "本地知识库入库完成: file_id=%s knowledge_types=%s chunks=%s",
        user_file.id,
        normalized_types,
        len(chunks)
    )
    return {
        'chunk_count': len(chunks),
        'knowledge_type_count': len(normalized_types)
    }


def remove_user_file_from_knowledge(user_file_id: int, knowledge_types: Sequence[str] | None = None) -> int:
    query = KnowledgeChunk.query.filter(KnowledgeChunk.user_file_id == user_file_id)
    normalized_types = normalize_knowledge_types(knowledge_types)
    if normalized_types:
        query = query.filter(KnowledgeChunk.knowledge_type.in_(normalized_types))

    deleted_count = query.delete(synchronize_session=False)
    db.session.flush()
    return deleted_count


def _normalize_for_search(text: str) -> str:
    return re.sub(r'\s+', '', (text or '').lower())


def _extract_query_terms(text: str) -> List[str]:
    seen = set()
    terms: List[str] = []
    normalized = _normalize_for_search(text)

    for term in re.findall(r'[a-z0-9_]+|[\u4e00-\u9fff]{2,}', normalized):
        if term not in seen:
            seen.add(term)
            terms.append(term)
        if re.search(r'[\u4e00-\u9fff]', term):
            for size in (2, 3):
                for index in range(0, max(0, len(term) - size + 1)):
                    ngram = term[index:index + size]
                    if ngram not in seen:
                        seen.add(ngram)
                        terms.append(ngram)

    return terms


def _build_ngrams(text: str, sizes: Sequence[int] = (2, 3)) -> set[str]:
    compact = _normalize_for_search(text)
    compact = ''.join(ch for ch in compact if ch.isalnum() or '\u4e00' <= ch <= '\u9fff')
    ngrams: set[str] = set()
    for size in sizes:
        if len(compact) < size:
            continue
        for index in range(0, len(compact) - size + 1):
            ngrams.add(compact[index:index + size])
    return ngrams


def _score_chunk(question: str, content: str, title: str) -> float:
    question_compact = _normalize_for_search(question)
    content_compact = _normalize_for_search(content)
    title_compact = _normalize_for_search(title)

    if not question_compact or not content_compact:
        return 0.0

    score = 0.0
    if question_compact in content_compact:
        score += 18.0
    if question_compact in title_compact:
        score += 12.0

    for term in _extract_query_terms(question):
        if len(term) < 2:
            continue
        term_length_weight = min(len(term), 8)
        content_hits = min(content_compact.count(term), 5)
        title_hits = min(title_compact.count(term), 3)
        if content_hits:
            score += content_hits * (1.6 + term_length_weight * 0.55)
        if title_hits:
            score += title_hits * (3.0 + term_length_weight * 0.75)

    question_ngrams = _build_ngrams(question)
    if question_ngrams:
        content_ngrams = _build_ngrams(content)
        overlap_ratio = len(question_ngrams & content_ngrams) / max(len(question_ngrams), 1)
        score += overlap_ratio * 20.0

    return round(score, 4)


def search_knowledge_chunks(user_id: int, question: str, mode: str, top_k: int = 3) -> List[Dict[str, object]]:
    if not question or mode == 'none_knowledge':
        return []

    query = KnowledgeChunk.query
    if mode == 'shared_knowledge':
        query = query.filter(KnowledgeChunk.knowledge_type == 'public')
    elif mode == 'private_knowledge':
        query = query.filter(
            KnowledgeChunk.knowledge_type == 'private',
            KnowledgeChunk.owner_user_id == user_id
        )
    elif mode in ('entire_knowledge', 'knowledgeQA'):
        query = query.filter(or_(
            KnowledgeChunk.knowledge_type == 'public',
            and_(
                KnowledgeChunk.knowledge_type == 'private',
                KnowledgeChunk.owner_user_id == user_id
            )
        ))
    else:
        return []

    candidates = query.all()
    if not candidates:
        return []

    limit = max(1, min(int(top_k or 3) * 2, get_max_context_chunks()))
    scored_candidates = []
    for chunk in candidates:
        score = _score_chunk(question, chunk.content, chunk.filename)
        if score > 0:
            scored_candidates.append((score, chunk))

    if not scored_candidates:
        return []

    results: List[Dict[str, object]] = []
    file_hit_count: Dict[tuple[int, str], int] = {}
    for score, chunk in sorted(scored_candidates, key=lambda item: item[0], reverse=True):
        file_key = (chunk.user_file_id, chunk.knowledge_type)
        if file_hit_count.get(file_key, 0) >= 2:
            continue

        results.append({
            'chunk_id': chunk.id,
            'user_file_id': chunk.user_file_id,
            'knowledge_type': chunk.knowledge_type,
            'filename': chunk.filename,
            'file_category': chunk.file_category,
            'chunk_index': chunk.chunk_index,
            'score': score,
            'content': chunk.content
        })
        file_hit_count[file_key] = file_hit_count.get(file_key, 0) + 1

        if len(results) >= limit:
            break

    return results


def format_knowledge_context(results: Sequence[Dict[str, object]], max_length: int = 700) -> str:
    blocks = []
    for index, item in enumerate(results, start=1):
        content = str(item.get('content') or '').strip()
        if len(content) > max_length:
            content = content[:max_length].rstrip() + '...'
        knowledge_label = '公有知识库' if item.get('knowledge_type') == 'public' else '私有知识库'
        blocks.append(
            f"[资料{index}] 文件名: {item.get('filename')} | 来源: {knowledge_label}\n{content}"
        )
    return '\n\n'.join(blocks)
