# 방법 B 설치 — GitHub Actions (컴퓨터 꺼도 됨)

클라우드에서 자동 실행됩니다. **토큰/요금 안 듦.** Private 저장소 + 10분 간격이면 완전 무료.

로컬 폴더는 이미 git 커밋까지 끝나 있습니다. 아래만 하면 됩니다.

---

## 1. GitHub 계정

없으면 https://github.com/signup 에서 가입 (무료).

## 2. 빈 저장소 만들기

https://github.com/new

- Repository name: `camp-alert` (아무거나)
- **Private** 선택
- **"Add a README" / .gitignore / license 는 전부 체크 해제** (반드시 빈 저장소로)
- **Create repository**

## 3. 파일 올리기 (git push)

윈도우에서 **명령 프롬프트(cmd)** 를 열고 (`<내아이디>` 를 본인 것으로):

```
cd /d "%USERPROFILE%\camp-alert"
git remote add origin https://github.com/<내아이디>/camp-alert.git
git branch -M main
git push -u origin main
```

- 로그인 창이 뜨면 GitHub 계정으로 로그인 (브라우저 인증).
- `git: command not found` 이면: https://git-scm.com/download/win 설치 후 다시.

## 4. 토픽을 Secret 으로 등록

저장소 페이지 → **Settings** → 왼쪽 **Secrets and variables** → **Actions** → **New repository secret**

- Name: `NTFY_TOPIC`
- Secret: 본인 토픽 (예: `saengnim-camp-h7yq2m8x`)
- **Add secret**

> Private 저장소라면 `camp_check.py` 안에 토픽을 직접 적어도 되지만, Secret 방식이 더 안전합니다.
> `camp_check.py` 는 지금 상태(placeholder) 그대로 두세요.

## 5. Actions 켜고 테스트

저장소 상단 **Actions** 탭 →
- "I understand my workflows, go ahead and enable them" 나오면 클릭
- 왼쪽에서 **"생림오토캠핑장 빈자리 감시"** 선택 → 오른쪽 **Run workflow** → **Run workflow**
- 30초쯤 뒤 실행 결과가 초록 체크면 성공. 로그를 열어 "빈자리 없음" 이 보이면 정상.

## 6. 폰에서 알림 받기

폰 **ntfy 앱** → **+** → 4번의 토픽 이름 입력 → 구독.
하루 1번 "감시 작동 중" 알림이 오고, 빈자리가 생기면 예약 링크와 함께 알림이 옵니다.

---

## 참고

- 기본 10분 간격입니다. 5분으로 하려면 `.github/workflows/camp-check.yml` 의
  `*/10` 을 `*/5` 로 바꿔 커밋 (Public 저장소면 무료, Private이면 월 2,000분 살짝 초과).
- 저장소에 **60일간 아무 활동이 없으면** 예약 실행이 자동 중지됩니다. 가끔 Actions 탭에서
  Run workflow 한 번 눌러주거나 커밋하면 유지됩니다.
- 날짜를 바꾸려면 `camp_check.py` 의 `TARGETS` 를 수정하고 다시 `git push`.
- 방법 A(내 PC)와 동시에 돌려도 됩니다. 중복 알림은 걸러집니다.
