#!/usr/bin/env python3
"""
Build the Automotive Insight blog from _blog/posts/*.html.

    python3 _blog/build.py

Writes:
  blog/index.html               the listing page
  blog/<slug>/index.html        one page per post
and refreshes the generated blocks in:
  _worker.js                    sitemap entries  (// BLOG-SITEMAP:START ... END)
  llms.txt                      blog post list   (<!-- BLOG:START --> ... END)

No dependencies beyond the Python 3 standard library. See _blog/README.md.
"""
import html, json, re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BLOG_SRC = ROOT / "_blog"
TPL = BLOG_SRC / "templates"
DOMAIN = "https://automotiveinsight.com.au"
BUSINESS = {"@id": f"{DOMAIN}/#business"}

def t(name): return (TPL / name).read_text()
def esc(s): return html.escape(s, quote=True)
def fill(tpl, **kw):
    for k, v in kw.items():
        tpl = tpl.replace("{{" + k + "}}", str(v))
    left = re.findall(r"\{\{[A-Z_]+\}\}", tpl)
    if left: raise SystemExit(f"unfilled tokens: {sorted(set(left))}")
    return tpl
def human(d): return date.fromisoformat(d).strftime("%-d %B %Y")
def ld(obj): return '<script type="application/ld+json">\n' + json.dumps(obj, indent=2, ensure_ascii=False).replace("</", "<\\/") + "\n</script>"

# ------------------------------------------------------------------ load posts
def load(path):
    raw = path.read_text()
    m = re.match(r"\s*<!--\s*(\{.*?\})\s*-->\s*", raw, re.S)
    if not m: raise SystemExit(f"{path.name}: missing JSON front matter")
    meta = json.loads(m.group(1))
    rest = raw[m.end():]
    body, _, rest = rest.partition("<!-- FAQ -->")
    faq_html, _, sources = rest.partition("<!-- SOURCES -->")
    meta["body"] = body.strip()
    meta["faqs"] = [(re.sub(r"<[^>]+>", "", q).strip(), a.strip())
                    for q, a in re.findall(r"<h3>(.*?)</h3>\s*(<p>.*?</p>)", faq_html, re.S)]
    meta["sources"] = sources.strip()
    for k in ("slug", "title", "metaTitle", "description", "category", "tagline",
              "datePublished", "image", "imageAlt", "visitLead", "serviceLink"):
        if not meta.get(k): raise SystemExit(f"{path.name}: front matter needs '{k}'")
    if meta["slug"] != path.stem: raise SystemExit(f"{path.name}: slug must match file name")
    if date.fromisoformat(meta["datePublished"]) > date.today():
        meta["draft"] = True   # future-dated posts are held back until their date
    meta.setdefault("dateModified", meta["datePublished"])
    meta["categoryShort"] = meta["category"].split("|")[0].strip()
    meta["categoryKey"] = re.sub(r"[^a-z0-9]+", "-", meta["categoryShort"].lower()).strip("-")
    words = len(re.sub(r"<[^>]+>", " ", meta["body"]).split())
    meta["wordCount"] = words
    meta["readMins"] = max(2, round(words / 220))
    return meta

posts = [load(p) for p in sorted((BLOG_SRC / "posts").glob("*.html"))]
posts = [p for p in posts if not p.get("draft")]
posts.sort(key=lambda p: p["datePublished"], reverse=True)
by_slug = {p["slug"]: p for p in posts}
page = t("page.html")
css = t("blog.css")

def card(p, feature=False, title_tag="h3"):
    return fill(t("card.html"),
        CARD_CLASS=" blog-feature" if feature else "", SLUG=p["slug"], CATEGORY_KEY=p["categoryKey"],
        IMAGE=p["image"], IMAGE_ALT=esc(p["imageAlt"]), CATEGORY_SHORT=esc(p["categoryShort"]),
        TITLE_TAG=title_tag, TITLE=esc(p["title"]), TAGLINE=esc(p["tagline"]),
        DATE_ISO=p["datePublished"], DATE_HUMAN=human(p["datePublished"]), READ_MINS=p["readMins"])

def related_for(p):
    picks = [s for s in p.get("related", []) if s in by_slug and s != p["slug"]]
    for q in posts:  # top up with the newest posts in the same topic, then newest overall
        if len(picks) >= 3: break
        if q["slug"] not in picks and q["slug"] != p["slug"] and q["categoryKey"] == p["categoryKey"]:
            picks.append(q["slug"])
    for q in posts:
        if len(picks) >= 3: break
        if q["slug"] not in picks and q["slug"] != p["slug"]:
            picks.append(q["slug"])
    return [by_slug[s] for s in picks[:3]]

# ------------------------------------------------------------------ post pages
for p in posts:
    url = f"{DOMAIN}/blog/{p['slug']}/"
    schema = [
        {"@context": "https://schema.org", "@type": "BlogPosting",
         "headline": p["title"], "description": p["description"],
         "mainEntityOfPage": {"@type": "WebPage", "@id": url}, "url": url,
         "datePublished": p["datePublished"], "dateModified": p["dateModified"],
         "image": {"@type": "ImageObject", "url": DOMAIN + p["image"], "width": 1200, "height": 675},
         "inLanguage": "en-AU", "wordCount": p["wordCount"], "articleSection": p["categoryShort"],
         **({"keywords": p["keywords"]} if p.get("keywords") else {}),
         "isPartOf": {"@type": "Blog", "@id": f"{DOMAIN}/blog/", "name": "Automotive Insight Blog"},
         "author": BUSINESS, "publisher": BUSINESS},
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{DOMAIN}/"},
            {"@type": "ListItem", "position": 2, "name": "Blog", "item": f"{DOMAIN}/blog/"},
            {"@type": "ListItem", "position": 3, "name": p["title"], "item": url}]},
    ]
    if p["faqs"]:
        schema.append({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": html.unescape(q),
             "acceptedAnswer": {"@type": "Answer", "text": html.unescape(re.sub(r"<[^>]+>", "", a)).strip()}}
            for q, a in p["faqs"]]})

    faq_block = ""
    if p["faqs"]:
        items = "\n".join(f'        <details>\n          <summary>{q}</summary>\n          <div class="faq-a">{a}</div>\n        </details>'
                          for q, a in p["faqs"])
        faq_block = f'      <section class="post-faq" aria-label="Frequently asked questions">\n        <h2>Common questions</h2>\n{items}\n      </section>'
    sources_block = (f'      <section class="post-sources" aria-label="Sources">\n        <p class="post-label">Sources</p>\n        {p["sources"]}\n      </section>'
                     if p["sources"] else "")

    hero = fill(t("post-hero.html"), CATEGORY_SHORT=esc(p["categoryShort"]), CATEGORY=esc(" · ".join(x.strip() for x in p["category"].split("|"))),
                TITLE=esc(p["title"]), TAGLINE=esc(p["tagline"]), DATE_ISO=p["datePublished"],
                DATE_HUMAN=human(p["datePublished"]), READ_MINS=p["readMins"])
    main = fill(t("post-main.html"), IMAGE=p["image"], IMAGE_ALT=esc(p["imageAlt"]), BODY=p["body"],
                VISIT_LEAD=esc(p["visitLead"]), SERVICE_HREF=p["serviceLink"]["href"],
                SERVICE_LABEL=esc(p["serviceLink"]["label"]), FAQ_BLOCK=faq_block, SOURCES_BLOCK=sources_block,
                RELATED_CARDS="\n".join(card(r) for r in related_for(p)))
    out = fill(page,
        META_TITLE=esc(p["metaTitle"]), DESCRIPTION=esc(p["description"]), CANONICAL=url,
        PRELOAD=f'  <link rel="preload" as="image" href="{p["image"]}" fetchpriority="high">\n',
        BLOG_CSS=css, OG_TYPE="article", OG_IMAGE=DOMAIN + p["image"], OG_IMAGE_W=1200, OG_IMAGE_H=675,
        OG_IMAGE_ALT=esc(p["imageAlt"]),
        OG_EXTRA=(f'  <meta property="article:published_time" content="{p["datePublished"]}">\n'
                  f'  <meta property="article:modified_time"  content="{p["dateModified"]}">\n'
                  f'  <meta property="article:section"        content="{esc(p["categoryShort"])}">'),
        SCHEMA="\n".join(ld(s) for s in schema), HERO=hero, MAIN=main, PAGE_SCRIPT="")
    dest = ROOT / "blog" / p["slug"] / "index.html"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(out)

# ------------------------------------------------------------------ index page
feature, rest = posts[0], posts[1:]
cats = []
for p in posts:
    if (p["categoryKey"], p["categoryShort"]) not in cats: cats.append((p["categoryKey"], p["categoryShort"]))
buttons = ['        <button type="button" class="blog-filter" data-filter="all" aria-pressed="true">All</button>'] + [
    f'        <button type="button" class="blog-filter" data-filter="{k}" aria-pressed="false">{esc(n)}</button>' for k, n in cats]
index_main = fill(t("index-main.html"), FEATURE_CARD=card(feature, feature=True, title_tag="h2"),
                  FILTER_BUTTONS="\n".join(buttons), CARDS="\n".join(card(p) for p in rest))
filter_js = """  <script>
    (function () {
      var btns = document.querySelectorAll('.blog-filter');
      var cards = document.querySelectorAll('#blogGrid .blog-card');
      btns.forEach(function (b) {
        b.addEventListener('click', function () {
          var f = b.getAttribute('data-filter');
          btns.forEach(function (x) { x.setAttribute('aria-pressed', String(x === b)); });
          cards.forEach(function (c) { c.hidden = !(f === 'all' || c.getAttribute('data-cat') === f); });
        });
      });
    })();
  </script>"""
index_schema = [
    {"@context": "https://schema.org", "@type": "Blog", "@id": f"{DOMAIN}/blog/", "url": f"{DOMAIN}/blog/",
     "name": "Automotive Insight Blog", "inLanguage": "en-AU", "publisher": BUSINESS,
     "blogPost": [{"@type": "BlogPosting", "headline": p["title"], "url": f"{DOMAIN}/blog/{p['slug']}/",
                   "datePublished": p["datePublished"]} for p in posts]},
    {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{DOMAIN}/"},
        {"@type": "ListItem", "position": 2, "name": "Blog", "item": f"{DOMAIN}/blog/"}]},
]
index_desc = "Servicing advice, buying guides and common faults from the Automotive Insight workshop in Shenton Park, Perth. European cars, hybrids and EVs, explained in plain English."
(ROOT / "blog").mkdir(exist_ok=True)
(ROOT / "blog/index.html").write_text(fill(page,
    META_TITLE="Blog | Automotive Insight Shenton Park", DESCRIPTION=esc(index_desc), CANONICAL=f"{DOMAIN}/blog/",
    PRELOAD="", BLOG_CSS=css, OG_TYPE="website", OG_IMAGE=DOMAIN + feature["image"], OG_IMAGE_W=1200, OG_IMAGE_H=675,
    OG_IMAGE_ALT=esc(feature["imageAlt"]), OG_EXTRA="", SCHEMA="\n".join(ld(s) for s in index_schema),
    HERO=t("index-hero.html"), MAIN=index_main, PAGE_SCRIPT=filter_js))

# ------------------------------------------------------------------ remove pages for deleted posts
for d in (ROOT / "blog").iterdir():
    if d.is_dir() and d.name not in by_slug and (d / "index.html").exists():
        print(f"note: blog/{d.name}/ has no source post (left in place; delete it by hand if intended)")

# ------------------------------------------------------------------ generated blocks
def replace_block(path, start, end, content):
    s = path.read_text()
    i, j = s.index(start) + len(start), s.index(end)
    path.write_text(s[:i] + "\n" + content + "\n" + s[j:])

newest = max(p["dateModified"] for p in posts)
entries = [f"  {{ url: '/blog',{' ' * 22}priority: '0.7', changefreq: 'weekly',  lastmod: '{newest}' }},"]
entries += [f"  {{ url: '/blog/{p['slug']}', priority: '0.6', changefreq: 'monthly', lastmod: '{p['dateModified']}' }},"
            for p in sorted(posts, key=lambda p: p["datePublished"])]
replace_block(ROOT / "_worker.js", "  // BLOG-SITEMAP:START (generated by _blog/build.py, do not edit by hand)",
              "  // BLOG-SITEMAP:END", "\n".join(entries))
replace_block(ROOT / "llms.txt", "<!-- BLOG:START -->", "<!-- BLOG:END -->",
              "## Blog\n- Blog index: https://automotiveinsight.com.au/blog/\n" +
              "\n".join(f"- {p['title']}: {DOMAIN}/blog/{p['slug']}/" for p in posts))

print(f"built {len(posts)} posts + blog index")
