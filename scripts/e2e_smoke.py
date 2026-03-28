#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

import requests


BASE_URL = os.environ.get("RAGLEX_BASE_URL", "http://127.0.0.1:5000").rstrip("/")
TIMEOUT = int(os.environ.get("RAGLEX_SMOKE_TIMEOUT", "120"))


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def post_json(session: requests.Session, url: str, payload: dict, **kwargs):
    response = session.post(url, json=payload, timeout=TIMEOUT, **kwargs)
    return response


def login_user(session: requests.Session, username: str, password: str) -> str:
    response = post_json(session, f"{BASE_URL}/api/auth/login", {
        "username": username,
        "password": password,
    })
    response.raise_for_status()
    data = response.json()
    return data["data"]["access_token"]


def create_user(session: requests.Session, prefix: str) -> tuple[str, str]:
    username = f"{prefix}_{int(time.time() * 1000)}"
    email = f"{username}@example.com"
    password = "Test1234"

    response = post_json(session, f"{BASE_URL}/api/auth/register", {
        "username": username,
        "email": email,
        "password": password,
        "full_name": prefix,
    })
    response.raise_for_status()
    return username, password


def create_conversation(session: requests.Session, headers: dict, title: str) -> int:
    response = post_json(session, f"{BASE_URL}/api/conversations/", {"title": title}, headers=headers)
    response.raise_for_status()
    return response.json()["data"]["id"]


def upload_text_file(session: requests.Session, headers: dict, filename: str, text: str, *,
                     file_category: str, case_subject: str, case_notes: str) -> int:
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as handle:
        handle.write(text)
        temp_path = Path(handle.name)

    try:
        with temp_path.open("rb") as file_handle:
            response = session.post(
                f"{BASE_URL}/api/files/upload",
                headers=headers,
                files={"file": (filename, file_handle, "text/plain")},
                data={
                    "file_category": file_category,
                    "case_subject": case_subject,
                    "case_notes": case_notes,
                },
                timeout=TIMEOUT,
            )
        response.raise_for_status()
        return response.json()["data"]["id"]
    finally:
        temp_path.unlink(missing_ok=True)


def upload_knowledge(session: requests.Session, headers: dict, file_id: int, knowledge_types: list[str]):
    response = post_json(
        session,
        f"{BASE_URL}/api/files/{file_id}/upload-knowledge",
        {"knowledge_types": knowledge_types},
        headers={**headers, "Content-Type": "application/json"},
    )
    response.raise_for_status()
    return response.json()


def download_uploaded_file(session: requests.Session, headers: dict, file_id: int) -> bytes:
    response = session.get(
        f"{BASE_URL}/api/files/{file_id}/download",
        headers=headers,
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    return response.content


def cancel_knowledge(session: requests.Session, headers: dict, file_id: int, knowledge_types: list[str]):
    response = post_json(
        session,
        f"{BASE_URL}/api/files/{file_id}/cancel-knowledge",
        {"knowledge_types": knowledge_types},
        headers={**headers, "Content-Type": "application/json"},
    )
    response.raise_for_status()
    return response.json()


def ask_question(session: requests.Session, headers: dict, *, question: str, conversation_id: int, mode: str):
    response = post_json(
        session,
        f"{BASE_URL}/api/query",
        {
            "question": question,
            "conversation_id": conversation_id,
            "embedding_model": "text2vec-base",
            "large_language_model": os.environ.get("OPENAI_CHAT_MODEL", "qwen2.5:7b"),
            "top_k": 3,
            "web_search": "notUse",
            "mode": mode,
        },
        headers={**headers, "Content-Type": "application/json"},
    )
    response.raise_for_status()
    return response.json()["data"]


def main() -> int:
    print(f"[smoke] base_url={BASE_URL}")
    health = requests.get(f"{BASE_URL}/api/health", timeout=TIMEOUT)
    health.raise_for_status()
    print("[smoke] health=", health.text)

    session = requests.Session()

    private_username, private_password = create_user(session, "raglex_private")
    private_token = login_user(session, private_username, private_password)
    private_headers = {"Authorization": f"Bearer {private_token}"}

    private_conversation_id = create_conversation(session, private_headers, "private smoke")
    private_text = (
        "借款合同纠纷案例\n\n"
        "张三与李四签订借款合同，借款金额为人民币100000元，借款期限12个月，年利率6%。\n"
        "若李四逾期还款，则按未还本金每日万分之五支付违约金。\n"
    )
    private_file_id = upload_text_file(
        session,
        private_headers,
        f"{private_username}.txt",
        private_text,
        file_category="case",
        case_subject="借款合同纠纷",
        case_notes="private smoke",
    )
    downloaded_private_file = download_uploaded_file(session, private_headers, private_file_id).decode("utf-8")
    assert_true("借款金额为人民币100000元" in downloaded_private_file, "downloaded private file content mismatch")
    upload_knowledge(session, private_headers, private_file_id, ["private"])
    private_answer = ask_question(
        session,
        private_headers,
        question="这个案例中的借款金额是多少？违约金约定是什么？",
        conversation_id=private_conversation_id,
        mode="private_knowledge",
    )
    print("[smoke] private answer=", json.dumps(private_answer, ensure_ascii=False))
    assert_true("100000" in private_answer["answer"], "private knowledge answer did not mention 100000")
    assert_true(private_answer["sources"], "private knowledge answer did not return sources")

    public_session = requests.Session()
    public_username, public_password = create_user(public_session, "raglex_public")
    public_token = login_user(public_session, public_username, public_password)
    public_headers = {"Authorization": f"Bearer {public_token}"}

    public_file_id = upload_text_file(
        public_session,
        public_headers,
        f"{public_username}.txt",
        "公有知识库案例\n\n本案材料中的唯一识别码是 ALPHA-3729-ZETA。\n",
        file_category="case",
        case_subject="共享知识库测试",
        case_notes="public smoke",
    )
    upload_knowledge(public_session, public_headers, public_file_id, ["public"])

    shared_conversation_id = create_conversation(public_session, public_headers, "public smoke")
    shared_answer = ask_question(
        public_session,
        public_headers,
        question="材料中的唯一识别码是什么？",
        conversation_id=shared_conversation_id,
        mode="shared_knowledge",
    )
    print("[smoke] public answer=", json.dumps(shared_answer, ensure_ascii=False))
    assert_true("ALPHA-3729-ZETA" in shared_answer["answer"], "shared knowledge answer did not mention the expected code")
    assert_true(shared_answer["sources"], "shared knowledge answer did not return sources")

    cancel_knowledge(public_session, public_headers, public_file_id, ["public"])
    shared_conversation_id_2 = create_conversation(public_session, public_headers, "public smoke after cancel")
    after_cancel = ask_question(
        public_session,
        public_headers,
        question="材料中的唯一识别码是什么？",
        conversation_id=shared_conversation_id_2,
        mode="shared_knowledge",
    )
    print("[smoke] after cancel=", json.dumps(after_cancel, ensure_ascii=False))
    assert_true(not after_cancel["sources"], "public knowledge sources should be empty after cancel")

    messages_response = public_session.get(
        f"{BASE_URL}/api/conversations/{shared_conversation_id}/messages",
        headers=public_headers,
        timeout=TIMEOUT,
    )
    messages_response.raise_for_status()
    messages_data = messages_response.json()["data"]["messages"]
    assert_true(len(messages_data) >= 3, "conversation history was not persisted")

    print("[smoke] all checks passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[smoke] FAILED: {exc}", file=sys.stderr)
        raise
