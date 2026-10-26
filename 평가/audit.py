"""랜딩페이지 해상도별 점검 + 스크린샷

사용법: python audit.py <라운드이름>
결과: 평가/<라운드>/ 아래에 해상도별 첫 화면·전체 화면 캡처, 한 장짜리 비교 이미지(contact.png), metrics.json
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
PAGE = (ROOT.parent / "index.html").as_uri() + "?utm_source=audit"

VIEWPORTS = [
    # (이름, 폭, 높이, 모바일 여부)
    ("폴드 커버 280", 280, 653, True),
    ("폴드5 커버 344", 344, 882, True),
    ("갤럭시 360", 360, 780, True),
    ("아이폰 390", 390, 844, True),
    ("폴드 펼침 673", 673, 841, True),
    ("태블릿 768", 768, 1024, True),
    ("노트북 1280", 1280, 720, False),
    ("데스크톱 1920", 1920, 1080, False),
]

CHECK_JS = r"""
() => {
  const vw = innerWidth, vh = innerHeight;
  const vis = el => { const r = el.getBoundingClientRect(); const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none' && +s.opacity > 0.05; };
  // 가로 넘침
  const overflowX = document.documentElement.scrollWidth > vw + 1;
  // 화면 밖으로 삐져나간 요소
  const offenders = [];
  document.querySelectorAll('body *').forEach(el => {
    const r = el.getBoundingClientRect();
    if (!vis(el) || el.closest('[aria-hidden="true"]')) return;
    if (r.right > vw + 1 || r.left < -1) offenders.push(el.tagName.toLowerCase() + '.' + [...el.classList].join('.') + ` (${Math.round(r.left)}~${Math.round(r.right)})`);
  });
  // 글자 잘림 (자기 영역보다 내용이 넓음)
  const clipped = [];
  document.querySelectorAll('h1,h2,h3,p,a,span,button,summary').forEach(el => {
    if (!vis(el) || el.closest('[aria-hidden="true"]')) return;
    if (el.scrollWidth > el.clientWidth + 2 && getComputedStyle(el).overflow !== 'visible') clipped.push(el.textContent.trim().slice(0, 30));
  });
  // CTA: 첫 화면(헤더 제외)에 본문 가입 버튼이 완전히 보이는지
  const ctas = [...document.querySelectorAll('.js-signup')].filter(el => !el.closest('header') && !el.closest('.sticky-cta'));
  const heroCta = ctas[0];
  let heroCtaBottom = null, heroCtaInFold = false;
  if (heroCta) { const r = heroCta.getBoundingClientRect(); heroCtaBottom = Math.round(r.bottom); heroCtaInFold = r.bottom <= vh && vis(heroCta); }
  // 터치 영역 44px 미만인 링크/버튼
  const smallTaps = [...document.querySelectorAll('a,button,summary')].filter(vis)
    .filter(el => { const r = el.getBoundingClientRect(); return r.height < 40 && !el.closest('footer'); })
    .map(el => el.textContent.trim().slice(0, 20) + ` (${Math.round(el.getBoundingClientRect().height)}px)`);
  // 가장 작은 본문 글자 크기
  let minFont = 99;
  document.querySelectorAll('p,li,span,a,small,h4').forEach(el => {
    if (!vis(el) || el.closest('[aria-hidden="true"]') || el.closest('footer') || !el.textContent.trim()) return;
    minFont = Math.min(minFont, parseFloat(getComputedStyle(el).fontSize));
  });
  // 혜택 문구 일관성: 각 구간에 핵심 혜택 2가지가 다 있는지
  const sections = {};
  document.querySelectorAll('[data-benefit-zone]').forEach(z => {
    const t = z.innerText;
    sections[z.dataset.benefitZone] = { 무제한: /무제한|횟수 제한 없이/.test(t), 정책: /정책/.test(t) };
  });
  const imgs = [...document.querySelectorAll('img')].map(i => ({ src: i.getAttribute('src'), alt: i.alt, loaded: i.complete && i.naturalWidth > 0 }));
  return { vw, vh, docHeight: document.documentElement.scrollHeight, overflowX, offenders: offenders.slice(0, 10),
           clipped: clipped.slice(0, 10), heroCtaInFold, heroCtaBottom, ctaCount: document.querySelectorAll('.js-signup').length,
           smallTaps: smallTaps.slice(0, 10), minFont, sections, imgs };
}
"""


def font(size):
    for f in ["C:/Windows/Fonts/malgunbd.ttf", "C:/Windows/Fonts/malgun.ttf"]:
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            pass
    return ImageFont.load_default()


def contact_sheet(shots, out, title):
    """해상도별 첫 화면을 같은 높이로 줄여 한 장에 나란히"""
    H = 560
    tiles = []
    for name, path in shots:
        im = Image.open(path).convert("RGB")
        w = round(im.width * H / im.height)
        tiles.append((name, im.resize((w, H), Image.LANCZOS)))
    pad, head = 24, 90
    W = sum(t.width for _, t in tiles) + pad * (len(tiles) + 1)
    sheet = Image.new("RGB", (W, H + head + 50), "#F3F4F6")
    d = ImageDraw.Draw(sheet)
    d.text((pad, 24), title, fill="#111827", font=font(30))
    x = pad
    for name, t in tiles:
        sheet.paste(t, (x, head))
        d.rectangle([x - 1, head - 1, x + t.width, head + H], outline="#D1D5DB")
        d.text((x, head + H + 12), name, fill="#374151", font=font(18))
        x += t.width + pad
    sheet.save(out)


def main():
    rnd = sys.argv[1]
    out = ROOT / rnd
    out.mkdir(parents=True, exist_ok=True)
    results, fold_shots = {}, []
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        for name, w, h, mobile in VIEWPORTS:
            ctx = b.new_context(viewport={"width": w, "height": h}, device_scale_factor=2 if w < 1000 else 1,
                                is_mobile=mobile, has_touch=mobile)
            pg = ctx.new_page()
            pg.goto(PAGE, wait_until="networkidle")
            pg.wait_for_timeout(500)
            slug = f"{w}x{h}"
            fold = out / f"fold_{slug}.png"
            pg.screenshot(path=str(fold))
            fold_shots.append((name, fold))
            m = pg.evaluate(CHECK_JS)
            # 전체 페이지: 끝까지 스크롤해 지연 로딩 이미지를 불러오고, 등장 애니메이션을 끝낸 상태로
            pg.evaluate("""async () => { for (let y = 0; y < document.body.scrollHeight; y += innerHeight / 2) {
                scrollTo(0, y); await new Promise(r => setTimeout(r, 80)); } scrollTo(0, 0); }""")
            pg.wait_for_load_state("networkidle")
            m["imgs"] = pg.evaluate("[...document.images].map(i => ({src: i.getAttribute('src'), alt: !!i.alt, loaded: i.complete && i.naturalWidth > 0}))")
            pg.evaluate("document.querySelectorAll('.reveal').forEach(e=>e.classList.add('in'))")
            pg.add_style_tag(content=".sticky-cta{display:none!important}")
            pg.wait_for_timeout(700)
            pg.screenshot(path=str(out / f"full_{slug}.png"), full_page=True)
            results[name] = m
            ctx.close()
        b.close()
    contact_sheet(fold_shots, out / "contact.png", f"{rnd} · 해상도별 첫 화면")
    (out / "metrics.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    for name, m in results.items():
        print(f"[{name}] 넘침={m['overflowX']} 잘림={len(m['clipped'])} 이탈요소={len(m['offenders'])} "
              f"첫화면CTA={m['heroCtaInFold']}({m['heroCtaBottom']}/{m['vh']}) 작은터치={len(m['smallTaps'])} 최소글자={m['minFont']}")
    first = next(iter(results.values()))
    print("혜택 구간:", json.dumps(first["sections"], ensure_ascii=False))
    print("이미지:", json.dumps(first["imgs"], ensure_ascii=False))
    for name, m in results.items():
        if m["offenders"] or m["clipped"] or m["smallTaps"]:
            print(f"  - {name}: 이탈 {m['offenders'][:4]} / 잘림 {m['clipped'][:4]} / 작은터치 {m['smallTaps'][:5]}")


if __name__ == "__main__":
    main()
