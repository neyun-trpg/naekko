"""
코코포리아(CCFOLIA) 방을 확인해서 새 채팅이 올라오면 ntfy로 모바일 알림을 보내는 스크립트.

- 코코포리아의 공개 Firebase 설정(API 키, 프로젝트 ID)을 이용해 '익명 로그인'으로 접속합니다.
  (개인 구글 계정 정보는 전혀 사용하지 않습니다.)
- 방의 채팅(messages 컬렉션)을 최신순으로 조회해서, 마지막으로 확인한 시점 이후의
  새 메시지가 있으면 ntfy 알림을 보냅니다.
- 마지막으로 확인한 위치는 state.json 파일에 저장합니다. (GitHub Actions에서는
  워크플로우가 이 파일을 커밋해서 다음 실행 때 이어서 사용합니다.)
"""

import json
import os
import sys
from pathlib import Path

import requests

# 코코포리아 웹앱에 공개적으로 내장되어 있는 값입니다. (비밀 키가 아니라 클라이언트 공개 설정값)
FIREBASE_API_KEY = "AIzaSyAMlcPs4ekVSBdzpRdEloqQ8lIgP9lEnRI"
FIREBASE_PROJECT_ID = "ccfolia-160aa"

ROOM_ID = os.environ.get("CCFOLIA_ROOM_ID", "").strip()
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "").strip()
NTFY_SERVER = os.environ.get("NTFY_SERVER", "https://ntfy.sh").rstrip("/")

STATE_FILE = Path(__file__).parent / "state.json"

FETCH_LIMIT = 20  # 한 번에 확인할 최근 메시지 개수 (폴링 간격 사이에 여러 개가 쌓여도 놓치지 않도록)
MAX_NOTIFY = 5  # 한 번에 개별 알림을 보낼 최대 개수 (그 이상이면 요약 알림)


def fail(msg: str) -> None:
    print(f"오류: {msg}", file=sys.stderr)
    sys.exit(1)


def get_anonymous_id_token() -> str:
    resp = requests.post(
        f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_API_KEY}",
        json={"returnSecureToken": True},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["idToken"]


def fetch_recent_messages(id_token: str, limit: int = FETCH_LIMIT):
    url = (
        f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}"
        f"/databases/(default)/documents/rooms/{ROOM_ID}:runQuery"
    )
    body = {
        "structuredQuery": {
            "from": [{"collectionId": "messages"}],
            "orderBy": [{"field": {"fieldPath": "createdAt"}, "direction": "DESCENDING"}],
            "limit": limit,
        }
    }
    resp = requests.post(
        url,
        json=body,
        headers={"Authorization": f"Bearer {id_token}"},
        timeout=15,
    )
    if resp.status_code == 403:
        fail(
            "방에 접근할 권한이 없습니다. CCFOLIA_ROOM_ID가 올바른지, "
            "방이 비공개 설정은 아닌지 확인해주세요."
        )
    resp.raise_for_status()

    messages = []
    for item in resp.json():
        doc = item.get("document")
        if not doc:
            continue
        fields = doc["fields"]

        def field(name, key="stringValue", default=""):
            return fields.get(name, {}).get(key, default)

        messages.append(
            {
                "doc_id": doc["name"].split("/")[-1],
                "name": field("name") or "(이름없음)",
                "text": field("text"),
                "msg_type": field("type") or "text",
                "created_at": fields.get("createdAt", {}).get("timestampValue", ""),
            }
        )
    # created_at 오름차순(오래된 것 -> 최신)으로 정렬해서 반환
    messages.sort(key=lambda m: m["created_at"])
    return messages


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"last_created_at": None, "last_doc_id": None}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def message_preview(msg: dict) -> str:
    if msg["msg_type"] == "text" and msg["text"]:
        body = msg["text"]
    elif msg["msg_type"] == "roll" and msg["text"]:
        body = f"🎲 {msg['text']}"
    else:
        body = f"[{msg['msg_type']}] 새 메시지"
    return body.strip().replace("\n", " ")[:200]


def send_ntfy(title: str, message: str) -> None:
    resp = requests.post(
        f"{NTFY_SERVER}/{NTFY_TOPIC}",
        data=message.encode("utf-8"),
        headers={
            "Title": title.encode("utf-8"),
            "Priority": "default",
        },
        timeout=15,
    )
    resp.raise_for_status()


def main() -> None:
    if not ROOM_ID:
        fail("CCFOLIA_ROOM_ID 환경변수가 설정되지 않았습니다.")
    if not NTFY_TOPIC:
        fail("NTFY_TOPIC 환경변수가 설정되지 않았습니다.")

    state = load_state()
    id_token = get_anonymous_id_token()
    messages = fetch_recent_messages(id_token)

    if not messages:
        print("방에 메시지가 없습니다.")
        return

    last_created_at = state.get("last_created_at")

    if last_created_at is None:
        # 최초 실행: 알림을 보내지 않고 현재 시점을 기준점으로만 저장
        latest = messages[-1]
        state["last_created_at"] = latest["created_at"]
        state["last_doc_id"] = latest["doc_id"]
        save_state(state)
        print("최초 실행이라 기준점만 저장했습니다. 다음 실행부터 새 메시지를 감지합니다.")
        return

    new_messages = [m for m in messages if m["created_at"] > last_created_at]

    if not new_messages:
        print("새 메시지가 없습니다.")
        return

    if len(new_messages) <= MAX_NOTIFY:
        for msg in new_messages:
            send_ntfy(f"코코포리아 · {msg['name']}", message_preview(msg))
    else:
        names = ", ".join(sorted({m["name"] for m in new_messages}))
        send_ntfy(
            "코코포리아 · 새 메시지 다수",
            f"{names} 등 {len(new_messages)}개의 새 메시지가 있습니다.",
        )

    latest = new_messages[-1]
    state["last_created_at"] = latest["created_at"]
    state["last_doc_id"] = latest["doc_id"]
    save_state(state)
    print(f"{len(new_messages)}개의 새 메시지에 대해 알림을 보냈습니다.")


if __name__ == "__main__":
    main()
