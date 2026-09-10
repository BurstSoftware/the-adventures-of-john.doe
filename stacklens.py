# app.py
# pip install streamlit requests beautifulsoup4

import re
import json
from collections import defaultdict
from urllib.parse import urlparse, urljoin

import requests
from bs4 import BeautifulSoup
import streamlit as st

st.set_page_config(
    page_title="StackLens — Website Tech Detector",
    page_icon="🔍",
    layout="wide",
)

FINGERPRINTS = [
    {"name": "WordPress", "cats": ["CMS", "Blogs"],
     "html": [r"wp-content", r"wp-includes", r"wp-json"],
     "headers": {"x-powered-by": r"WP Engine"},
     "meta_generator": r"WordPress(?:\s([\d.]+))?"},
    {"name": "WooCommerce", "cats": ["Ecommerce", "WordPress plugins"],
     "html": [r"woocommerce", r"wc-add-to-cart", r"wp-content/plugins/woocommerce"]},
    {"name": "Yoast SEO", "cats": ["SEO", "WordPress plugins"],
     "html": [r"yoast", r"YoastSEO", r"wp-content/plugins/wordpress-seo"]},
    {"name": "Elementor", "cats": ["Page builders", "WordPress plugins"],
     "html": [r"elementor", r"wp-content/plugins/elementor"]},
    {"name": "Contact Form 7", "cats": ["WordPress plugins"],
     "html": [r"wpcf7", r"contact-form-7"]},
    {"name": "Jetpack", "cats": ["WordPress plugins"],
     "html": [r"/wp-content/plugins/jetpack/"]},
    {"name": "Gravity Forms", "cats": ["WordPress plugins"],
     "html": [r"gravityforms", r"gform_wrapper"]},
    {"name": "WP Rocket", "cats": ["Caching", "WordPress plugins"],
     "html": [r"wp-rocket"]},
    {"name": "Shopify", "cats": ["Ecommerce", "PaaS"],
     "html": [r"cdn\.shopify\.com", r"Shopify\.theme"],
     "headers": {"x-shopid": r".+", "x-shopify-stage": r".+"},
     "cookies": {"_shopify_s": r".+", "_shopify_y": r".+"}},
    {"name": "Wix", "cats": ["CMS", "Website builders"],
     "html": [r"static\.wixstatic\.com", r"wix-thunderbolt"],
     "headers": {"x-wix-request-id": r".+"}},
    {"name": "Squarespace", "cats": ["CMS", "Website builders"],
     "html": [r"static\.squarespace\.com", r"squarespace-cdn"],
     "headers": {"server": r"Squarespace"}},
    {"name": "Webflow", "cats": ["CMS", "Website builders"],
     "html": [r"uploads-ssl\.webflow\.com", r"data-wf-page"],
     "headers": {"x-wf-region": r".+"}},
    {"name": "Drupal", "cats": ["CMS"],
     "html": [r"Drupal\.settings", r"sites/default/files"],
     "headers": {"x-drupal-cache": r".+", "x-generator": r"Drupal"},
     "meta_generator": r"Drupal\s*([\d.]+)?"},
    {"name": "Joomla", "cats": ["CMS"],
     "html": [r"/media/jui/", r"option=com_"],
     "meta_generator": r"Joomla"},
    {"name": "Ghost", "cats": ["CMS", "Blogs"],
     "html": [r"ghost-url", r"/ghost/api/"],
     "meta_generator": r"Ghost(?:\s([\d.]+))?"},
    {"name": "Magento", "cats": ["Ecommerce"],
     "html": [r"mage/cookies", r"Magento_"],
     "cookies": {"mage-cache-sessid": r".+"}},
    {"name": "BigCommerce", "cats": ["Ecommerce"],
     "html": [r"cdn\d*\.bigcommerce\.com", r"stencil"]},

    {"name": "React", "cats": ["JavaScript frameworks"],
     "html": [r"data-reactroot", r"react-dom", r"__NEXT_DATA__"],
     "scripts": [r"react(?:[-.]dom)?(?:\.min)?\.js"]},
    {"name": "Next.js", "cats": ["JavaScript frameworks", "Web frameworks"],
     "html": [r"__NEXT_DATA__", r"/_next/static/"],
     "headers": {"x-powered-by": r"Next\.js"}},
    {"name": "Vue.js", "cats": ["JavaScript frameworks"],
     "html": [r"data-v-[a-f0-9]{8}", r"__vue__"],
     "scripts": [r"vue(?:\.min)?\.js"]},
    {"name": "Nuxt.js", "cats": ["JavaScript frameworks"],
     "html": [r"__NUXT__", r"/_nuxt/"]},
    {"name": "Angular", "cats": ["JavaScript frameworks"],
     "html": [r"ng-version", r"ng-app", r"_ngcontent-"]},
    {"name": "Svelte", "cats": ["JavaScript frameworks"],
     "html": [r"data-svelte-", r"__svelte"]},
    {"name": "SvelteKit", "cats": ["Web frameworks"],
     "html": [r"__sveltekit"]},
    {"name": "Gatsby", "cats": ["Static site generators"],
     "html": [r"___gatsby", r"/page-data/"]},
    {"name": "Astro", "cats": ["Static site generators"],
     "html": [r"astro-island", r"data-astro-cid"]},
    {"name": "Django", "cats": ["Web frameworks"],
     "cookies": {"csrftoken": r".+"},
     "html": [r"csrfmiddlewaretoken"]},
    {"name": "Laravel", "cats": ["Web frameworks"],
     "cookies": {"laravel_session": r".+", "XSRF-TOKEN": r".+"}},
    {"name": "Ruby on Rails", "cats": ["Web frameworks"],
     "headers": {"x-runtime": r".+"},
     "html": [r"csrf-param"]},
    {"name": "Express", "cats": ["Web frameworks"],
     "headers": {"x-powered-by": r"Express"}},
    {"name": "ASP.NET", "cats": ["Web frameworks"],
     "headers": {"x-aspnet-version": r"([\d.]+)", "x-powered-by": r"ASP\.NET"},
     "cookies": {"ASP.NET_SessionId": r".+"},
     "html": [r"__VIEWSTATE"]},
    {"name": "Flask", "cats": ["Web frameworks"],
     "headers": {"server": r"Werkzeug"}},

    {"name": "PHP", "cats": ["Programming languages"],
     "headers": {"x-powered-by": r"PHP(?:/([\d.]+))?"},
     "cookies": {"PHPSESSID": r".+"},
     "html": [r"\.php(?:\?|#|\"|')"]},
    {"name": "Node.js", "cats": ["Programming languages"],
     "headers": {"x-powered-by": r"Express|Next\.js|NestJS"}},
    {"name": "Python", "cats": ["Programming languages"],
     "headers": {"server": r"gunicorn|uwsgi|Werkzeug"}},
    {"name": "Ruby", "cats": ["Programming languages"],
     "headers": {"x-powered-by": r"Phusion Passenger", "x-runtime": r".+"}},
    {"name": "Java", "cats": ["Programming languages"],
     "headers": {"x-powered-by": r"Servlet|JSP|Java", "server": r"Apache-Coyote|Tomcat"},
     "cookies": {"JSESSIONID": r".+"}},

    {"name": "MySQL", "cats": ["Databases"]},
    {"name": "PostgreSQL", "cats": ["Databases"],
     "html": [r"PostgreSQL"]},
    {"name": "MongoDB", "cats": ["Databases"],
     "html": [r"mongodb"]},
    {"name": "Redis", "cats": ["Databases", "Caching"],
     "html": [r"\bredis\b"]},

    {"name": "jQuery", "cats": ["JavaScript libraries"],
     "scripts": [r"jquery[-.]([\d.]+)(?:\.min)?\.js", r"jquery(?:\.min)?\.js"]},
    {"name": "jQuery UI", "cats": ["JavaScript libraries"],
     "scripts": [r"jquery-ui"]},
    {"name": "Lodash", "cats": ["JavaScript libraries"],
     "scripts": [r"lodash(?:\.min)?\.js"]},
    {"name": "Bootstrap", "cats": ["UI frameworks"],
     "html": [r"bootstrap(?:\.min)?\.(?:css|js)"],
     "scripts": [r"bootstrap(?:\.bundle)?(?:\.min)?\.js"]},
    {"name": "Tailwind CSS", "cats": ["UI frameworks"],
     "html": [r"cdn\.tailwindcss\.com", r"tailwindcss"]},
    {"name": "Font Awesome", "cats": ["Font scripts"],
     "html": [r"font-awesome", r"fontawesome"]},
    {"name": "Google Fonts", "cats": ["Font scripts"],
     "html": [r"fonts\.googleapis\.com", r"fonts\.gstatic\.com"]},

    {"name": "Google Analytics", "cats": ["Analytics"],
     "html": [r"google-analytics\.com/analytics\.js", r"gtag\(", r"G-[A-Z0-9]+", r"UA-\d+-\d+"],
     "cookies": {"_ga": r".+", "_gid": r".+"}},
    {"name": "Google Tag Manager", "cats": ["Tag managers"],
     "html": [r"googletagmanager\.com/gtm\.js", r"GTM-[A-Z0-9]+"]},
    {"name": "Google Ads", "cats": ["Advertising"],
     "html": [r"googleadservices\.com", r"googlesyndication\.com", r"gtag/js\?id=AW-"]},
    {"name": "Hotjar", "cats": ["Analytics"],
     "html": [r"static\.hotjar\.com"],
     "cookies": {"_hjSession": r".+"}},
    {"name": "Mixpanel", "cats": ["Analytics"],
     "html": [r"cdn\.mxpnl\.com", r"mixpanel"]},
    {"name": "Segment", "cats": ["Analytics"],
     "html": [r"cdn\.segment\.com"]},
    {"name": "Amplitude", "cats": ["Analytics"],
     "html": [r"cdn\.amplitude\.com"]},
    {"name": "Facebook Pixel", "cats": ["Analytics", "Advertising"],
     "html": [r"connect\.facebook\.net/.+/fbevents", r"fbq\("],
     "cookies": {"_fbp": r".+"}},
    {"name": "HubSpot", "cats": ["Marketing automation", "CRM"],
     "html": [r"js\.hs-scripts\.com"],
     "cookies": {"hubspotutk": r".+"}},
    {"name": "Intercom", "cats": ["Live chat"],
     "html": [r"widget\.intercom\.io"]},
    {"name": "Drift", "cats": ["Live chat"],
     "html": [r"js\.driftt\.com"]},
    {"name": "Mailchimp", "cats": ["Marketing automation"],
     "html": [r"chimpstatic\.com", r"list-manage\.com"]},
    {"name": "Klaviyo", "cats": ["Marketing automation"],
     "html": [r"static\.klaviyo\.com", r"_learnq"]},

    {"name": "Cloudflare", "cats": ["CDN", "Security", "Hosting"],
     "headers": {"server": r"cloudflare", "cf-ray": r".+", "cf-cache-status": r".+"},
     "cookies": {"__cf_bm": r".+", "cf_clearance": r".+"}},
    {"name": "Amazon CloudFront", "cats": ["CDN", "Hosting"],
     "headers": {"via": r"cloudfront", "x-amz-cf-id": r".+"}},
    {"name": "Fastly", "cats": ["CDN"],
     "headers": {"via": r"fastly", "x-served-by": r"cache-"}},
    {"name": "Akamai", "cats": ["CDN"],
     "headers": {"server": r"AkamaiGHost", "x-akamai-transformed": r".+"}},
    {"name": "Vercel", "cats": ["PaaS", "Hosting", "CDN"],
     "headers": {"x-vercel-id": r".+", "server": r"Vercel", "x-vercel-cache": r".+"}},
    {"name": "Netlify", "cats": ["PaaS", "Hosting"],
     "headers": {"server": r"Netlify", "x-nf-request-id": r".+"}},
    {"name": "GitHub Pages", "cats": ["Hosting"],
     "headers": {"server": r"GitHub.com", "x-github-request-id": r".+"}},
    {"name": "WP Engine", "cats": ["Hosting"],
     "headers": {"x-powered-by": r"WP Engine"}},
    {"name": "Kinsta", "cats": ["Hosting"],
     "headers": {"x-kinsta-cache": r".+"}},
    {"name": "nginx", "cats": ["Web servers"],
     "headers": {"server": r"nginx(?:/([\d.]+))?"}},
    {"name": "Apache HTTP Server", "cats": ["Web servers"],
     "headers": {"server": r"Apache(?:/([\d.]+))?"}},
    {"name": "IIS", "cats": ["Web servers"],
     "headers": {"server": r"Microsoft-IIS(?:/([\d.]+))?"}},
    {"name": "LiteSpeed", "cats": ["Web servers", "Hosting"],
     "headers": {"server": r"LiteSpeed"}},
    {"name": "Caddy", "cats": ["Web servers"],
     "headers": {"server": r"Caddy"}},
    {"name": "Amazon S3", "cats": ["Hosting", "PaaS"],
     "headers": {"server": r"AmazonS3"}},
    {"name": "Google Cloud", "cats": ["Hosting", "PaaS"],
     "headers": {"via": r"google", "server": r"Google Frontend"}},
    {"name": "AWS ELB", "cats": ["Load balancers"],
     "headers": {"server": r"awselb"}},

    {"name": "Stripe", "cats": ["Payment processors"],
     "html": [r"js\.stripe\.com", r"js\.stripe\.com/v3"]},
    {"name": "PayPal", "cats": ["Payment processors"],
     "html": [r"paypal\.com/sdk", r"paypalobjects\.com"]},
    {"name": "reCAPTCHA", "cats": ["Security"],
     "html": [r"google\.com/recaptcha", r"grecaptcha"]},
    {"name": "hCaptcha", "cats": ["Security"],
     "html": [r"hcaptcha\.com"]},
    {"name": "Cloudflare Turnstile", "cats": ["Security"],
     "html": [r"challenges\.cloudflare\.com/turnstile"]},
    {"name": "YouTube", "cats": ["Video players"],
     "html": [r"youtube\.com/embed", r"youtube-nocookie\.com"]},
    {"name": "Vimeo", "cats": ["Video players"],
     "html": [r"player\.vimeo\.com"]},
    {"name": "Disqus", "cats": ["Comment systems"],
     "html": [r"disqus\.com"]},
]

IMPLIES = {
    "WordPress": ["PHP", "MySQL"],
    "WooCommerce": ["WordPress", "PHP", "MySQL"],
    "Yoast SEO": ["WordPress"],
    "Elementor": ["WordPress"],
    "Contact Form 7": ["WordPress"],
    "Jetpack": ["WordPress"],
    "Gravity Forms": ["WordPress"],
    "WP Rocket": ["WordPress"],
    "Laravel": ["PHP"],
    "Django": ["Python"],
    "Flask": ["Python"],
    "Ruby on Rails": ["Ruby"],
    "Next.js": ["React", "Node.js"],
    "Nuxt.js": ["Vue.js", "Node.js"],
    "Express": ["Node.js"],
    "SvelteKit": ["Svelte", "Node.js"],
    "Gatsby": ["React", "Node.js"],
    "ASP.NET": ["IIS"],
}

KNOWN_NAMES = {fp["name"] for fp in FINGERPRINTS}
CATS_BY_NAME = {fp["name"]: fp["cats"] for fp in FINGERPRINTS}

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

PLUGIN_SLUG_RE = re.compile(r"/wp-content/plugins/([a-zA-Z0-9_-]+)/", re.I)


def normalize_url(raw: str) -> str:
    raw = raw.strip()
    if not raw:
        return raw
    if not re.match(r"^https?://", raw, re.I):
        raw = "https://" + raw
    return raw


def fetch(url: str, timeout: int = 20) -> dict:
    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })
    resp = session.get(url, timeout=timeout, allow_redirects=True)
    cookies = {c.name: c.value for c in session.cookies}
    headers = {k.lower(): v for k, v in resp.headers.items()}
    return {
        "final_url": resp.url,
        "status": resp.status_code,
        "headers": headers,
        "cookies": cookies,
        "html": resp.text or "",
        "elapsed_ms": int(resp.elapsed.total_seconds() * 1000),
    }


def extract_page_signals(html: str, base_url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    scripts = []
    for s in soup.find_all("script"):
        src = s.get("src")
        if src:
            scripts.append(urljoin(base_url, src))
        if s.string:
            scripts.append(s.string[:2000])
    metas = {}
    for m in soup.find_all("meta"):
        name = (m.get("name") or m.get("property") or "").lower()
        content = m.get("content") or ""
        if name:
            metas[name] = content
    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    return {"scripts": scripts, "meta": metas, "title": title}


def match_patterns(text: str, patterns) -> tuple[bool, str]:
    if not text or not patterns:
        return False, ""
    for pat in patterns:
        m = re.search(pat, text, re.I | re.S)
        if m:
            ver = m.group(1) if m.lastindex else ""
            return True, ver or ""
    return False, ""


def humanize_slug(slug: str) -> str:
    return slug.replace("-", " ").replace("_", " ").title()


def discover_wp_plugins(html: str) -> list[dict]:
    slugs = sorted(set(PLUGIN_SLUG_RE.findall(html)))
    out = []
    for slug in slugs:
        name = humanize_slug(slug)
        if name in KNOWN_NAMES:
            continue
        out.append({
            "name": name,
            "categories": ["WordPress plugins"],
            "version": "",
            "confidence": 80,
            "evidence": [f"path wp-content/plugins/{slug}"],
        })
    return out


def apply_implies(found: dict) -> dict:
    changed = True
    while changed:
        changed = False
        for name in list(found):
            for implied in IMPLIES.get(name, []):
                if implied not in found:
                    found[implied] = {
                        "name": implied,
                        "categories": CATS_BY_NAME.get(implied, ["Inferred"]),
                        "version": "",
                        "confidence": 60,
                        "evidence": [f"implied by {name}"],
                    }
                    changed = True
    return found


def detect(page: dict) -> list[dict]:
    html = page["html"]
    headers = page["headers"]
    cookies = page["cookies"]
    signals = extract_page_signals(html, page["final_url"])
    script_blob = "\n".join(signals["scripts"])
    found = {}

    for fp in FINGERPRINTS:
        hits = 0
        version = ""
        reasons = []

        if "headers" in fp:
            for hname, pat in fp["headers"].items():
                val = headers.get(hname.lower(), "")
                ok, ver = match_patterns(val, [pat])
                if ok:
                    hits += 1
                    version = version or ver
                    reasons.append(f"header {hname}")

        if "cookies" in fp:
            for cname, pat in fp["cookies"].items():
                matched_cookie = None
                for existing in cookies:
                    if existing.lower() == cname.lower() or existing.lower().startswith(cname.lower()):
                        matched_cookie = existing
                        break
                if matched_cookie is not None:
                    if pat == r".+":
                        ok, ver = True, ""
                    else:
                        ok, ver = match_patterns(cookies[matched_cookie], [pat])
                    if ok:
                        hits += 1
                        version = version or ver
                        reasons.append(f"cookie {matched_cookie}")

        if "html" in fp:
            ok, ver = match_patterns(html, fp["html"])
            if ok:
                hits += 1
                version = version or ver
                reasons.append("html")

        if "scripts" in fp:
            ok, ver = match_patterns(script_blob, fp["scripts"])
            if ok:
                hits += 1
                version = version or ver
                reasons.append("script")

        if "meta_generator" in fp:
            gen = signals["meta"].get("generator", "")
            ok, ver = match_patterns(gen, [fp["meta_generator"]])
            if ok:
                hits += 1
                version = version or ver
                reasons.append("meta generator")

        if hits:
            confidence = min(100, 50 + hits * 25)
            prev = found.get(fp["name"])
            if not prev or confidence > prev["confidence"]:
                found[fp["name"]] = {
                    "name": fp["name"],
                    "categories": fp["cats"],
                    "version": version,
                    "confidence": confidence,
                    "evidence": reasons,
                }

    for plugin in discover_wp_plugins(html):
        found.setdefault(plugin["name"], plugin)

    found = apply_implies(found)
    return sorted(found.values(), key=lambda x: (-x["confidence"], x["name"].lower()))


def group_by_category(techs: list[dict]) -> dict:
    grouped = defaultdict(list)
    for t in techs:
        for c in t["categories"]:
            grouped[c].append(t)
    return dict(sorted(grouped.items(), key=lambda kv: kv[0].lower()))


def friendly_request_error(exc: Exception) -> str:
    text = str(exc)
    if "NameResolutionError" in text or "Failed to resolve" in text or "Name or service not known" in text:
        host = ""
        m = re.search(r"host='([^']+)'", text)
        if m:
            host = m.group(1)
        return (
            f"The hostname `{host or 'entered'}` could not be resolved. "
            "Check the spelling (this is a DNS miss, not a detector failure)."
        )
    return f"Could not fetch the site: {exc}"


st.markdown(
    """
    <style>
      .tech-chip {
        display:inline-block; padding:6px 12px; margin:4px;
        border-radius:999px; background:#111827; color:#e5e7eb;
        border:1px solid #374151; font-size:0.9rem;
      }
      .cat-title { font-size:1.05rem; font-weight:600; margin-top:0.4rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🔍 StackLens")
st.caption(
    "Detects CMS, plugins, languages, frameworks, hosting, CDN, analytics, "
    "and inferred databases from public headers, HTML, cookies, and scripts."
)

col_in, col_btn = st.columns([4, 1])
with col_in:
    url_input = st.text_input(
        "Website URL",
        placeholder="example.com or https://example.com",
        label_visibility="collapsed",
    )
with col_btn:
    run = st.button("Analyze", type="primary", use_container_width=True)

with st.expander("Options"):
    timeout = st.slider("Request timeout (seconds)", 5, 40, 20)
    focus = st.multiselect(
        "Show only these category groups (optional)",
        [
            "Programming languages",
            "Databases",
            "CMS",
            "WordPress plugins",
            "Web frameworks",
            "JavaScript frameworks",
            "Hosting",
            "CDN",
            "PaaS",
            "Web servers",
            "Analytics",
            "Ecommerce",
            "Security",
        ],
    )

if run and url_input.strip():
    url = normalize_url(url_input)
    parsed = urlparse(url)
    if not parsed.netloc:
        st.error("Please enter a valid URL.")
        st.stop()

    with st.spinner(f"Fetching {url} …"):
        try:
            page = fetch(url, timeout=timeout)
        except requests.exceptions.SSLError:
            st.error("SSL error. The site’s certificate could not be verified.")
            st.stop()
        except requests.exceptions.Timeout:
            st.error("Request timed out.")
            st.stop()
        except requests.RequestException as e:
            st.error(friendly_request_error(e))
            st.stop()

    techs = detect(page)
    if focus:
        techs = [t for t in techs if any(c in focus for c in t["categories"])]

    grouped = group_by_category(techs)
    signals = extract_page_signals(page["html"], page["final_url"])

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Status", page["status"])
    m2.metric("Technologies", len(techs))
    m3.metric("Categories", len(grouped))
    m4.metric("Response", f"{page['elapsed_ms']} ms")

    st.write(f"**Final URL:** `{page['final_url']}`")
    if signals["title"]:
        st.write(f"**Title:** {signals['title']}")

    if not techs:
        st.warning("No known technologies matched for the current filters.")
    else:
        tabs = st.tabs(["By category", "All technologies", "Raw signals"])

        with tabs[0]:
            cols = st.columns(2)
            items = list(grouped.items())
            for i, (cat, items_in_cat) in enumerate(items):
                with cols[i % 2]:
                    st.markdown(f"<div class='cat-title'>{cat}</div>", unsafe_allow_html=True)
                    chips = []
                    for t in items_in_cat:
                        label = t["name"]
                        if t["version"]:
                            label += f" {t['version']}"
                        chips.append(f"<span class='tech-chip'>{label}</span>")
                    st.markdown("".join(chips), unsafe_allow_html=True)

        with tabs[1]:
            rows = [
                {
                    "Technology": t["name"],
                    "Version": t["version"] or "—",
                    "Categories": ", ".join(t["categories"]),
                    "Confidence": t["confidence"],
                    "Evidence": ", ".join(t["evidence"]),
                }
                for t in techs
            ]
            st.dataframe(rows, use_container_width=True, hide_index=True)
            st.download_button(
                "Download JSON",
                data=json.dumps({"url": page["final_url"], "technologies": techs}, indent=2),
                file_name="stacklens.json",
                mime="application/json",
            )

        with tabs[2]:
            st.subheader("Response headers")
            st.json(page["headers"])
            st.subheader("Cookies")
            st.json(page["cookies"] or {"_": "none visible on first request"})
            st.subheader("Meta tags")
            st.json(signals["meta"])
            with st.expander("HTML preview (first 8 KB)"):
                st.code(page["html"][:8192], language="html")

elif run:
    st.warning("Enter a URL first.")
else:
    st.info(
        "Enter a public website and click **Analyze**. "
        "Languages and databases that are not leaked in public responses are inferred "
        "(for example WordPress → PHP + MySQL)."
    )
