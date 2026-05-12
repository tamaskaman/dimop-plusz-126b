"""
DIMOP Plusz 126B Tudásbázis — Kérdés-Válasz alkalmazás
Dual API: Claude Sonnet 4 + GPT-5 Mini
"""

import streamlit as st
import os
import time
from pathlib import Path

# ── Oldal beállítás ──────────────────────────────────────────────
st.set_page_config(
    page_title="DIMOP Plusz 126B Tudásbázis",
    page_icon="📋",
    layout="centered",
)

# ── Téma leírások a routinghoz ───────────────────────────────────
TÉMÁK = {
    "0_Bevezeto.md": {
        "cím": "Bevezető",
        "leírás": "A képzési sorozat áttekintése, a DIMOP Plusz 126B felhívás ellenőrzési folyamatának bemutatása, a 8 téma felsorolása."
    },
    "1_Felhivas_bemutatasa.md": {
        "cím": "Felhívás bemutatása",
        "leírás": "A DIMOP Plusz 126B felhívás céljai, keretei, támogatási konstrukció, digitalizáció, pályázati feltételek áttekintése."
    },
    "2_Tamogatast_igenylok_kore.md": {
        "cím": "Támogatást igénylők köre",
        "leírás": "Ki nyújthat be támogatási kérelmet, jogosultsági feltételek, szervezeti formák (egyéni vállalkozók, ügyvédi irodák, Bt, Kft stb.), TEÁOR szűrés."
    },
    "3_KKV_minosites.md": {
        "cím": "KKV minősítés",
        "leírás": "Kis- és középvállalkozás minősítés, vállalkozásméretek (mikro, kis, közép), létszám, árbevétel, mérlegfőösszeg, kapcsolt vállalkozások, partner vállalkozások, 25%-os szabály, konszolidáció."
    },
    "4_Kizaro_okok.md": {
        "cím": "Kizáró okok",
        "leírás": "Kizáró okok ellenőrzése, adótartozás, végelszámolás, csőd, jogerős ítélet, összeférhetetlenség, kettős finanszírozás."
    },
    "5_De_minimis.md": {
        "cím": "De minimis támogatás",
        "leírás": "Csekély összegű (de minimis) támogatás szabályai, 300 ezer eurós korlát, halmozási szabályok, egységes vállalkozás fogalma."
    },
    "6_Arachne.md": {
        "cím": "Arachne kockázatértékelés",
        "leírás": "Arachne kockázatértékelő rendszer használata, kockázati jelzések (red flag), szűrés, ellenőrzési lépések az Arachne felületén."
    },
    "7_Fejlesztesi_celok_koltsegek.md": {
        "cím": "Fejlesztési célok és költségek",
        "leírás": "Fejlesztési célok, támogatható tevékenységek, költségvetés, költségtípusok, egységárak, piaci ár ellenőrzés, költségek elszámolhatósága."
    },
    "8_Ellenorzes_menete.md": {
        "cím": "Ellenőrzés menete",
        "leírás": "A projektkiválasztás és ellenőrzés teljes menete, EPTK felületen végzett ellenőrzés lépései, bírálati szempontok, döntéshozatal, hiánypótlás."
    },
}

# ── Rendszer prompt ──────────────────────────────────────────────
SYSTEM_PROMPT = """Te a DIMOP Plusz 126B felhívás projektkiválasztási folyamatának szakértője vagy.

Az alábbi tudásbázis képzési videók tisztított átiratából készült. Minden fájl elején szerepel a forrás videó neve (Forrás sor). Minden szöveges sor tartalmaz egy időbélyeget [ÓÓ:PP:MM-ÓÓ:PP:MM] formátumban.

FELADATOD:
1. A feltett kérdésre KIZÁRÓLAG a tudásbázis tartalma alapján válaszolj.
2. A válaszban MINDIG hivatkozz a forrás videó nevére ÉS az időbélyegre, például: "A KKV minősítés videóban (3_KKV_minosites, 5. rész) [00:05:12-00:05:30] elhangzik, hogy..."
3. Ha a kérdésre a tudásbázis nem tartalmaz választ, mondd el őszintén.
4. Válaszolj magyarul, szakszerűen de közérthetően.
5. Ha több témakör is érintett, hivatkozz mindegyikre.
6. FORMÁZÁS: használj normál szöveget, félkövér kiemelést és felsorolást. NE használj nagy címsorokat (# ## ###), csak ha a válasz több fő részt tartalmaz. A válasz legyen folyó szöveg, nem prezentáció.

TUDÁSBÁZIS:
"""

# ── Routing prompt ───────────────────────────────────────────────
ROUTING_PROMPT_TEMPLATE = """Az alábbi témakörök állnak rendelkezésre egy DIMOP Plusz 126B tudásbázisban:

{témák_lista}

A felhasználó kérdése: "{kérdés}"

Mely témakör(ök) relevánsak a kérdés megválaszolásához?
Válaszolj CSAK a fájlnevek vesszővel elválasztott listájával, semmi mással.
Ha több is releváns, sorold fel relevancia szerint csökkenő sorrendben.
Példa válasz: 3_KKV_minosites.md, 2_Tamogatast_igenylok_kore.md"""


# ── Segédfüggvények ──────────────────────────────────────────────

@st.cache_data
def load_tudásbázis():
    """Betölti az összes markdown fájlt a tudásbázis mappából."""
    kb_dir = Path(__file__).parent / "tudásbázis"
    fájlok = {}
    for fájl in sorted(kb_dir.glob("*.md")):
        fájlok[fájl.name] = fájl.read_text(encoding="utf-8")
    return fájlok


def get_témák_lista():
    """Formázott témalista a routing prompthoz."""
    sorok = []
    for fájl, info in TÉMÁK.items():
        sorok.append(f"- {fájl}: {info['cím']} — {info['leírás']}")
    return "\n".join(sorok)


def route_claude(kérdés: str, client) -> list[str]:
    """Claude Haiku-val határozza meg a releváns témákat."""
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        messages=[{
            "role": "user",
            "content": ROUTING_PROMPT_TEMPLATE.format(
                témák_lista=get_témák_lista(),
                kérdés=kérdés
            )
        }]
    )
    return parse_routing_response(response.content[0].text)


def route_openai(kérdés: str, client) -> list[str]:
    """GPT-5 Mini Mini-vel határozza meg a releváns témákat."""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=200,
        messages=[{
            "role": "user",
            "content": ROUTING_PROMPT_TEMPLATE.format(
                témák_lista=get_témák_lista(),
                kérdés=kérdés
            )
        }]
    )
    return parse_routing_response(response.choices[0].message.content)


def parse_routing_response(válasz: str) -> list[str]:
    """Kinyeri a fájlneveket a routing válaszból."""
    összes_fájl = list(TÉMÁK.keys())
    találatok = []
    for fájl in összes_fájl:
        if fájl.replace(".md", "") in válasz or fájl in válasz:
            találatok.append(fájl)
    # Ha nem talált semmit, az összes releváns lehet
    if not találatok:
        találatok = összes_fájl
    return találatok


def build_context(fájlnevek: list[str], tudásbázis: dict, max_tokens: int = 180000) -> str:
    """Összeállítja a kontextust a kiválasztott fájlokból."""
    context_parts = []
    total_chars = 0
    char_limit = max_tokens * 3.5  # ~3.5 karakter/token becslés

    for fájl in fájlnevek:
        if fájl in tudásbázis:
            tartalom = tudásbázis[fájl]
            if total_chars + len(tartalom) < char_limit:
                context_parts.append(tartalom)
                total_chars += len(tartalom)
            else:
                break

    return "\n\n---\n\n".join(context_parts)


def answer_claude(kérdés: str, context: str, client, messages_history: list) -> str:
    """Claude Opus-szal válaszol a kérdésre."""
    system_with_kb = SYSTEM_PROMPT + context

    # Üzenet-előzmények összeállítása
    api_messages = []
    for msg in messages_history:
        api_messages.append({"role": msg["role"], "content": msg["content"]})
    api_messages.append({"role": "user", "content": kérdés})

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=[{
            "type": "text",
            "text": system_with_kb,
            "cache_control": {"type": "ephemeral"}
        }],
        messages=api_messages
    )

    return response.content[0].text


def answer_openai(kérdés: str, context: str, client, messages_history: list) -> str:
    """GPT-5 Mini-gyel válaszol a kérdésre."""
    system_with_kb = SYSTEM_PROMPT + context

    # Üzenet-előzmények összeállítása
    api_messages = [{"role": "system", "content": system_with_kb}]
    for msg in messages_history:
        api_messages.append({"role": msg["role"], "content": msg["content"]})
    api_messages.append({"role": "user", "content": kérdés})

    response = client.chat.completions.create(
        model="gpt-5-mini",
        max_completion_tokens=4096,
        messages=api_messages
    )

    return response.choices[0].message.content


# ── Jelszóvédelem ────────────────────────────────────────────────

def check_password():
    """Egyszerű jelszóvédelem."""
    app_password = st.secrets.get("APP_PASSWORD", "")
    if not app_password:
        return True  # Ha nincs jelszó beállítva, mindenkit beenged

    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True

    st.markdown("## 🔐 DIMOP Plusz 126B Tudásbázis")
    st.markdown("Kérlek, add meg a jelszót a belépéshez.")
    password = st.text_input("Jelszó:", type="password")
    if st.button("Belépés"):
        if password == app_password:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Hibás jelszó!")
    return False


# ── Fő alkalmazás ────────────────────────────────────────────────

def main():
    if not check_password():
        return

    # ── Fejléc ──
    st.markdown("## 📋 DIMOP Plusz 126B Tudásbázis")
    st.markdown("*Kérdezz a projektkiválasztási folyamatról — válasz időbélyeg-hivatkozásokkal*")

    # ── Oldalsáv: modellválasztás ──
    with st.sidebar:
        st.markdown("### Beállítások")

        modell = st.radio(
            "Válaszadó modell:",
            ["Claude Sonnet 4", "GPT-5 Mini"],
            index=0,
            help="Melyik AI modell válaszoljon a kérdésedre?"
        )

        st.markdown("---")
        st.markdown("### Témakörök a tudásbázisban")
        for fájl, info in TÉMÁK.items():
            st.markdown(f"**{info['cím']}**")

        st.markdown("---")
        st.markdown(f"*Tudásbázis méret: ~201K token*")

        if st.button("🗑️ Előzmények törlése"):
            st.session_state.messages = []
            st.session_state.routed_files = []
            st.rerun()

    # ── API kliensek inicializálása ──
    try:
        if modell == "Claude Sonnet 4":
            from anthropic import Anthropic
            client = Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
        else:
            from openai import OpenAI
            client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    except Exception as e:
        st.error(f"API kulcs hiba: {e}")
        st.info("Kérlek, állítsd be az API kulcsokat a `.streamlit/secrets.toml` fájlban.")
        return

    # ── Tudásbázis betöltése ──
    tudásbázis = load_tudásbázis()

    if not tudásbázis:
        st.error("Nem találhatók tudásbázis fájlok a `tudásbázis/` mappában!")
        return

    # ── Chat előzmények ──
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "routed_files" not in st.session_state:
        st.session_state.routed_files = []

    # Előzmények megjelenítése
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # ── Új kérdés ──
    if kérdés := st.chat_input("Kérdezz a DIMOP Plusz 126B felhívásról..."):
        # Kérdés megjelenítése
        with st.chat_message("user"):
            st.markdown(kérdés)
        st.session_state.messages.append({"role": "user", "content": kérdés})

        # Válasz generálása
        with st.chat_message("assistant"):
            with st.status("Gondolkodom...", expanded=True) as status:
                # 1. Téma routing
                st.write("🔍 Releváns témakörök keresése...")
                try:
                    if modell == "Claude Sonnet 4":
                        releváns_fájlok = route_claude(kérdés, client)
                    else:
                        releváns_fájlok = route_openai(kérdés, client)
                except Exception as e:
                    st.error(f"Routing hiba: {e}")
                    releváns_fájlok = list(TÉMÁK.keys())

                téma_nevek = [TÉMÁK[f]["cím"] for f in releváns_fájlok if f in TÉMÁK]
                st.write(f"📚 Témakörök: {', '.join(téma_nevek)}")

                # 2. Kontextus összeállítása
                st.write("📖 Tudásbázis betöltése...")
                context = build_context(releváns_fájlok, tudásbázis)

                # 3. Válasz generálása
                st.write(f"🤖 Válasz generálása ({modell})...")
                start_time = time.time()

                try:
                    if modell == "Claude Sonnet 4":
                        válasz = answer_claude(kérdés, context, client, st.session_state.messages[:-1])
                    else:
                        válasz = answer_openai(kérdés, context, client, st.session_state.messages[:-1])
                except Exception as e:
                    válasz = f"Hiba történt a válasz generálásakor: {e}"

                elapsed = time.time() - start_time
                status.update(
                    label=f"Kész! ({elapsed:.1f} mp, {modell})",
                    state="complete",
                    expanded=False
                )

            # Válasz megjelenítése
            st.markdown(válasz)

            # Meta információ
            st.caption(
                f"🏷️ Modell: {modell} | "
                f"📚 Témák: {', '.join(téma_nevek)} | "
                f"⏱️ {elapsed:.1f} mp"
            )

        st.session_state.messages.append({"role": "assistant", "content": válasz})


if __name__ == "__main__":
    main()
