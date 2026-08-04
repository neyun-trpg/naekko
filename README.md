# 코코포리아 PBP 모바일 알림

코코포리아(CCFOLIA) 방에 새 채팅이 올라오면 휴대폰으로 알림을 보내주는 자동화 도구입니다.
GitHub Actions가 5분마다 방을 확인하고, 새 메시지가 있으면 [ntfy](https://ntfy.sh)를 통해
휴대폰 알림을 보냅니다. 상시 켜져있는 서버나 PC가 없어도 동작합니다.

## 준비물

- GitHub 계정 (무료)
- 휴대폰에 **ntfy** 앱 설치
  - Android: Google Play스토어에서 "ntfy" 검색
  - iOS: 앱스토어에서 "ntfy" 검색

## 설정 방법

### 1. GitHub 저장소 만들기

초록색 "Use this template" 버튼 클릭 → "Create a new repository"


```
ccfolia_watch.py
requirements.txt
.github/workflows/ccfolia-watch.yml
```

### 2. 알림 받을 "토픽" 이름 정하기

ntfy는 회원가입 없이, 정한 "토픽 이름"으로 알림을 주고받는 방식입니다.
**토픽 이름을 아는 사람은 누구나 그 알림을 구독할 수 있으므로**,
`my-ccfolia-alert-9f3k2` 처럼 남이 추측하기 어려운 이름으로 정해주세요.

### 3. GitHub 저장소에 값 등록

저장소의 **Settings → Secrets and variables → Actions**로 이동합니다.

- **Variables** 탭 → New repository variable
  - Name: `CCFOLIA_ROOM_ID`
  - Value: 방 링크의 마지막 부분 (예: `https://ccfolia.com/rooms/lQa2HtGdF` → `lQa2HtGdF`)
- **Secrets** 탭 → New repository secret
  - Name: `NTFY_TOPIC`
  - Value: 2번에서 정한 토픽 이름

### 4. 휴대폰 ntfy 앱에서 구독

ntfy 앱을 열고 **+** 버튼 → "Subscribe to topic" → 2번에서 정한 토픽 이름 입력.

### 5. 첫 실행 (기준점 만들기)

저장소의 **Actions** 탭 → "CCFOLIA 새 채팅 알림" 워크플로우 선택 → **Run workflow** 클릭.

> 처음 실행할 때는 "지금까지의 메시지"를 기준점으로만 저장하고 알림은 보내지 않습니다.
> 이후 실행부터 새로 올라오는 메시지에 대해서만 알림이 옵니다.

이후로는 5분마다 자동으로 실행되며, 새 채팅이 있을 때만 휴대폰에 알림이 옵니다.

## 참고 / 한계

- GitHub Actions의 스케줄 실행은 정확히 5분 간격이 보장되지 않고, 상황에 따라 몇 분 정도
  지연될 수 있습니다. (완전 실시간은 아닙니다.)
- 무료 GitHub 계정 기준 매월 제공되는 Actions 실행 시간 한도 내에서 동작합니다. 이 스크립트는
  1회 실행에 몇 초 정도만 걸리므로, 5분 간격으로 돌려도 무료 한도 안에서 충분히 여유가 있습니다.
- ntfy 무료 서버(ntfy.sh)는 공개 서버이므로, 토픽 이름이 노출되지 않게 주의해주세요.
  더 안전하게 쓰고 싶다면 ntfy를 직접 호스팅하거나 유료 개인 토픽 기능을 사용할 수 있습니다.
- 이 스크립트는 코코포리아 앱에 공개적으로 내장된 설정값(Firebase API 키)을 사용해
  "익명 로그인" 방식으로 채팅을 읽습니다. 개인 계정 로그인 정보는 전혀 필요하지 않습니다.
