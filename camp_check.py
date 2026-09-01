#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
생림오토캠핑장(김해) 빈자리 감시 스크립트
------------------------------------------------
camp.xticket.kr 예약 사이트의 내부 JSON API를 조회해서, 지정한 날짜/숙박일에
예약 가능한 사이트가 생기면 휴대폰으로 알림(ntfy.sh)을 보냅니다.
5분마다 이 스크립트를 실행하도록 스케줄러에 등록해서 씁니다.

사용법:
  python camp_check.py            # 1회 체크 (스케줄러가 5분마다 이걸 호출)
  python camp_check.py --status   # 현재 상태만 출력, 알림/상태저장 안 함
  python camp_check.py --test     # 테스트 알림 1개 발송 (폰 연결 확인용)

의존성 없음(파이썬 표준 라이브러리만). 파이썬 3.8+
"""

import argparse
import calendar
import datetime as dt
import json
import os
import sys
import time
import urllib.parse
import urllib.request
import http.cookiejar

# ================== 설정 (여기만 고치면 됩니다) ==================

# 폰 알림용 ntfy.sh 토픽. 아무도 못 맞출 고유한 문자열로 바꾸세요.
# 폰에 ntfy 앱(무료) 설치 -> 이 토픽을 구독(subscribe) 하면 알림이 옵니다.
# 환경변수 NTFY_TOPIC 가 있으면 그 값을 우선 사용합니다(깃허브 액션용).
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "saengnim-camp-CHANGE-ME-9f3a7")

# 감시 목록: 체크인 날짜(YYYYMMDD) + 숙박일수(박). 필요하면 자유롭게 추가/수정.
TARGETS = [
    {"checkin": "20261002", "nights": 2},   # 10/2(금) 2박3일  -> 10/2, 10/3 숙박
    {"checkin": "20261016", "nights": 2},   # 10/16(금) 2박3일
    {"checkin": "20261023", "nights": 2},   # 10/23(금) 2박3일
    {"checkin": "20261030", "nights": 2},   # 10/30(금) 2박3일
]

# 감시할 시설 구역. "아무자리나" 이므로 3구역 전부.
FACILITIES = [
    ("0001", "잔디사이트"),
    ("0002", "데크사이트"),
    ("0004", "파쇄석사이트"),
]

# 같은 빈자리에 대해 재알림하기까지 최소 간격(분). 가능 상태가 유지되면 이 간격마다 리마인드.
RENOTIFY_MINUTES = 60

# 하루 1번 "감시 정상 작동 / 아직 빈자리 없음" 조용한 알림. 0 이면 끔.
HEARTBEAT_HOURS = 24

# ================== 사이트 고정값 (건드릴 필요 없음) ==================
SHOP_ENCODE = "f5f32b56abe23f9aec682e337c7ee65772a4438ff09b56823d4c7d2a7528d940"
SHOP_CODE = "622830018001"
BASE = "https://camp.xticket.kr"
MAIN_URL = BASE + "/web/main?shopEncode=" + SHOP_ENCODE
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
HERE = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(HERE, "camp_state.json")
LOG_FILE = os.path.join(HERE, "camp_check.log")
API_HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "*/*",
    "Referer": MAIN_URL,
    "Origin": BASE,
    "User-Agent": UA,
}
# ====================================================================


def log(*a):
    line = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S ") + " ".join(str(x) for x in a)
    try:
        print(line, flush=True)
    except Exception:
        pass
    try:
        if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > 1_000_000:
            os.replace(LOG_FILE, LOG_FILE + ".1")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(s):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False, indent=1)
    except Exception as e:
        log("상태 저장 실패:", e)


def new_session():
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.addheaders = [
        ("User-Agent", UA),
        ("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"),
        ("Accept-Language", "ko-KR,ko;q=0.9,en;q=0.8"),
    ]
    # 리다이렉트(main -> Reservation -> main)를 따라가며 세션 쿠키 획득
    op.open(MAIN_URL, timeout=25).read()
    # 세션에 상점 컨텍스트 등록
    api(op, "/Web/Book/GetShopInformation.json", {"shopEncode": SHOP_ENCODE})
    return op


def api(op, path, params):
    body = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(BASE + path, data=body, method="POST")
    for k, v in API_HEADERS.items():
        req.add_header(k, v)
    raw = op.open(req, timeout=25).read().decode("utf-8")
    j = json.loads(raw)
    if isinstance(j, dict) and j.get("error"):
        raise RuntimeError("API error: %s" % j.get("error"))
    return j


def month_bounds(yyyymm):
    y, m = int(yyyymm[:4]), int(yyyymm[4:6])
    last = calendar.monthrange(y, m)[1]
    return "%s01" % yyyymm, "%s%02d" % (yyyymm, last)


def nights_of(checkin, nights):
    d0 = dt.datetime.strptime(checkin, "%Y%m%d")
    return [(d0 + dt.timedelta(days=i)).strftime("%Y%m%d") for i in range(nights)]


def last_night(checkin, nights):
    d0 = dt.datetime.strptime(checkin, "%Y%m%d")
    return (d0 + dt.timedelta(days=nights - 1)).strftime("%Y%m%d")


def fmt(ymd):
    return "%d/%d" % (int(ymd[4:6]), int(ymd[6:8]))


def get_month_remain(op, yyyymm):
    """해당 월 날짜별 잔여 수(사이트 전체 합산). {'20261003': 0, ...}"""
    sd, ed = month_bounds(yyyymm)
    # PlayDate 조회 전 반드시 ProductGroup 을 먼저 호출해야 세션이 열림
    api(op, "/Web/Book/GetBookProductGroup.json",
        {"start_date": sd, "end_date": ed, "shopCode": SHOP_CODE})
    j = api(op, "/Web/Book/GetBookPlayDate.json",
            {"play_month": yyyymm, "shopCode": SHOP_CODE})
    out = {}
    for d in j.get("data", {}).get("bookPlayDateList", []):
        out[d["play_date"]] = d.get("book_remain_count", 0)
    return out


def get_available_sites(op, fac_code, checkin, nights):
    """해당 구역에서 체크인~마지막밤 동안 '같은 사이트'가 통째로 비어있는 것들의 이름."""
    j = api(op, "/Web/Book/GetBookProduct010001.json", {
        "product_group_code": fac_code,
        "start_date": checkin,
        "end_date": last_night(checkin, nights),
        "book_days": nights,
        "two_stay_days": 0,
        "shopCode": SHOP_CODE,
    })
    lst = j.get("data", {}).get("bookProductList", [])
    return [p.get("product_name", "?") for p in lst if p.get("select_yn") == "1"]


def ntfy(title, message, priority=3, tags=None):
    if not NTFY_TOPIC or "CHANGE-ME" in NTFY_TOPIC:
        log("!! NTFY_TOPIC 미설정 - 알림을 보내지 않습니다.")
        log("   (알림내용)", title, "|", message.replace("\n", " "))
        return
    payload = {"topic": NTFY_TOPIC, "title": title,
               "message": message, "priority": priority}
    if tags:
        payload["tags"] = tags
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request("https://ntfy.sh/", data=data,
                                 headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=20).read()
        log("알림 발송:", title)
    except Exception as e:
        log("알림 발송 실패:", e)


def run_check(status_only=False):
    state = load_state()
    now = time.time()
    try:
        op = new_session()
    except Exception as e:
        log("사이트 접속 실패:", e)
        return 2

    months = sorted({t["checkin"][:6] for t in TARGETS})
    remain_by_month = {}
    for m in months:
        try:
            remain_by_month[m] = get_month_remain(op, m)
        except Exception as e:
            log("월별 잔여 조회 실패(%s): %s" % (m, e))
            remain_by_month[m] = {}

    any_available = False
    status_lines = []

    for t in TARGETS:
        checkin, nights = t["checkin"], t["nights"]
        label = "%s 체크인 %d박%d일" % (fmt(checkin), nights, nights + 1)
        remain = remain_by_month.get(checkin[:6], {})
        need = nights_of(checkin, nights)
        blocked = [n for n in need if remain.get(n, 0) <= 0]

        if blocked:
            status_lines.append("· %s → 불가 (마감: %s)"
                                % (label, ", ".join(fmt(n) for n in blocked)))
            for fc, _ in FACILITIES:
                state.pop("%s|%s|%s" % (checkin, nights, fc), None)
            continue

        # 필요한 밤이 전부 여유 있음 → 구역별 상세 확인
        for fc, fname in FACILITIES:
            key = "%s|%s|%s" % (checkin, nights, fc)
            try:
                sites = get_available_sites(op, fc, checkin, nights)
            except Exception as e:
                log("상세 조회 실패 (%s %s): %s" % (label, fname, e))
                continue

            if sites:
                any_available = True
                status_lines.append("· %s / %s → 예약가능 %d곳: %s"
                                    % (label, fname, len(sites), ", ".join(sites[:15])))
                if not status_only:
                    prev = state.get(key, {})
                    last_notified = prev.get("last_notified", 0)
                    is_new = prev.get("count", 0) == 0
                    stale = (now - last_notified) > RENOTIFY_MINUTES * 60
                    if is_new or stale:
                        ntfy("🏕️ 생림오토캠핑장 빈자리! %s" % label,
                             "%s 에 예약 가능한 자리가 생겼습니다.\n"
                             "예약가능 %d곳: %s\n\n예약: %s"
                             % (fname, len(sites), ", ".join(sites[:15]), MAIN_URL),
                             priority=5, tags=["tent", "rotating_light"])
                        last_notified = now
                    state[key] = {"count": len(sites), "last_notified": last_notified}
            else:
                status_lines.append("· %s / %s → 통째로 비는 자리 없음" % (label, fname))
                state.pop(key, None)

    if not status_only and HEARTBEAT_HOURS > 0 and not any_available:
        if (now - state.get("_heartbeat", 0)) > HEARTBEAT_HOURS * 3600:
            ntfy("생림 캠핑 감시 작동 중",
                 "아직 빈자리 없음. 계속 감시합니다.\n확인시각: "
                 + dt.datetime.now().strftime("%m/%d %H:%M"),
                 priority=1, tags=["hourglass_flowing_sand"])
            state["_heartbeat"] = now

    state["_last_run"] = now
    if not status_only:
        save_state(state)

    log("확인 완료 -", "빈자리 있음!" if any_available else "빈자리 없음.")
    for ln in status_lines:
        log("  " + ln)
    return 1 if any_available else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true", help="현재 상태만 출력(알림/저장 없음)")
    ap.add_argument("--test", action="store_true", help="테스트 알림 발송")
    args = ap.parse_args()
    if args.test:
        ntfy("테스트 알림", "생림 캠핑 감시가 폰과 정상 연결되었습니다. ✅",
             priority=4, tags=["white_check_mark"])
        return 0
    return run_check(status_only=args.status)


if __name__ == "__main__":
    sys.exit(main())
