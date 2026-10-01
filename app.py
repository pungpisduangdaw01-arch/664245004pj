from __future__ import annotations

import base64
import json
import re
import unicodedata
import zlib
from functools import lru_cache
from html import escape
from io import BytesIO
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote

import pandas as pd
import pymupdf
import streamlit as st
from PIL import Image, ImageOps

from neo4j_service import (
    RELATIONSHIP_TYPES,
    connection_info,
    create_fruit,
    create_user,
    delete_fruit,
    delete_user,
    get_dashboard_metrics,
    get_fruit_images,
    get_fruits,
    get_profile,
    get_users,
    graph_neighborhood,
    list_likes,
    list_similarities,
    ping,
    rebuild_similar,
    recommend_fruits,
    rename_fruit,
    rename_user,
    seed_demo_data,
    set_fruit_image,
    set_likes,
    set_similar,
)

IMAGE_TYPES = ["png", "jpg", "jpeg", "webp"]
IMAGE_MAX_SIDE = 480  # stored pictures are shrunk to this so a node property stays small
FRUIT_IMAGE_DIR = Path(__file__).parent / "images"  # optional bundled photos, matched by name: Mango -> images/mango.jpg

# Sidebar menu: internal page key -> Thai label.
PAGES = {
    "Dashboard": "📊 ภาพรวม",
    "Recommendations": "✨ แนะนำผลไม้",
    "Users": "👤 ผู้ใช้",
    "Fruits": "🍎 ผลไม้",
    "Relationships": "🔗 ความสัมพันธ์",
    "Graph Explorer": "🕸️ กราฟความสัมพันธ์",
    "Admin / Setup": "⚙️ ตั้งค่าข้อมูล",
}

# Hub (landing page): homework 1-3 live in homework/<folder>/, card 4 opens this app.
REPO_URL = "https://github.com/pungpisduangdaw01-arch/664245004pj"
REPO_BRANCH = "main"
HOMEWORK_DIR = Path(__file__).parent / "homework"
HOMEWORK = [
    {
        "folder": "01_club",
        "tag": "01 / CLUB",
        "icon": "👥",
        "title": "ระบบชมรมด้วย Neo4j",
        "text": "ออกแบบกราฟนักศึกษาและชมรม แล้วเขียน Cypher แนะนำชมรมจากเพื่อนของนักศึกษา",
        "name": "งานที่ 1 — ระบบชมรมด้วย Neo4j",
        "about": (
            "เอกสารรวมคำสั่ง Cypher ของระบบชมรมพร้อมภาพผลลัพธ์จาก Neo4j "
            "เริ่มจากสร้างข้อมูลนักศึกษาและชมรม กำหนดความสัมพันธ์ แล้วไล่ทีละขั้นจนได้คำสั่งแนะนำชมรม "
            "ที่เพื่อนของนักศึกษาเป็นสมาชิกมากที่สุด โดยไม่แนะนำชมรมที่เจ้าตัวเป็นสมาชิกอยู่แล้ว"
        ),
        "topics": [
            "สร้าง Student 5 คน และ Club 3 ชมรม ด้วย CREATE",
            "ความสัมพันธ์ FRIEND (นักศึกษา → นักศึกษา) และ MEMBER_OF (นักศึกษา → ชมรม)",
            "ค้นหาด้วย MATCH + WHERE + RETURN",
            "Traversal: S001 → FRIEND → เพื่อน → MEMBER_OF → Club",
            "นับเพื่อนในแต่ละชมรมด้วย count(DISTINCT friend) และตัดชมรมเดิมด้วย WHERE NOT",
            "แนะนำชมรมอันดับ 1 ด้วย ORDER BY และ LIMIT 1",
        ],
    },
    {
        "folder": "02_graph",
        "tag": "02 / GRAPH",
        "icon": "🕸️",
        "title": "ผลไม้ด้วย Graph",
        "text": "สร้างกราฟผู้ใช้และผลไม้ด้วย Python / NetworkX เพื่อสำรวจความชอบและแนะนำผลไม้",
        "name": "งานที่ 2 — ระบบแนะนำผลไม้ด้วย Graph (NetworkX)",
        "about": (
            "Notebook บน Google Colab ที่สร้างกราฟแบบไม่มีทิศทางของผู้ใช้ 10 คนและผลไม้ 7 ชนิดด้วย NetworkX "
            "แล้วใช้การเดินบนกราฟหาผู้ใช้ที่ชอบผลไม้เหมือนกัน เพื่อแนะนำชนิดที่ผู้ใช้ยังไม่เคยเลือก "
            "คะแนนของแต่ละชนิดคือจำนวนเส้นทางที่เดินไปถึงชนิดนั้นได้"
        ),
        "topics": [
            "สร้าง Node ผู้ใช้และผลไม้ และ Edge ความชอบด้วย nx.Graph()",
            "วาดกราฟด้วย matplotlib แยกสี Node สองประเภท",
            "ใช้ G.neighbors() ตอบคำถามว่าใครชอบผลไม้อะไร",
            "หาผู้ใช้ที่ชอบผลไม้เหมือนกันด้วยการเดินสองทอด",
            "นับคะแนนคำแนะนำด้วย Counter และสร้างฟังก์ชัน recommend_fruits()",
        ],
    },
    {
        "folder": "03_neo4j",
        "tag": "03 / NEO4J",
        "icon": "🗃️",
        "title": "ผลไม้ด้วย Neo4j",
        "text": "เชื่อม Neo4j Aura จาก Python แล้วแนะนำผลไม้ด้วย Cypher จากผู้ใช้ที่ชอบผลไม้คล้ายกัน",
        "name": "งานที่ 3 — ระบบแนะนำผลไม้ด้วย Neo4j Aura",
        "about": (
            "Notebook ที่ย้ายโจทย์ผลไม้จากกราฟในหน่วยความจำไปเก็บใน Neo4j Aura ผ่าน Neo4j Python Driver "
            "สร้าง User, Fruit และความสัมพันธ์ LIKES แล้วสร้าง SIMILAR_TO ระหว่างผู้ใช้ที่ชอบผลไม้ชนิดเดียวกัน "
            "จากนั้นเขียน Cypher แนะนำผลไม้ที่ผู้ใช้ที่คล้ายกันชอบแต่เจ้าตัวยังไม่ได้ชอบ เป็นต้นแบบของระบบในการ์ดที่ 4"
        ),
        "topics": [
            "เชื่อมต่อ Neo4j Aura และหา home database",
            "สร้าง Unique Constraint ของ User.name และ Fruit.name",
            "เพิ่มข้อมูลหลายรายการด้วย UNWIND + MERGE",
            "สร้าง SIMILAR_TO จากผู้ใช้ที่ชอบผลไม้ชนิดเดียวกัน",
            "Traversal หลายทอด: User → SIMILAR_TO → User → LIKES → Fruit",
            "นับคะแนนด้วย count(DISTINCT similar) และตัดผลไม้ที่ชอบอยู่แล้วด้วย WHERE NOT",
            "ฟังก์ชัน recommend_fruits()",
        ],
    },
]

st.set_page_config(
    page_title="ระบบแนะนำผลไม้",
    page_icon="🍎",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Base colours and fonts live in .streamlit/config.toml; this adds the fruit-market details.
st.markdown(
    """
    <style>
      :root {
        --cream: #fff9ef; --peel: #ffeed6; --rind: #ffd8a8; --ink: #3b2a1a; --soft-ink: #7a5c3e;
        --mango: #ffc233; --tangerine: #e8590c; --berry: #d6336c; --grape: #7048e8; --leaf: #2f9e44;
      }

      /* Page: cream paper with faint seed dots; top padding clears Streamlit's fixed header */
      .stApp {
        background-color: var(--cream);
        background-image: radial-gradient(rgba(255,192,120,.38) 1.3px, transparent 1.4px);
        background-size: 24px 24px;
      }
      [data-testid="stHeader"] {background: rgba(255,249,239,.88);}
      .block-container {padding-top: 4rem; padding-bottom: 2rem;}

      /* Hero banner: banana-to-peach gradient, fruit-slice circles, and a row of fruit on the right */
      .hero {
        position: relative; overflow: hidden;
        padding: 1.7rem 15rem 1.8rem 2rem; border-radius: 28px; margin-bottom: 1.2rem;
        color: var(--ink); border: 2px solid #ffc078;
        background:
          radial-gradient(circle at 96% 8%, rgba(255,255,255,.55) 0 58px, transparent 59px),
          radial-gradient(circle at 4% 118%, rgba(255,255,255,.40) 0 78px, transparent 79px),
          linear-gradient(115deg, #ffe066 0%, #ffc078 52%, #ffa8a8 100%);
        box-shadow: 0 8px 0 #ffd8a8;
      }
      .hero::after {
        content: "🍊 🍇 🍌 🍓 🥭";
        position: absolute; right: 1.6rem; top: 50%; transform: translateY(-50%) rotate(-4deg);
        font-size: 2.1rem; letter-spacing: .15rem; white-space: nowrap;
        filter: drop-shadow(0 3px 0 rgba(59,42,26,.12));
      }
      .hero h1 {margin: .2rem 0 0; padding: 0; font-size: 2.1rem; color: var(--ink);}
      .hero p {margin: .4rem 0 0; color: #5c4127;}
      .hero .hero-sub {
        display: inline-block; padding: .15rem .7rem; border-radius: 999px;
        background: rgba(255,255,255,.65); color: #c2410c;
        font-size: .75rem; font-weight: 700; letter-spacing: .08em;
      }

      /* Sidebar: light peach with rounded menu items */
      [data-testid="stSidebar"] {border-right: 2px dashed #ffc078;}
      .brand {display: flex; align-items: center; gap: .65rem; margin: .2rem 0 .1rem;}
      .brand .drop {
        width: 46px; height: 46px; flex: 0 0 46px; border-radius: 50%; font-size: 1.45rem;
        display: flex; align-items: center; justify-content: center;
        background: linear-gradient(135deg, #ffe066, #ffa94d); border: 2px solid #fff;
        box-shadow: 0 3px 0 #ffc078;
      }
      .brand b {font-size: 1.12rem; line-height: 1.2; color: var(--ink);}
      .brand span {font-size: .78rem; color: var(--soft-ink);}
      .author {
        padding: .75rem .9rem; border-radius: 18px; font-size: .9rem; line-height: 1.5;
        background: #fff; border: 2px solid var(--rind); color: var(--ink);
      }
      .author small {display: block; color: var(--soft-ink); font-size: .75rem; letter-spacing: .03em;}
      .author b {color: #c2410c;}
      [data-testid="stSidebar"] [role="radiogroup"] {gap: .25rem;}
      [data-testid="stSidebar"] [role="radiogroup"] label {
        width: 100%; padding: .5rem .8rem; border-radius: 999px;
        border: 2px solid transparent; transition: background .15s, border-color .15s;
      }
      [data-testid="stSidebar"] [role="radiogroup"] label:hover {background: rgba(255,255,255,.7);}
      [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
        background: #fff; border-color: #ffa94d; box-shadow: 0 3px 0 #ffd8a8; font-weight: 600;
      }

      /* Buttons: juicy pills that press down on hover */
      [data-testid="stButton"] button, [data-testid="stLinkButton"] a,
      [data-testid="stDownloadButton"] button, [data-testid="stFormSubmitButton"] button {
        border-radius: 999px; font-weight: 600; transition: transform .12s, box-shadow .12s;
      }
      [data-testid="stButton"] button:not(:disabled):hover, [data-testid="stLinkButton"] a:hover,
      [data-testid="stDownloadButton"] button:hover, [data-testid="stFormSubmitButton"] button:hover {
        transform: translateY(1px);
      }
      [data-testid="stButton"] button[kind="primary"]:not(:disabled),
      [data-testid="stFormSubmitButton"] button[kind="primaryFormSubmit"]:not(:disabled),
      button[data-testid="stBaseButton-primary"]:not(:disabled),
      button[data-testid="stBaseButton-primaryFormSubmit"]:not(:disabled) {
        background: linear-gradient(90deg, #f76707, #e8590c); border-color: #d9480f;
        box-shadow: 0 3px 0 #c2410c; color: #fff;
      }

      /* Cards */
      [data-testid="stMetric"] {
        background: #fff; border: 2px solid var(--rind); border-left: 8px solid var(--mango);
        border-radius: 20px; padding: 1rem 1.2rem; box-shadow: 0 5px 0 var(--peel);
      }
      [data-testid="stMetricValue"] {color: var(--tangerine); font-weight: 700;}
      [class*="st-key-card_"], [data-testid="stForm"] {
        background: #fff; border-color: var(--rind) !important; border-radius: 22px;
        box-shadow: 0 5px 0 var(--peel);
      }
      [data-testid="stImage"] img {border-radius: 18px; border: 2px solid var(--peel);}

      .score-pill {
        display: inline-block; padding: .2rem .7rem; border-radius: 999px;
        background: linear-gradient(90deg, #e8590c, #d6336c);
        color: #fff; font-size: .8rem; font-weight: 700;
      }
      .muted {color: var(--soft-ink); font-size: .9rem;}

      /* Hub landing page: each card takes the colour of one fruit */
      .hero.hub {text-align: center; padding: 2.2rem 1.8rem 2rem;}
      .hero.hub::after {position: static; display: block; transform: none; margin-top: 1rem; font-size: 2rem;}
      .hero.hub h1 {font-size: 2.5rem; margin-top: .7rem;}
      .hub-badge {
        display: inline-block; padding: .3rem 1rem; border-radius: 999px;
        font-size: .75rem; font-weight: 700; letter-spacing: .12em;
        background: rgba(255,255,255,.7); color: #c2410c;
      }
      .hub-head {display: flex; align-items: center; justify-content: space-between;}
      .hub-icon {
        width: 48px; height: 48px; border-radius: 50%; font-size: 1.35rem;
        display: flex; align-items: center; justify-content: center;
        background: var(--fruit-soft, var(--peel)); border: 2px solid var(--fruit, var(--mango));
      }
      .hub-tag {font-size: .75rem; font-weight: 700; letter-spacing: .1em; color: var(--fruit-dark, #c2410c);}
      .hub-name {margin: .9rem 0 .2rem !important; padding: 0 !important; font-size: 1.2rem !important; min-height: 3.3rem;}
      .hub-desc {margin: 0; min-height: 6.6rem; color: var(--soft-ink);}
      [class*="st-key-card_hub_"] {
        min-height: 23.5rem; border-top: 8px solid var(--fruit, var(--mango)) !important;
        transition: transform .15s, box-shadow .15s;
      }
      [class*="st-key-card_hub_"]:hover {transform: translateY(-4px); box-shadow: 0 9px 0 var(--peel);}
      .st-key-card_hub_01_club {--fruit: #ffc233; --fruit-soft: #fff3bf; --fruit-dark: #b25e00;}
      .st-key-card_hub_02_graph {--fruit: #9775fa; --fruit-soft: #e5dbff; --fruit-dark: #5f3dc4;}
      .st-key-card_hub_03_neo4j {--fruit: #f06595; --fruit-soft: #ffdeeb; --fruit-dark: #a61e4d;}
      .st-key-card_hub_app {--fruit: #51cf66; --fruit-soft: #d3f9d8; --fruit-dark: #2b8a3e;}
      .hub-footer {text-align: center; color: var(--soft-ink); font-size: .88rem; line-height: 1.8;}
      .hub-footer small {color: #c2410c;}
      .hero.work h1 {font-size: 1.9rem; margin-top: .6rem;}
      .work-section {margin: 0 0 .5rem; padding: 0; font-size: 1.1rem;}
      .nb-label {
        margin: .9rem 0 .25rem; font-size: .72rem; font-weight: 700; letter-spacing: .08em; color: #c2410c;
      }

      @media (max-width: 900px) {
        .hero {padding: 1.3rem 1.2rem 1.4rem;}
        .hero::after {display: none;}
        .hero.hub::after {display: block; font-size: 1.6rem;}
        .hero h1 {font-size: 1.7rem;}
        .hero.hub h1 {font-size: 1.9rem;}
        [class*="st-key-card_hub_"] {min-height: 0;}
        .hub-name, .hub-desc {min-height: 0;}
        .hub-desc {margin-bottom: 1rem;}
      }
      @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after {transition-duration: .01ms !important;}
      }
    </style>
    """,
    unsafe_allow_html=True,
)


def require_connection() -> None:
    try:
        if not ping():
            raise RuntimeError("Neo4j did not return a healthy response")
    except Exception as exc:
        st.error("ยังเชื่อมต่อ Neo4j Aura ไม่สำเร็จ")
        st.code(
            '[neo4j]\nuri = "neo4j+s://96f9ec23.databases.neo4j.io"\n'
            'username = "96f9ec23"\npassword = "YOUR_PASSWORD"\ndatabase = "96f9ec23"',
            language="toml",
        )
        st.caption("ให้นำค่าด้านบนไปใส่ใน .streamlit/secrets.toml (หรือ Streamlit Secrets) และห้าม commit password ลง GitHub")
        st.exception(exc)
        if st.button("ลองเชื่อมต่ออีกครั้ง"):
            st.rerun()
        if st.button("← กลับหน้าหลัก"):
            st.session_state["view"] = "hub"
            st.rerun()
        st.stop()


def flash(message: str) -> None:
    st.session_state["flash"] = message
    # Every successful write bumps the revision; widgets keyed with it are rebuilt from the database.
    st.session_state["rev"] = revision() + 1


def revision() -> int:
    return st.session_state.get("rev", 0)


def show_flash() -> None:
    message = st.session_state.pop("flash", None)
    if message:
        st.success(message)


def user_selector(key: str = "user") -> str:
    users = [u["name"] for u in get_users()]
    if not users:
        st.info('ยังไม่มีข้อมูลผู้ใช้ กรุณาไปที่เมนู "ตั้งค่าข้อมูล" แล้วสร้างข้อมูลตัวอย่าง หรือเพิ่มผู้ใช้ที่เมนู "ผู้ใช้"')
        st.stop()
    return st.selectbox("เลือกผู้ใช้", users, key=key)


def change_summary(current: list[str], chosen: list[str]) -> tuple[list[str], list[str]]:
    added, removed = sorted(set(chosen) - set(current)), sorted(set(current) - set(chosen))
    if added or removed:
        st.write(f"จะเพิ่ม {len(added)} เส้น: {', '.join(added) or '-'} · จะลบ {len(removed)} เส้น: {', '.join(removed) or '-'}")
    return added, removed


def prepare_image(uploaded: Any) -> bytes | None:
    try:
        picture = ImageOps.exif_transpose(Image.open(uploaded)).convert("RGBA")
        flat = Image.new("RGB", picture.size, "white")
        flat.paste(picture, mask=picture.getchannel("A"))
        flat.thumbnail((IMAGE_MAX_SIDE, IMAGE_MAX_SIDE))
        buffer = BytesIO()
        flat.save(buffer, "JPEG", quality=85)
    except Exception:
        return None
    return buffer.getvalue()


def placeholder_svg(name: str) -> str:
    hue = zlib.crc32(name.encode()) % 360
    text = name if len(name) <= 18 else name[:17] + "…"
    font_size = min(11.0, 116 / max(len(text), 1))
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 -40 240 320" width="240" height="320">
  <rect y="-40" width="240" height="320" fill="hsl({hue},60%,94%)"/>
  <circle cx="120" cy="140" r="60" fill="hsl({hue},65%,56%)"/>
  <path d="M120 70 C110 50 120 40 120 30 C120 40 130 50 120 70 Z" fill="#15803d"/>
  <text x="120" y="235" text-anchor="middle" font-family="sans-serif" font-size="{font_size:.1f}" font-weight="700"
        fill="hsl({hue},55%,28%)">{escape(text)}</text>
</svg>"""


@lru_cache(maxsize=None)
def bundled_picture(name: str) -> bytes | None:
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")
    path = FRUIT_IMAGE_DIR / f"{slug}.jpg"
    return path.read_bytes() if slug and path.is_file() else None


def fruit_picture(name: str, images: dict[str, bytes]) -> bytes | str:
    return images.get(name) or bundled_picture(name) or placeholder_svg(name)


def fruit_picture_uri(name: str, images: dict[str, bytes]) -> str:
    data = images.get(name) or bundled_picture(name)
    if data:
        return "data:image/jpeg;base64," + base64.b64encode(data).decode()
    return "data:image/svg+xml;base64," + base64.b64encode(placeholder_svg(name).encode()).decode()


def dot_quote(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def manage_nodes(
    *,
    kind: str,
    noun: str,
    rows: list[dict[str, Any]],
    column_labels: dict[str, str],
    create: Callable[[str], bool],
    rename: Callable[[str, str], bool],
    delete: Callable[[str], bool],
    delete_warning: Callable[[dict[str, Any]], str],
    images: dict[str, bytes] | None = None,
    set_image: Callable[[str, bytes | None], bool] | None = None,
) -> None:
    """Add / edit / delete tabs for nodes whose unique key is `name` (User and Fruit)."""
    st.write(f"ทั้งหมด {len(rows)} รายการ")
    if rows:
        st.dataframe(pd.DataFrame(rows).rename(columns=column_labels), width="stretch", hide_index=True)

    by_name = {row["name"]: row for row in rows}
    add_tab, edit_tab, delete_tab = st.tabs(["➕ เพิ่ม", "✏️ แก้ไข", "🗑️ ลบ"])

    with add_tab:
        with st.form(f"add_{kind}_{revision()}"):
            new_name = st.text_input(f"ชื่อ{noun}")
            upload = st.file_uploader(f"รูป{noun} (ไม่บังคับ)", type=IMAGE_TYPES) if set_image else None
            submitted = st.form_submit_button("เพิ่ม", type="primary")
        if submitted:
            new_name = new_name.strip()
            new_image = prepare_image(upload) if upload else None
            if not new_name:
                st.error(f"กรุณากรอกชื่อ{noun}")
            elif upload and new_image is None:
                st.error("ไฟล์ที่อัปโหลดไม่ใช่รูปภาพที่อ่านได้ กรุณาเลือกไฟล์อื่น")
            elif not create(new_name):
                st.error(f"มี{noun}ชื่อ {new_name} อยู่แล้ว กรุณาใช้ชื่ออื่น")
            else:
                if new_image:
                    set_image(new_name, new_image)
                flash(f"เพิ่ม{noun} {new_name} แล้ว" + (" พร้อมรูป" if new_image else ""))
                st.rerun()

    if not rows:
        edit_tab.info(f"ยังไม่มี{noun}ให้แก้ไข")
        delete_tab.info(f"ยังไม่มี{noun}ให้ลบ")
        return

    with edit_tab:
        edit_name = st.selectbox(f"เลือก{noun}ที่จะแก้ไข", list(by_name), key=f"edit_{kind}")
        has_image = bool(set_image) and edit_name in (images or {})
        if set_image:
            st.image(fruit_picture(edit_name, images or {}), width=160)
            st.caption("รูปปัจจุบัน" if has_image else "ยังไม่มีรูปที่อัปโหลด (แสดงรูปเริ่มต้น)")
        upload, remove_image = None, False
        with st.form(f"edit_{kind}_{edit_name}_{revision()}"):
            edited_name = st.text_input(f"ชื่อ{noun}", value=edit_name)
            st.caption("การเปลี่ยนชื่อไม่กระทบความสัมพันธ์ LIKES / SIMILAR_TO ที่มีอยู่")
            if set_image:
                upload = st.file_uploader(f"เปลี่ยนรูป{noun} (ไม่บังคับ)", type=IMAGE_TYPES)
                if has_image:
                    remove_image = st.checkbox("ลบรูปปัจจุบัน แล้วกลับไปใช้รูปเริ่มต้น")
            submitted = st.form_submit_button("บันทึกการแก้ไข", type="primary")
        if submitted:
            edited_name = edited_name.strip()
            renamed = edited_name != edit_name
            new_image = prepare_image(upload) if upload else None
            if not edited_name:
                st.error("ชื่อห้ามว่าง")
            elif upload and new_image is None:
                st.error("ไฟล์ที่อัปโหลดไม่ใช่รูปภาพที่อ่านได้ กรุณาเลือกไฟล์อื่น")
            elif not (renamed or new_image or remove_image):
                st.info("ยังไม่มีการเปลี่ยนแปลง")
            elif renamed and edited_name in by_name:
                st.error(f"มี{noun}ชื่อ {edited_name} อยู่แล้ว กรุณาใช้ชื่ออื่น")
            elif renamed and not rename(edit_name, edited_name):
                st.error(f"แก้ไขไม่สำเร็จ: ไม่พบ{noun} {edit_name} หรือชื่อ {edited_name} ถูกใช้แล้ว")
            else:
                if new_image:
                    set_image(edited_name, new_image)
                elif remove_image:
                    set_image(edited_name, None)
                name_note = f"เปลี่ยนชื่อ{noun} {edit_name} เป็น {edited_name}" if renamed else f"แก้ไข{noun} {edit_name}"
                image_note = " และเปลี่ยนรูป" if new_image else " และลบรูป" if remove_image else ""
                flash(f"{name_note}{image_note} แล้ว")
                st.rerun()

    with delete_tab:
        delete_name = st.selectbox(f"เลือก{noun}ที่จะลบ", list(by_name), key=f"delete_{kind}")
        st.warning(delete_warning(by_name[delete_name]))
        confirmed = st.checkbox(f"ยืนยันการลบ {delete_name}", key=f"confirm_{kind}_{delete_name}_{revision()}")
        if st.button("ลบ", type="primary", disabled=not confirmed, key=f"delete_button_{kind}"):
            if delete(delete_name):
                flash(f"ลบ{noun} {delete_name} แล้ว")
            st.rerun()


def hub_card_header(icon: str, tag: str, title: str, text: str) -> None:
    st.markdown(
        f"""
        <div class="hub-head"><div class="hub-icon">{icon}</div><div class="hub-tag">{escape(tag)}</div></div>
        <h3 class="hub-name">{escape(title)}</h3>
        <p class="hub-desc">{escape(text)}</p>
        """,
        unsafe_allow_html=True,
    )


def homework_files(folder: str) -> list[Path]:
    return sorted(p for p in (HOMEWORK_DIR / folder).glob("*") if p.is_file() and not p.name.startswith("."))


def github_url(folder: str) -> str:
    return f"{REPO_URL}/tree/{REPO_BRANCH}/homework/{folder}"


def colab_url(folder: str, notebook: Path) -> str:
    repo = REPO_URL.split("github.com/")[1]
    return f"https://colab.research.google.com/github/{repo}/blob/{REPO_BRANCH}/homework/{folder}/{quote(notebook.name)}"


def notebook_text(value: Any) -> str:
    return value if isinstance(value, str) else "".join(value or [])


def output_text(value: Any) -> str:
    return re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", notebook_text(value)).rstrip()


def render_notebook(path: Path) -> None:
    cells = json.loads(path.read_text(encoding="utf-8")).get("cells", [])
    for cell in cells:
        source = notebook_text(cell.get("source"))
        if not source.strip():
            continue
        if cell.get("cell_type") == "markdown":
            st.markdown(source, unsafe_allow_html=True)
            continue
        if cell.get("cell_type") != "code":
            continue
        st.code(source, language="python")
        outputs = [] if re.search(r"^\s*[!%]pip\b", source, re.MULTILINE) else cell.get("outputs", [])
        if outputs:
            st.markdown('<div class="nb-label">ผลลัพธ์</div>', unsafe_allow_html=True)
        for output in outputs:
            kind = output.get("output_type")
            data = output.get("data", {})
            if kind == "stream":
                st.code(output_text(output.get("text")), language=None)
            elif kind == "error":
                st.code(output_text("\n".join(output.get("traceback", []))), language=None)
            elif "image/png" in data:
                st.image(base64.b64decode(notebook_text(data["image/png"])))
            elif "text/plain" in data:
                st.code(output_text(data["text/plain"]), language=None)


@st.cache_data(show_spinner="กำลังเปิดเอกสาร...")
def pdf_page_images(path: str, modified: float) -> list[bytes]:
    with pymupdf.open(path) as document:
        return [page.get_pixmap(dpi=130).tobytes("png") for page in document]


def render_pdf(path: Path) -> None:
    pages = pdf_page_images(str(path), path.stat().st_mtime)
    for number, page in enumerate(pages, start=1):
        st.image(page)
        st.caption(f"หน้า {number} / {len(pages)}")


def render_homework(work: dict[str, Any]) -> None:
    if st.button("← กลับหน้าหลัก"):
        st.session_state["view"] = "hub"
        st.rerun()

    st.markdown(
        f"""
        <div class="hero work">
          <span class="hub-badge">{escape(work["tag"])}</span>
          <h1>{work["icon"]} {escape(work["name"])}</h1>
          <p>{escape(work["text"])}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    files = homework_files(work["folder"])
    viewable = [p for p in files if p.suffix.lower() in (".ipynb", ".pdf")]
    about, actions = st.columns([2, 1])
    with about, st.container(border=True, key="card_work_about"):
        st.markdown('<h3 class="work-section">เกี่ยวกับการบ้านนี้</h3>', unsafe_allow_html=True)
        st.write(work["about"])
        st.markdown("**สิ่งที่ทำในงานนี้**\n" + "\n".join(f"- {topic}" for topic in work["topics"]))
    with actions, st.container(border=True, key="card_work_files"):
        st.markdown('<h3 class="work-section">ไฟล์งาน</h3>', unsafe_allow_html=True)
        for path in files:
            st.caption(f"📄 {path.name} · {path.stat().st_size / 1024:,.0f} KB")
        for path in viewable:
            if path.suffix.lower() == ".ipynb":
                st.link_button("เปิดการบ้านใน Colab ↗", colab_url(work["folder"], path), width="stretch")
        for path in files:
            st.download_button(
                f"ดาวน์โหลด {path.suffix.lstrip('.').upper() or 'ไฟล์'} ↓",
                data=path.read_bytes(),
                file_name=path.name,
                width="stretch",
                key=f"download_{work['folder']}_{path.name}",
            )
        st.link_button("ดูไฟล์บน GitHub ↗", github_url(work["folder"]), width="stretch")

    if not viewable:
        st.info("ยังไม่มีไฟล์ .ipynb หรือ .pdf ให้แสดงในโฟลเดอร์ของงานนี้")
        return
    st.markdown('<h3 class="work-section">เนื้อหาการบ้าน</h3>', unsafe_allow_html=True)
    areas = st.tabs([p.name for p in viewable]) if len(viewable) > 1 else [st.container()]
    for index, (area, path) in enumerate(zip(areas, viewable)):
        with area, st.container(height=760, border=True, key=f"card_frame_{index}"):
            if path.suffix.lower() == ".ipynb":
                render_notebook(path)
            else:
                render_pdf(path)


def render_hub() -> None:
    st.markdown(
        """
        <div class="hero hub">
          <span class="hub-badge">HOMEWORK · RECOMMENDATION HUB</span>
          <h1>รวมการบ้านและระบบแนะนำผลไม้</h1>
          <p>ระบบชมรม · กราฟผลไม้ · Neo4j<br>เลือกงานที่ต้องการเปิดดูได้จากการ์ดด้านล่าง</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    columns = st.columns(len(HOMEWORK) + 1)
    for column, work in zip(columns, HOMEWORK):
        files = homework_files(work["folder"])
        notebook = next((p for p in files if p.suffix.lower() == ".ipynb"), None)
        pdf = next((p for p in files if p.suffix.lower() == ".pdf"), None)
        with column, st.container(border=True, key=f"card_hub_{work['folder']}"):
            hub_card_header(work["icon"], work["tag"], work["title"], work["text"])
            if not files:
                st.caption(f"⏳ ยังไม่มีไฟล์งาน — วางไฟล์ไว้ในโฟลเดอร์ `homework/{work['folder']}/`")
                continue
            if st.button("ดูการบ้าน →", type="primary", width="stretch", key=f"open_{work['folder']}"):
                st.session_state["view"] = "homework"
                st.session_state["homework"] = work["folder"]
                st.rerun()
            if notebook:
                st.link_button("เปิดการบ้านใน Colab ↗", colab_url(work["folder"], notebook), width="stretch")
            elif pdf:
                st.download_button(
                    "ดาวน์โหลดเอกสาร PDF ↓",
                    data=pdf.read_bytes(),
                    file_name=pdf.name,
                    mime="application/pdf",
                    width="stretch",
                    key=f"pdf_{work['folder']}",
                )
            else:
                st.link_button("ดูไฟล์บน GitHub ↗", github_url(work["folder"]), width="stretch")

    with columns[-1], st.container(border=True, key="card_hub_app"):
        hub_card_header(
            "🍎",
            f"{len(HOMEWORK) + 1:02d} / APPLICATION",
            "ระบบแนะนำผลไม้",
            "ทดลองระบบแนะนำผลไม้ เลือกผู้ใช้ จัดการข้อมูลผู้ใช้ ผลไม้ ความสัมพันธ์ และสำรวจกราฟภายในแอป",
        )
        if st.button("เข้าสู่ระบบแนะนำ →", type="primary", width="stretch"):
            st.session_state["view"] = "app"
            st.rerun()
        st.link_button("ดูโค้ดโปรเจกต์บน GitHub ↗", REPO_URL, width="stretch")

    st.divider()
    st.markdown(
        """
        <div class="hub-footer">
          ชิษณุพงศ์ เกตุพูนทอง · รหัสนักศึกษา 664245004<br>
          <small>Fruit Recommendation Project</small>
        </div>
        """,
        unsafe_allow_html=True,
    )


view = st.session_state.setdefault("view", "hub")
opened_work = next((w for w in HOMEWORK if w["folder"] == st.session_state.get("homework")), None)
if view == "homework" and opened_work:
    render_homework(opened_work)
    st.stop()
if view != "app":
    render_hub()
    st.stop()

require_connection()

with st.sidebar:
    if st.button("← กลับหน้าหลัก", width="stretch"):
        st.session_state["view"] = "hub"
        st.rerun()
    st.markdown(
        """
        <div class="brand">
          <div class="drop">🍊</div>
          <div><b>ระบบแนะนำผลไม้</b><br><span>Neo4j Aura + Streamlit</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.divider()
    page = st.radio("เมนู", list(PAGES), format_func=PAGES.get, key="page")
    st.divider()
    st.markdown(
        """
        <div class="author">
          <small>ผู้จัดทำ</small>
          <b>ชิษณุพงศ์ เกตุพูนทอง</b><br>
          รหัสนักศึกษา 664245004
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown(
    """
    <div class="hero">
      <div class="hero-sub">FRUIT RECOMMENDATION SYSTEM</div>
      <h1>ระบบแนะนำผลไม้</h1>
      <p>แนะนำผลไม้ด้วย Graph Database จากผู้ใช้ที่ชอบผลไม้คล้ายกัน</p>
    </div>
    """,
    unsafe_allow_html=True,
)

show_flash()

if page == "Dashboard":
    st.subheader("ภาพรวมระบบ")
    m = get_dashboard_metrics()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("👤 ผู้ใช้", m.get("users", 0))
    c2.metric("🍎 ผลไม้", m.get("fruits", 0))
    c3.metric("❤️ ความสัมพันธ์ LIKES", m.get("likes", 0))
    c4.metric("🤝 ความสัมพันธ์ SIMILAR_TO", m.get("similarities", 0))

    fruits = sorted(get_fruits(), key=lambda f: (-f["likes"], f["name"]))
    if fruits:
        st.markdown("### ความนิยมของผลไม้")
        images = get_fruit_images()
        table = [{"image": fruit_picture_uri(f["name"], images), **f} for f in fruits]
        st.dataframe(
            pd.DataFrame(table).rename(columns={"image": "รูป", "name": "ผลไม้", "likes": "จำนวนคนชอบ"}),
            column_config={
                "รูป": st.column_config.ImageColumn(width="small"),
                "จำนวนคนชอบ": st.column_config.ProgressColumn(
                    format="%d", min_value=0, max_value=max(1, fruits[0]["likes"])
                ),
            },
            width="stretch",
            hide_index=True,
        )

    st.divider()
    profile = get_profile(user_selector("dash_user"))

    if profile:
        left, mid, right = st.columns([1, 1, 1])
        with left:
            st.markdown(f"### {profile['name']}")
            st.write(f"**ชอบผลไม้:** {len(profile['liked'])} ชนิด")
            st.write(f"**ผู้ใช้ที่คล้ายกัน:** {len(profile['similar'])} คน")
        with mid:
            st.markdown("### ผลไม้ที่ชอบ")
            if profile["liked"]:
                st.dataframe(pd.DataFrame({"ผลไม้": profile["liked"]}), width="stretch", hide_index=True)
            else:
                st.info("ยังไม่มีผลไม้ที่ชอบ")
        with right:
            st.markdown("### ผู้ใช้ที่คล้ายกัน")
            if profile["similar"]:
                st.dataframe(pd.DataFrame({"ผู้ใช้": profile["similar"]}), width="stretch", hide_index=True)
            else:
                st.info("ยังไม่มีผู้ใช้ที่คล้ายกัน")

elif page == "Recommendations":
    st.subheader("✨ ผลไม้ที่แนะนำ")
    user = user_selector("rec_user")
    top_n = st.slider("จำนวนคำแนะนำ", 1, 10, 5, key="rec_top_n")
    rows = recommend_fruits(user, top_n)

    st.caption("score = จำนวนผู้ใช้ที่คล้ายกัน (SIMILAR_TO) ที่ชอบผลไม้นั้น โดยตัดผลไม้ที่ผู้ใช้ชอบอยู่แล้วออก")
    if not rows:
        st.info("ยังไม่มีคำแนะนำสำหรับผู้ใช้นี้ (อาจชอบผลไม้ครบทุกชนิดแล้ว หรือยังไม่มีผู้ใช้ที่คล้ายกัน)")
    images = get_fruit_images() if rows else {}
    for i, row in enumerate(rows, start=1):
        names = ", ".join(row.get("similar_names") or [])
        with st.container(border=True, key=f"card_rec_{i}"):
            picture, details = st.columns([1, 6], vertical_alignment="center")
            picture.image(fruit_picture(row["fruit"], images), width=120)
            details.markdown(
                f"""
                <span class="score-pill">#{i} · score {row['score']}</span>
                <h3 style="margin:.55rem 0 .2rem 0">{escape(row['fruit'])}</h3>
                <p><b>เหตุผล:</b> ผู้ใช้ที่คล้ายกัน {row['score']} คนชอบ ({escape(names)})</p>
                """,
                unsafe_allow_html=True,
            )

elif page == "Users":
    st.subheader("👤 จัดการผู้ใช้")
    manage_nodes(
        kind="user",
        noun="ผู้ใช้",
        rows=get_users(),
        column_labels={"name": "ชื่อ", "likes": "ชอบผลไม้ (ชนิด)", "similar": "ผู้ใช้ที่คล้ายกัน (คน)"},
        create=create_user,
        rename=rename_user,
        delete=delete_user,
        delete_warning=lambda row: (
            f"การลบจะลบความสัมพันธ์ของผู้ใช้คนนี้ด้วย: LIKES {row['likes']} เส้น "
            f"และ SIMILAR_TO {row['similar']} เส้น (ย้อนกลับไม่ได้)"
        ),
    )

elif page == "Fruits":
    st.subheader("🍎 จัดการผลไม้")
    fruits = get_fruits()
    images = get_fruit_images()
    if fruits:
        gallery = st.columns(6)
        for i, f in enumerate(fruits):
            with gallery[i % 6]:
                st.image(fruit_picture(f["name"], images), width=140)
                st.caption(f["name"])
        st.caption("ผลไม้ที่ยังไม่ได้อัปโหลดรูปจะใช้รูปในโฟลเดอร์ images ตามชื่อ (ถ้ามี) ไม่เช่นนั้นจะแสดงรูปที่ระบบวาดให้ อัปโหลดรูปเองได้ที่แท็บ เพิ่ม หรือ แก้ไข ด้านล่าง")
    manage_nodes(
        kind="fruit",
        noun="ผลไม้",
        rows=fruits,
        images=images,
        set_image=set_fruit_image,
        column_labels={"name": "ชื่อ", "likes": "จำนวนคนชอบ"},
        create=create_fruit,
        rename=rename_fruit,
        delete=delete_fruit,
        delete_warning=lambda row: (
            f"การลบจะลบความสัมพันธ์ LIKES ที่ชี้มายังผลไม้นี้ด้วย {row['likes']} เส้น (ย้อนกลับไม่ได้)"
        ),
    )

elif page == "Relationships":
    st.subheader("🔗 จัดการความสัมพันธ์")
    user = user_selector("rel_user")
    profile = get_profile(user)
    if not profile:
        st.error(f"ไม่พบผู้ใช้ {user} (อาจถูกลบไปแล้ว)")
        st.stop()
    st.caption("เลือกเพิ่มหรือเอาออกในช่องด้านล่าง แล้วกดบันทึก ระบบจะเพิ่ม/ลบความสัมพันธ์ให้ตรงกับที่เลือก")

    likes_tab, similar_tab = st.tabs(["LIKES (ผู้ใช้ → ผลไม้)", "SIMILAR_TO (ผู้ใช้ ↔ ผู้ใช้)"])

    with likes_tab:
        chosen = st.multiselect(
            f"ผลไม้ที่ {user} ชอบ",
            [f["name"] for f in get_fruits()],
            default=profile["liked"],
            key=f"likes_{user}_{revision()}",
        )
        added, removed = change_summary(profile["liked"], chosen)
        if st.button("บันทึก LIKES", type="primary", disabled=not (added or removed)):
            set_likes(user, chosen)
            flash(f"บันทึก LIKES ของ {user} แล้ว (เพิ่ม {len(added)} · ลบ {len(removed)})")
            st.rerun()
        st.caption("การแก้ LIKES ไม่เปลี่ยน SIMILAR_TO ให้อัตโนมัติ ถ้าต้องการให้ตรงกับความชอบล่าสุด ให้กดคำนวณใหม่ที่แท็บ SIMILAR_TO")

        st.markdown("#### LIKES ทั้งหมดในระบบ")
        st.dataframe(
            pd.DataFrame(list_likes(), columns=["user", "fruit"]).rename(columns={"user": "ผู้ใช้", "fruit": "ผลไม้"}),
            width="stretch",
            hide_index=True,
        )

    with similar_tab:
        chosen = st.multiselect(
            f"ผู้ใช้ที่คล้ายกับ {user}",
            [u["name"] for u in get_users() if u["name"] != user],
            default=profile["similar"],
            key=f"similar_{user}_{revision()}",
        )
        st.caption("SIMILAR_TO เป็นความสัมพันธ์สองทิศทาง: ถ้า A คล้าย B แล้ว B ก็คล้าย A ด้วย (เก็บเพียงหนึ่งเส้นต่อคู่)")
        added, removed = change_summary(profile["similar"], chosen)
        if st.button("บันทึก SIMILAR_TO", type="primary", disabled=not (added or removed)):
            set_similar(user, chosen)
            flash(f"บันทึก SIMILAR_TO ของ {user} แล้ว (เพิ่ม {len(added)} · ลบ {len(removed)})")
            st.rerun()

        with st.expander("คำนวณ SIMILAR_TO ใหม่ทั้งระบบจากผลไม้ที่ชอบร่วมกัน (วิธีเดียวกับ notebook)"):
            st.warning(
                "ระบบจะลบ SIMILAR_TO เดิมทั้งหมด (รวมที่แก้ไขด้วยมือ) แล้วเชื่อมผู้ใช้ทุกคู่ที่ชอบผลไม้ชนิดเดียวกันอย่างน้อย 1 ชนิด"
            )
            confirmed = st.checkbox("ยืนยันการคำนวณใหม่", key=f"confirm_rebuild_{revision()}")
            if st.button("คำนวณ SIMILAR_TO ใหม่", disabled=not confirmed):
                pairs = rebuild_similar()
                flash(f"คำนวณ SIMILAR_TO ใหม่แล้ว ได้ทั้งหมด {pairs} คู่")
                st.rerun()

        st.markdown("#### SIMILAR_TO ทั้งหมดในระบบ")
        st.dataframe(
            pd.DataFrame(list_similarities(), columns=["user1", "user2"]).rename(
                columns={"user1": "ผู้ใช้คนที่ 1", "user2": "ผู้ใช้คนที่ 2"}
            ),
            width="stretch",
            hide_index=True,
        )

elif page == "Graph Explorer":
    st.subheader("🕸️ กราฟความสัมพันธ์")
    user = user_selector("graph_user")
    left, right = st.columns(2)
    depth = left.slider("ระยะจากผู้ใช้ (จำนวนทอด)", 1, 3, 1, key="graph_depth")
    types = right.multiselect("ความสัมพันธ์ที่แสดง", RELATIONSHIP_TYPES, default=RELATIONSHIP_TYPES, key="graph_types")
    rows = graph_neighborhood(user, depth, types) if types else []
    if not rows:
        st.info("ไม่พบความสัมพันธ์ของผู้ใช้นี้ตามเงื่อนไขที่เลือก")
    else:
        fill = {"User": "#fff3bf", "Fruit": "#ffdeeb"}
        dot = [
            "digraph G {",
            'rankdir="LR";',
            'node [shape=box, style="rounded,filled", fillcolor="#ffffff", color="#ffa94d", fontname="sans-serif"];',
            'edge [color="#65716c", fontcolor="#65716c", fontname="sans-serif", fontsize=10];',
        ]
        seen_nodes = set()
        for r in rows:
            for label, name in [(r["source_label"], r["source"]), (r["target_label"], r["target"])]:
                if (label, name) not in seen_nodes:
                    border = ', penwidth=3, color="#e8590c"' if (label, name) == ("User", user) else ""
                    dot.append(
                        f'{dot_quote(f"{label}:{name}")} [label={dot_quote(name)}, fillcolor="{fill.get(label, "#ffffff")}"{border}];'
                    )
                    seen_nodes.add((label, name))
            source = dot_quote(f'{r["source_label"]}:{r["source"]}')
            target = dot_quote(f'{r["target_label"]}:{r["target"]}')
            # SIMILAR_TO is treated as symmetric, so draw it without an arrowhead.
            direction = ", dir=none" if r["relationship"] == "SIMILAR_TO" else ""
            dot.append(f'{source} -> {target} [label="{r["relationship"]}"{direction}];')
        dot.append("}")
        st.caption(f"พบ {len(seen_nodes)} node และ {len(rows)} relationship · สีเหลือง = ผู้ใช้ · สีชมพู = ผลไม้ · กรอบหนา = ผู้ใช้ที่เลือก")
        st.graphviz_chart("\n".join(dot), width="stretch")
        with st.expander("ดูข้อมูล relationship ที่ใช้วาดกราฟ"):
            st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

elif page == "Admin / Setup":
    st.subheader("⚙️ ตั้งค่าข้อมูล")
    info = connection_info()
    st.markdown(
        f"""
        **การเชื่อมต่อ Neo4j Aura** ✅ เชื่อมต่อสำเร็จ
        - URI: `{info['uri']}`
        - Username: `{info['username']}`
        - Database: `{info['database']}`

        **Graph schema** (ตาม notebook งานที่ 3)
        - `(:User {{name}})-[:LIKES]->(:Fruit {{name, image}})`
        - `(:User)-[:SIMILAR_TO]-(:User)` — ผู้ใช้ที่ชอบผลไม้ชนิดเดียวกันอย่างน้อย 1 ชนิด
        """
    )

    st.markdown("### เพิ่มข้อมูลตัวอย่าง")
    st.info(
        "สร้าง Constraint และเพิ่มข้อมูลจาก notebook (ผู้ใช้ 10 คน ผลไม้ 5 ชนิด LIKES 21 เส้น) ด้วย MERGE "
        "จึงกดซ้ำได้และไม่ลบผู้ใช้/ผลไม้ที่เพิ่มเอง จากนั้นคำนวณ SIMILAR_TO ใหม่ทั้งระบบจากผลไม้ที่ชอบร่วมกัน"
    )
    if st.button("สร้าง Constraint + ข้อมูลตัวอย่าง", type="primary"):
        with st.spinner("กำลังสร้างข้อมูล..."):
            seed_demo_data()
        flash("สร้างข้อมูลตัวอย่างเรียบร้อยแล้ว")
        st.rerun()

    st.markdown("### ล้างข้อมูลแล้วเริ่มใหม่")
    st.warning("ลบ User และ Fruit ทั้งหมดพร้อมความสัมพันธ์และรูปที่อัปโหลด แล้วสร้างข้อมูลตัวอย่างใหม่ (ย้อนกลับไม่ได้)")
    confirmed = st.checkbox("ยืนยันการล้างข้อมูลทั้งหมด", key=f"confirm_reset_{revision()}")
    if st.button("ล้างข้อมูลและสร้างข้อมูลตัวอย่างใหม่", disabled=not confirmed):
        with st.spinner("กำลังล้างและสร้างข้อมูล..."):
            seed_demo_data(reset=True)
        flash("ล้างข้อมูลและสร้างข้อมูลตัวอย่างใหม่เรียบร้อยแล้ว")
        st.rerun()
