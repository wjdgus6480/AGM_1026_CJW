"""CTA 위치별 스크린샷 (엑셀 보고서용)

사용법: python cta_shots.py <저장폴더>
모바일(390px)에서 각 가입 버튼과 주변 문맥을 잘라 cta_<position>.png 로 저장합니다.
Amplitude 요청은 가로채서 실제 데이터에 쌓이지 않습니다.
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
PAGE = (ROOT.parent / "index.html").as_uri()
# 버튼을 감싼 영역(문맥까지 보이도록)
AREAS = {
    "header": "header .wrap",
    "hero": ".hero .cta-box",
    "benefits": "#benefits .mid-cta",
    "how": ".how .mid-cta",
    "final": ".final",
    "sticky": "#stickyCta",
}

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    pg = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
    pg.route("**/*amplitude.com/**", lambda r: r.fulfill(status=200, body="{}") if r.request.method == "POST" else r.continue_())
    pg.goto(PAGE, wait_until="networkidle")
    pg.evaluate("document.querySelectorAll('.reveal').forEach(e => e.classList.add('in'))")
    for pos, sel in AREAS.items():
        if pos == "sticky":
            pg.evaluate("scrollTo(0, document.querySelector('#benefits').offsetTop)")
            pg.wait_for_timeout(600)
        el = pg.locator(sel).first
        if pos != "sticky":
            el.scroll_into_view_if_needed()
            pg.wait_for_timeout(300)
        box = el.bounding_box()
        pad = 12
        clip = {"x": max(box["x"] - pad, 0), "y": max(box["y"] - pad, 0),
                "width": min(box["width"] + pad * 2, 390), "height": box["height"] + pad * 2}
        pg.screenshot(path=str(out / f"cta_{pos}.png"), clip=clip)
        print(pos, round(box["width"]), round(box["height"]))
    b.close()
