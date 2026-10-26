"""CTA 노출·클릭 이벤트 테스트

사용법: python cta_test.py [페이지 주소] [--send]
기본은 로컬 index.html을 열고, Amplitude로 가는 요청을 가로채 내용만 확인합니다(실제 데이터에 쌓이지 않음).
--send를 붙이면 실제로 Amplitude에 전송합니다(utm_source=claude_test).
"""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
args = [a for a in sys.argv[1:] if not a.startswith("--")]
SEND = "--send" in sys.argv
PAGE = (args[0] if args else (ROOT.parent / "index.html").as_uri()) + "?utm_source=claude_test&utm_campaign=cta_test"

MOBILE_POSITIONS = {"header", "hero", "benefits", "how", "final", "sticky"}
DESKTOP_POSITIONS = {"header", "hero", "benefits", "how", "final"}  # 하단 고정 버튼은 데스크톱에서 숨김


def run(b, label, viewport, mobile, expected, click_positions):
    ctx = b.new_context(viewport=viewport, is_mobile=mobile, has_touch=mobile)
    pg = ctx.new_page()
    events = []

    def capture(route):
        try:
            events.extend(json.loads(route.request.post_data or "{}").get("events", []))
        except ValueError:
            pass
        if SEND:
            route.continue_()
        else:
            route.fulfill(status=200, content_type="application/json", body='{"code":200}')

    pg.route("**/*amplitude.com/**", lambda r: capture(r) if r.request.method == "POST" else r.continue_())
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(PAGE, wait_until="networkidle")
    # 사람이 읽듯 천천히 끝까지 스크롤
    height = pg.evaluate("document.body.scrollHeight")
    for y in range(0, height, 300):
        pg.evaluate(f"scrollTo(0,{y})")
        pg.wait_for_timeout(80)
    # 다시 한 번 훑어도 노출이 중복 기록되지 않는지
    pg.evaluate("scrollTo(0,0)"); pg.wait_for_timeout(300)
    pg.evaluate(f"scrollTo(0,{height // 2})"); pg.wait_for_timeout(500)
    # 클릭: 실제 이동은 막고 클릭 이벤트만 발생
    pg.evaluate("document.querySelectorAll('.js-signup').forEach(a => a.addEventListener('click', e => e.preventDefault()))")
    for pos in click_positions:
        pg.evaluate(f"document.querySelector('.js-signup[data-position=\"{pos}\"]').click()")
    pg.wait_for_timeout(2500)
    ctx.close()

    views = [e["event_properties"] for e in events if e["event_type"] == "LP Signup CTA Viewed"]
    clicks = [e["event_properties"] for e in events if e["event_type"] == "LP Signup CTA Clicked"]
    view_pos = [v["position"] for v in views]
    click_pos = [c["position"] for c in clicks]
    checks = {
        "노출: 기대한 위치 모두 기록": set(view_pos) == expected,
        "노출: 위치별 1번만 기록(중복 없음)": len(view_pos) == len(set(view_pos)),
        "클릭: 누른 위치가 그대로 기록": sorted(click_pos) == sorted(click_positions),
        "버튼 문구(cta_text) 포함": all(e.get("cta_text") for e in views + clicks),
        "JS 오류 없음": not errors,
    }
    print(f"\n[{label}] 노출 {len(views)}건 · 클릭 {len(clicks)}건")
    for v in views:
        print(f"  노출  {v['position']:<9} \"{v['cta_text']}\"")
    for c in clicks:
        print(f"  클릭  {c['position']:<9} \"{c['cta_text']}\"")
    for name, ok in checks.items():
        print(f"  {'통과' if ok else '실패'}  {name}")
    if errors:
        print("  오류:", errors)
    return all(checks.values())


with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    print("페이지:", PAGE, "| 실제 전송" if SEND else "| 전송 가로채기(테스트 전용)")
    ok1 = run(b, "모바일 390x844", {"width": 390, "height": 844}, True, MOBILE_POSITIONS, ["hero", "sticky", "final"])
    ok2 = run(b, "데스크톱 1280x720", {"width": 1280, "height": 720}, False, DESKTOP_POSITIONS, ["header", "benefits"])
    b.close()
print("\n결과:", "모두 통과" if ok1 and ok2 else "실패 있음")
sys.exit(0 if ok1 and ok2 else 1)
