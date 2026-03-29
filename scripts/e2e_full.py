#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import os
import time
import uuid
from typing import Iterable

import requests


BASE_URL = os.environ.get("RAGLEX_BASE_URL", "http://127.0.0.1:13000").rstrip("/")
TIMEOUT = int(os.environ.get("RAGLEX_E2E_TIMEOUT", "120"))
PASSWORD = os.environ.get("RAGLEX_E2E_PASSWORD", "Test1234")


def ensure(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def api(path: str) -> str:
    normalized = path if path.startswith("/") else f"/{path}"
    return f"{BASE_URL}{normalized}"


def log_step(message: str) -> None:
    print(f"[e2e] {message}", flush=True)


def request(
    session: requests.Session,
    method: str,
    path: str,
    *,
    expected_status: int | None = None,
    headers: dict | None = None,
    **kwargs,
) -> requests.Response:
    response = session.request(
        method,
        api(path),
        headers=headers,
        timeout=TIMEOUT,
        **kwargs,
    )
    if expected_status is not None:
        ensure(
            response.status_code == expected_status,
            f"{method} {path} expected {expected_status}, got {response.status_code}: {response.text[:500]}",
        )
    return response


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def unique_name(prefix: str) -> str:
    return f"{prefix}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"


def register_user(session: requests.Session, prefix: str) -> tuple[str, str]:
    username = unique_name(prefix)
    payload = {
        "username": username,
        "email": f"{username}@example.com",
        "password": PASSWORD,
        "full_name": prefix,
    }
    response = request(session, "POST", "/api/auth/register", expected_status=201, json=payload)
    data = response.json()
    ensure(data.get("success") is True, f"register failed: {data}")
    return username, PASSWORD


def login_user(session: requests.Session, username: str, password: str) -> str:
    response = request(
        session,
        "POST",
        "/api/auth/login",
        expected_status=200,
        json={"username": username, "password": password},
    )
    data = response.json()
    ensure(data.get("success") is True, f"login failed: {data}")
    return data["data"]["access_token"]


def create_conversation(session: requests.Session, token: str, title: str) -> int:
    response = request(
        session,
        "POST",
        "/api/conversations/",
        expected_status=200,
        headers=auth_headers(token),
        json={"title": title},
    )
    data = response.json()
    ensure(data.get("success") is True, f"create conversation failed: {data}")
    return data["data"]["id"]


def get_messages(session: requests.Session, token: str, conversation_id: int) -> dict:
    response = request(
        session,
        "GET",
        f"/api/conversations/{conversation_id}/messages",
        expected_status=200,
        headers=auth_headers(token),
    )
    data = response.json()
    ensure(data.get("success") is True, f"get messages failed: {data}")
    return data["data"]


def get_context(session: requests.Session, token: str, conversation_id: int, *, expected_status: int = 200) -> requests.Response:
    return request(
        session,
        "GET",
        f"/api/conversations/{conversation_id}/context",
        expected_status=expected_status,
        headers=auth_headers(token),
    )


def rename_conversation(
    session: requests.Session,
    token: str,
    conversation_id: int,
    title: str,
    *,
    expected_status: int = 200,
) -> requests.Response:
    return request(
        session,
        "PUT",
        f"/api/conversations/{conversation_id}",
        expected_status=expected_status,
        headers={**auth_headers(token), "Content-Type": "application/json"},
        json={"title": title},
    )


def delete_conversation(
    session: requests.Session,
    token: str,
    conversation_id: int,
    *,
    expected_status: int = 200,
) -> requests.Response:
    return request(
        session,
        "DELETE",
        f"/api/conversations/{conversation_id}",
        expected_status=expected_status,
        headers=auth_headers(token),
    )


def upload_text_file(
    session: requests.Session,
    token: str,
    filename: str,
    text: str,
    *,
    file_category: str = "case",
    case_subject: str = "",
    case_notes: str = "",
    expected_status: int = 201,
) -> requests.Response:
    return request(
        session,
        "POST",
        "/api/files/upload",
        expected_status=expected_status,
        headers=auth_headers(token),
        files={"file": (filename, text.encode("utf-8"), "text/plain")},
        data={
            "file_category": file_category,
            "case_subject": case_subject,
            "case_notes": case_notes,
        },
    )


def batch_upload_text_files(
    session: requests.Session,
    token: str,
    entries: Iterable[dict],
    *,
    file_category: str = "case",
    case_subject: str = "",
    case_notes: str = "",
) -> dict:
    files = [
        ("files", (entry["filename"], entry["content"].encode("utf-8"), "text/plain"))
        for entry in entries
    ]
    response = request(
        session,
        "POST",
        "/api/files/batch-upload",
        expected_status=201,
        headers=auth_headers(token),
        files=files,
        data={
            "file_category": file_category,
            "case_subject": case_subject,
            "case_notes": case_notes,
        },
    )
    data = response.json()
    ensure(data.get("success") is True, f"batch upload failed: {data}")
    return data["data"]


def list_files(session: requests.Session, token: str, *, search: str | None = None) -> list[dict]:
    params = {"page": 1, "per_page": 100}
    if search:
        params["search"] = search
    response = request(
        session,
        "GET",
        "/api/files",
        expected_status=200,
        headers=auth_headers(token),
        params=params,
    )
    data = response.json()
    ensure(data.get("success") is True, f"list files failed: {data}")
    return data["data"]["files"]


def update_file(session: requests.Session, token: str, file_id: int, payload: dict) -> dict:
    response = request(
        session,
        "PUT",
        f"/api/files/{file_id}",
        expected_status=200,
        headers={**auth_headers(token), "Content-Type": "application/json"},
        json=payload,
    )
    data = response.json()
    ensure(data.get("success") is True, f"update file failed: {data}")
    return data["data"]


def download_file(session: requests.Session, token: str, file_id: int) -> bytes:
    response = request(
        session,
        "GET",
        f"/api/files/{file_id}/download",
        expected_status=200,
        headers=auth_headers(token),
    )
    return response.content


def upload_knowledge(session: requests.Session, token: str, file_id: int, knowledge_types: list[str]) -> dict:
    response = request(
        session,
        "POST",
        f"/api/files/{file_id}/upload-knowledge",
        expected_status=200,
        headers={**auth_headers(token), "Content-Type": "application/json"},
        json={"knowledge_types": knowledge_types},
    )
    data = response.json()
    ensure(data.get("success") is True, f"upload knowledge failed: {data}")
    return data["data"]


def cancel_knowledge(session: requests.Session, token: str, file_id: int, knowledge_types: list[str]) -> dict:
    response = request(
        session,
        "POST",
        f"/api/files/{file_id}/cancel-knowledge",
        expected_status=200,
        headers={**auth_headers(token), "Content-Type": "application/json"},
        json={"knowledge_types": knowledge_types},
    )
    data = response.json()
    ensure(data.get("success") is True, f"cancel knowledge failed: {data}")
    return data["data"]


def batch_upload_knowledge(session: requests.Session, token: str, file_ids: list[int], knowledge_types: list[str]) -> dict:
    response = request(
        session,
        "POST",
        "/api/files/batch-upload-knowledge",
        expected_status=200,
        headers={**auth_headers(token), "Content-Type": "application/json"},
        json={"file_ids": file_ids, "knowledge_types": knowledge_types},
    )
    data = response.json()
    ensure(data.get("success") is True, f"batch upload knowledge failed: {data}")
    return data["data"]


def batch_upload_knowledge_progress(
    session: requests.Session,
    token: str,
    file_ids: list[int],
    knowledge_types: list[str],
) -> dict:
    response = request(
        session,
        "POST",
        "/api/files/batch-upload-knowledge-progress",
        expected_status=200,
        headers={**auth_headers(token), "Content-Type": "application/json"},
        json={"file_ids": file_ids, "knowledge_types": knowledge_types},
        stream=True,
    )

    final_event = None
    for raw_line in response.iter_lines(decode_unicode=True):
        if not raw_line or not raw_line.startswith("data: "):
            continue
        payload = json.loads(raw_line[6:])
        if payload.get("type") == "complete":
            final_event = payload
            break

    ensure(final_event is not None, "progress upload did not emit complete event")
    ensure(final_event.get("success") is True, f"progress upload failed: {final_event}")
    return final_event["data"]


def delete_file(session: requests.Session, token: str, file_id: int) -> None:
    response = request(
        session,
        "DELETE",
        f"/api/files/{file_id}",
        expected_status=200,
        headers=auth_headers(token),
    )
    data = response.json()
    ensure(data.get("success") is True, f"delete file failed: {data}")


def ask_question(
    session: requests.Session,
    token: str,
    question: str,
    *,
    mode: str,
    web_search: str = "notUse",
    conversation_id: int | None = None,
) -> dict:
    payload = {
        "question": question,
        "embedding_model": "text2vec-base",
        "large_language_model": os.environ.get("RAGLEX_E2E_MODEL", "qwen2.5:7b"),
        "top_k": 3,
        "web_search": web_search,
        "mode": mode,
    }
    if conversation_id is not None:
        payload["conversation_id"] = conversation_id

    response = request(
        session,
        "POST",
        "/api/query",
        expected_status=200,
        headers={**auth_headers(token), "Content-Type": "application/json"},
        json=payload,
    )
    data = response.json()
    ensure(data.get("success") is True, f"ask question failed: {data}")
    return data["data"]


def ask_in_new_conversation(
    session: requests.Session,
    token: str,
    title: str,
    question: str,
    *,
    mode: str,
    web_search: str = "notUse",
) -> dict:
    conversation_id = create_conversation(session, token, title)
    return ask_question(
        session,
        token,
        question,
        mode=mode,
        web_search=web_search,
        conversation_id=conversation_id,
    )


def extract_file_ids(batch_result: dict) -> list[int]:
    return [item["file_id"] for item in batch_result["successful_files"]]


def main() -> int:
    log_step(f"base_url={BASE_URL}")

    probe = requests.get(api("/api/health"), timeout=TIMEOUT)
    probe.raise_for_status()
    health = probe.json()
    ensure(health.get("status") == "healthy", f"unexpected health payload: {health}")

    owner_session = requests.Session()
    viewer_session = requests.Session()

    owner_username, owner_password = register_user(owner_session, "raglex_owner")
    viewer_username, viewer_password = register_user(viewer_session, "raglex_viewer")
    owner_token = login_user(owner_session, owner_username, owner_password)
    viewer_token = login_user(viewer_session, viewer_username, viewer_password)

    request(owner_session, "GET", "/api/auth/profile", expected_status=200, headers=auth_headers(owner_token))
    request(viewer_session, "GET", "/api/auth/profile", expected_status=200, headers=auth_headers(viewer_token))
    log_step("auth ok")

    suffix = uuid.uuid4().hex[:8].upper()
    private_token = f"PRIVATE-{suffix}"
    pub_priv_token = f"PUBPRIV-{suffix}"
    priv_pub_token = f"PRIVPUB-{suffix}"
    batch_public_token = f"BATCHPUBLIC-{suffix}"
    delete_token = f"DELETEBATCH-{suffix}"

    private_filename = f"private_case_{suffix}.txt"
    private_upload = upload_text_file(
        owner_session,
        owner_token,
        private_filename,
        (
            f"私有案件材料\n唯一识别码：{private_token}\n"
            "本案系民间借贷纠纷，借款本金为人民币80000元，约定月利率1%。\n"
        ),
        case_subject="私有案件",
        case_notes="private e2e",
    ).json()["data"]
    private_file_id = private_upload["id"]
    ensure(private_token in download_file(owner_session, owner_token, private_file_id).decode("utf-8"), "download content mismatch")

    updated_private = update_file(
        owner_session,
        owner_token,
        private_file_id,
        {"case_title": f"更新后的私有案件 {suffix}", "case_summary": f"摘要 {private_token}"},
    )
    ensure(updated_private["case_title"] == f"更新后的私有案件 {suffix}", "file title update failed")
    searched_files = list_files(owner_session, owner_token, search=private_token)
    ensure(any(item["id"] == private_file_id for item in searched_files), "file search did not return updated private file")

    duplicate_response = upload_text_file(
        owner_session,
        owner_token,
        private_filename,
        f"重复文件内容 {suffix}",
        expected_status=400,
    ).json()
    ensure(duplicate_response.get("success") is False, "duplicate file upload should fail")
    log_step("single upload, download, edit, search, duplicate guard ok")

    private_knowledge_state = upload_knowledge(owner_session, owner_token, private_file_id, ["private"])
    ensure(private_knowledge_state["private_knowledge_uploaded"] is True, "private upload flag missing")

    owner_private_answer = ask_in_new_conversation(
        owner_session,
        owner_token,
        "owner private visibility",
        f"请回答唯一识别码 {private_token} 是什么？",
        mode="private_knowledge",
    )
    ensure(owner_private_answer["sources"], "owner private knowledge should have sources")

    viewer_private_answer = ask_in_new_conversation(
        viewer_session,
        viewer_token,
        "viewer private isolation",
        f"请回答唯一识别码 {private_token} 是什么？",
        mode="private_knowledge",
    )
    ensure(not viewer_private_answer["sources"], "viewer should not see another user's private knowledge")
    log_step("private knowledge isolation ok")

    history_conversation_id = create_conversation(owner_session, owner_token, "history regression")
    ask_question(
        owner_session,
        owner_token,
        f"重复确认私有识别码 {private_token} 是什么？",
        mode="private_knowledge",
        conversation_id=history_conversation_id,
    )
    ask_question(
        owner_session,
        owner_token,
        f"这个案件中的识别码 {private_token} 再确认一次。",
        mode="private_knowledge",
        conversation_id=history_conversation_id,
    )
    history_messages = get_messages(owner_session, owner_token, history_conversation_id)
    ensure(len(history_messages["messages"]) >= 5, "conversation history was not persisted")

    rename_denied = rename_conversation(
        viewer_session,
        viewer_token,
        history_conversation_id,
        "should not work",
        expected_status=404,
    ).json()
    ensure(rename_denied.get("success") is False, "cross-user rename should fail")
    context_denied = get_context(
        viewer_session,
        viewer_token,
        history_conversation_id,
        expected_status=404,
    ).json()
    ensure(context_denied.get("success") is False, "cross-user context should fail")
    delete_denied = delete_conversation(
        viewer_session,
        viewer_token,
        history_conversation_id,
        expected_status=404,
    ).json()
    ensure(delete_denied.get("success") is False, "cross-user delete should fail")
    log_step("conversation auth and persistence ok")

    pub_priv_file_id = upload_text_file(
        owner_session,
        owner_token,
        f"public_then_private_{suffix}.txt",
        f"公转私案例\n唯一标识：{pub_priv_token}\n该材料先进入公有知识库，再进入私有知识库。\n",
        case_subject="公转私",
        case_notes="public then private",
    ).json()["data"]["id"]
    priv_pub_file_id = upload_text_file(
        owner_session,
        owner_token,
        f"private_then_public_{suffix}.txt",
        f"私转公案例\n唯一标识：{priv_pub_token}\n该材料先进入私有知识库，再进入公有知识库。\n",
        case_subject="私转公",
        case_notes="private then public",
    ).json()["data"]["id"]

    batch_public_upload = batch_upload_text_files(
        owner_session,
        owner_token,
        [
            {
                "filename": f"batch_public_1_{suffix}.txt",
                "content": f"批量公有材料一\n唯一标识：{batch_public_token}-1\n",
            },
            {
                "filename": f"batch_public_2_{suffix}.txt",
                "content": f"批量公有材料二\n唯一标识：{batch_public_token}-2\n",
            },
        ],
        case_subject="批量公有",
        case_notes="batch public",
    )
    ensure(batch_public_upload["success_count"] == 2, f"unexpected batch public upload result: {batch_public_upload}")
    batch_public_ids = extract_file_ids(batch_public_upload)

    delete_batch_upload = batch_upload_text_files(
        owner_session,
        owner_token,
        [
            {
                "filename": f"batch_delete_1_{suffix}.txt",
                "content": f"批量删除材料一\n唯一标识：{delete_token}-1\n",
            },
            {
                "filename": f"batch_delete_2_{suffix}.txt",
                "content": f"批量删除材料二\n唯一标识：{delete_token}-2\n",
            },
        ],
        case_subject="批量删除",
        case_notes="batch delete",
    )
    ensure(delete_batch_upload["success_count"] == 2, f"unexpected delete batch upload result: {delete_batch_upload}")
    delete_batch_ids = extract_file_ids(delete_batch_upload)
    log_step("batch file submission ok")

    batch_public_result = batch_upload_knowledge(owner_session, owner_token, batch_public_ids, ["public"])
    ensure(batch_public_result["success_count"] == 2, f"batch public knowledge upload failed: {batch_public_result}")
    shared_batch_answer = ask_in_new_conversation(
        viewer_session,
        viewer_token,
        "shared batch knowledge",
        f"请回答唯一标识 {batch_public_token}-1 是什么？",
        mode="shared_knowledge",
    )
    ensure(shared_batch_answer["sources"], "shared batch knowledge should have sources")

    progress_private_result = batch_upload_knowledge_progress(owner_session, owner_token, delete_batch_ids, ["private"])
    ensure(progress_private_result["success_count"] == 2, f"progress private upload failed: {progress_private_result}")
    delete_batch_answer = ask_in_new_conversation(
        owner_session,
        owner_token,
        "batch private knowledge",
        f"请回答唯一标识 {delete_token}-1 是什么？",
        mode="private_knowledge",
    )
    ensure(delete_batch_answer["sources"], "progress private knowledge should have sources")
    log_step("batch knowledge upload and progress ok")

    state_after_public = upload_knowledge(owner_session, owner_token, pub_priv_file_id, ["public"])
    ensure(state_after_public["public_knowledge_uploaded"] is True, "public flag should be set")
    viewer_pub_priv_public = ask_in_new_conversation(
        viewer_session,
        viewer_token,
        "public then private shared",
        f"请回答唯一标识 {pub_priv_token} 是什么？",
        mode="shared_knowledge",
    )
    ensure(viewer_pub_priv_public["sources"], "public knowledge should be visible to viewer")

    state_after_private = upload_knowledge(owner_session, owner_token, pub_priv_file_id, ["private"])
    ensure(
        state_after_private["public_knowledge_uploaded"] is True and state_after_private["private_knowledge_uploaded"] is True,
        "public->private dual flags missing",
    )
    owner_pub_priv_private = ask_in_new_conversation(
        owner_session,
        owner_token,
        "public then private private",
        f"请回答唯一标识 {pub_priv_token} 是什么？",
        mode="private_knowledge",
    )
    ensure(owner_pub_priv_private["sources"], "owner should see public->private file in private mode")

    cancel_knowledge(owner_session, owner_token, pub_priv_file_id, ["public"])
    viewer_pub_priv_after_cancel = ask_in_new_conversation(
        viewer_session,
        viewer_token,
        "public cancel check",
        f"请回答唯一标识 {pub_priv_token} 是什么？",
        mode="shared_knowledge",
    )
    ensure(not viewer_pub_priv_after_cancel["sources"], "public cancel should hide shared visibility")
    owner_pub_priv_after_cancel = ask_in_new_conversation(
        owner_session,
        owner_token,
        "private remains after public cancel",
        f"请回答唯一标识 {pub_priv_token} 是什么？",
        mode="private_knowledge",
    )
    ensure(owner_pub_priv_after_cancel["sources"], "private knowledge should remain after public cancel")

    priv_pub_private_state = upload_knowledge(owner_session, owner_token, priv_pub_file_id, ["private"])
    ensure(priv_pub_private_state["private_knowledge_uploaded"] is True, "private flag should be set")
    owner_priv_pub_private = ask_in_new_conversation(
        owner_session,
        owner_token,
        "private then public private",
        f"请回答唯一标识 {priv_pub_token} 是什么？",
        mode="private_knowledge",
    )
    ensure(owner_priv_pub_private["sources"], "owner should see private->public file in private mode")

    priv_pub_public_state = upload_knowledge(owner_session, owner_token, priv_pub_file_id, ["public"])
    ensure(
        priv_pub_public_state["public_knowledge_uploaded"] is True and priv_pub_public_state["private_knowledge_uploaded"] is True,
        "private->public dual flags missing",
    )
    viewer_priv_pub_public = ask_in_new_conversation(
        viewer_session,
        viewer_token,
        "private then public shared",
        f"请回答唯一标识 {priv_pub_token} 是什么？",
        mode="shared_knowledge",
    )
    ensure(viewer_priv_pub_public["sources"], "viewer should see private->public file in shared mode")

    cancel_knowledge(owner_session, owner_token, priv_pub_file_id, ["private"])
    owner_priv_pub_after_cancel = ask_in_new_conversation(
        owner_session,
        owner_token,
        "private cancel check",
        f"请回答唯一标识 {priv_pub_token} 是什么？",
        mode="private_knowledge",
    )
    ensure(not owner_priv_pub_after_cancel["sources"], "private cancel should hide private visibility")
    viewer_priv_pub_after_cancel = ask_in_new_conversation(
        viewer_session,
        viewer_token,
        "public remains after private cancel",
        f"请回答唯一标识 {priv_pub_token} 是什么？",
        mode="shared_knowledge",
    )
    ensure(viewer_priv_pub_after_cancel["sources"], "public knowledge should remain after private cancel")
    log_step("public/private switching and cancel flow ok")

    for file_id in delete_batch_ids:
        delete_file(owner_session, owner_token, file_id)
    remaining_ids = {item["id"] for item in list_files(owner_session, owner_token)}
    ensure(not any(file_id in remaining_ids for file_id in delete_batch_ids), "batch delete loop did not remove all files")
    deleted_answer = ask_in_new_conversation(
        owner_session,
        owner_token,
        "deleted knowledge check",
        f"请回答唯一标识 {delete_token}-1 是什么？",
        mode="private_knowledge",
    )
    ensure(not deleted_answer["sources"], "deleted file should not remain in knowledge search")
    log_step("batch delete and knowledge cleanup ok")

    web_search_answer = ask_in_new_conversation(
        owner_session,
        owner_token,
        "web search check",
        "借款合同违约金在民法典框架下通常如何约定？",
        mode="none_knowledge",
        web_search="use",
    )
    ensure(web_search_answer["answer"], "web search answer should not be empty")
    ensure(web_search_answer.get("web_search_used") is True, "web search flag should be true")
    ensure(
        any(item.get("source_type") == "web" for item in web_search_answer["sources"]),
        f"web search should return web sources: {web_search_answer}",
    )
    log_step("web search ok")

    delete_conversation(owner_session, owner_token, history_conversation_id, expected_status=200)
    deleted_conversation_check = request(
        owner_session,
        "GET",
        f"/api/conversations/{history_conversation_id}/messages",
        expected_status=404,
        headers=auth_headers(owner_token),
    ).json()
    ensure(deleted_conversation_check.get("success") is False, "deleted conversation should not be accessible")

    log_step("all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
