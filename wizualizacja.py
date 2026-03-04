import streamlit as st
import pandas as pd
import hashlib
import os
from fpdf import FPDF
import sqlalchemy
from sqlalchemy import text

# --- KONFIGURACJA BAZY ---
try:
    DB_URL = st.secrets["DB_URL"]
    # Używamy prostego silnika bez zbędnych connect_args, które wywalają TypeError
    engine = sqlalchemy.create_engine(
        DB_URL,
        pool_pre_ping=True,
        pool_recycle=300
    )
except Exception as e:
    st.error(f"Błąd konfiguracji bazy: {e}")

def get_data(query, params=None):
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn, params=params)

def run_query(query, params=None):
    with engine.begin() as conn:
        conn.execute(text(query), params)

def get_vda_ap(s, o, d):
    score = s * o * d
    if s >= 9 or score > 200: return "H"
    if s >= 7 or score > 80: return "M"
    return "L"

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="FMEA Industrial System", layout="wide")

# --- TWOJA STYLIZACJA (PRZYWRÓCONA) ---
st.markdown("""
    <style>
    div[data-testid="stVerticalBlock"] > div { gap: 0rem !important; }
    [data-testid="column"] { display: flex; flex-direction: column; justify-content: flex-end !important; }
    .stButton > button { height: 38px !important; border-radius: 4px !important; border: 1px solid #4b5563 !important; background-color: #1f2937 !important; color: #e5e7eb !important; width: 100%; }
    div[data-testid="column"] button { height: 28px !important; min-height: 28px !important; padding: 0px !important; font-size: 14px !important; line-height: 1 !important; }
    .stButton > button:hover { border-color: #3b82f6 !important; color: #3b82f6 !important; }
    input, textarea { background-color: #111827 !important; color: #f3f4f6 !important; border: 1px solid #374151 !important; }
    .main-logo { font-family: 'Inter', sans-serif; font-weight: 800; color: #f3f4f6; border-left: 5px solid #3b82f6; padding-left: 15px; margin-bottom: 25px; }
    </style>
    """, unsafe_allow_html=True)

# --- PDF (BEZPIECZNY) ---
class FMEA_PDF(FPDF):
    def __init__(self, user_name, **kwargs):
        super().__init__(**kwargs)
        self.user_name = user_name
        self.pl_font = 'Helvetica'

def generate_pdf(df, project_name, user_name):
    pdf = FMEA_PDF(user_name=user_name, orientation='L', unit='mm', format='A4')
    pdf.alias_nb_pages(); pdf.add_page(); f = pdf.pl_font
    pdf.set_font(f, 'B', 14); pdf.set_fill_color(30, 41, 59); pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 12, f"  ARKUSZ ANALIZY RYZYKA FMEA: {project_name.upper()}", border=1, ln=True, fill=True)
    pdf.set_text_color(0, 0, 0)
    w = [30, 30, 7, 30, 35, 7, 35, 7, 10, 50, 18, 18]
    current_op = None
    for _, row in df.iterrows():
        if row['nazwa'] != current_op:
            current_op = row['nazwa']; pdf.ln(4)
            pdf.set_font(f, 'B', 8); pdf.set_fill_color(226, 232, 240)
            pdf.cell(0, 8, f" KROK: {row['nazwa']}", border='LTR', ln=True, fill=True)
            headers = ["Wada", "Skutek", "S", "Przyczyna", "Prewencja", "O", "Detekcja", "D", "AP", "Dzialania", "Kto", "Termin"]
            pdf.set_font(f, 'B', 6); pdf.set_fill_color(241, 245, 249)
            for i, h in enumerate(headers): pdf.cell(w[i], 7, h, border=1, align='C', fill=True)
            pdf.ln()
        pdf.set_font(f, '', 7)
        pdf.cell(w[0], 8, str(row['wada'])[:22], border=1)
        pdf.cell(w[1], 8, str(row['skutek'])[:22], border=1)
        pdf.cell(w[2], 8, str(row['s']), border=1, align='C')
        pdf.cell(w[3], 8, str(row['przyczyna'])[:22], border=1)
        pdf.cell(w[4], 8, str(row['prewencja'])[:25], border=1)
        pdf.cell(w[5], 8, str(row['o']), border=1, align='C')
        pdf.cell(w[6], 8, str(row['detekcja'])[:25], border=1)
        pdf.cell(w[7], 8, str(row['d']), border=1, align='C')
        ap_val = str(row['ap']).upper()
        if ap_val == "H": pdf.set_fill_color(255, 200, 200)
        elif ap_val == "M": pdf.set_fill_color(255, 255, 200)
        elif ap_val == "L": pdf.set_fill_color(200, 255, 200)
        else: pdf.set_fill_color(255, 255, 255)
        pdf.cell(10, 8, ap_val, border=1, align='C', fill=True)
        pdf.set_fill_color(255, 255, 255)
        pdf.cell(w[9], 8, str(row['dzialanie'])[:45], border=1)
        pdf.cell(w[10], 8, str(row['kto'])[:12], border=1, align='C')
        pdf.cell(w[11], 8, str(row['termin'])[:12], border=1, align='C'); pdf.ln()
    return bytes(pdf.output())

# --- MODALE (TWOJE ORYGINALNE IKONKI) ---
@st.dialog("➕ Dodaj analizę", width="large")
def modal_wpis(op_id, op_nazwa):
    st.write(f"Krok: **{op_nazwa}**")
    show_actions = st.toggle("Dodaj zalecane działania naprawcze", value=False)
    with st.form("fm_new"):
        wada = st.text_input("Błąd"); skutek = st.text_input("Skutek błędu")
        prz = st.text_input("Przyczyna"); pre = st.text_area("Prewencja", height=68)
        det = st.text_area("Wykrywanie", height=68)
        s = st.select_slider("S", options=range(1, 11), value=5)
        o = st.select_slider("O", options=range(1, 11), value=5)
        d = st.select_slider("D", options=range(1, 11), value=5)
        dz, kt, tr = ("n/a", "n/a", "n/a")
        if show_actions:
            dz = st.text_input("Działania"); kt = st.text_input("Kto"); tr = st.text_input("Termin")
        if st.form_submit_button("ZAPISZ DO BAZY", use_container_width=True):
            ap = get_vda_ap(s, o, d)
            run_query("""INSERT INTO wpisy (op_id, wada, skutek, s, przyczyna, prewencja, o, detekcja, d, ap, dzialanie, kto, termin) 
                         VALUES (:op_id, :w, :sk, :s, :prz, :pre, :o, :det, :d, :ap, :dz, :kt, :tr)""",
                      {"op_id": op_id, "w": wada, "sk": skutek, "s": s, "prz": prz, "pre": pre, "o": o, "det": det, "d": d, "ap": ap, "dz": dz, "kt": kt, "tr": tr})
            st.rerun()

@st.dialog("📝 Edytuj wpis", width="large")
def modal_edycja_wpisu(row):
    with st.form("fm_edit"):
        wada = st.text_input("Rodzaj błędu", value=row['wada'])
        skutek = st.text_input("Skutek błędu", value=row['skutek'])
        s = st.select_slider("Znaczenie (S) ", options=range(1, 11), value=int(row['s']))
        o = st.select_slider("Występowanie (O) ", options=range(1, 11), value=int(row['o']))
        d = st.select_slider("Wykrywalność (D) ", options=range(1, 11), value=int(row['d']))
        dz = st.text_input("Zalecane działania", value=row['dzialanie'])
        kt = st.text_input("Odpowiedzialny", value=row['kto'])
        tr = st.text_input("Termin", value=row['termin'])
        if st.form_submit_button("ZAKTUALIZUJ WPIS", use_container_width=True):
            ap = get_vda_ap(s, o, d)
            run_query("""UPDATE wpisy SET wada=:w, skutek=:sk, s=:s, o=:o, d=:d, ap=:ap, dzialanie=:dz, kto=:kt, termin=:tr WHERE id=:id""",
                      {"w": wada, "sk": skutek, "s": s, "o": o, "d": d, "ap": ap, "dz": dz, "kt": kt, "tr": tr, "id": row['id']})
            st.rerun()

@st.dialog("👤 Edytuj użytkownika")
def modal_edit_user(u_data):
    with st.form("edit_u"):
        new_role = st.selectbox("Rola", ["user", "admin"], index=0 if u_data['role'] == "user" else 1)
        if st.form_submit_button("ZAPISZ ZMIANY", use_container_width=True):
            run_query("UPDATE users SET role=:r WHERE username=:u", {"r": new_role, "u": u_data['username']})
            st.rerun()

# --- LOGOWANIE ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.markdown("<div class='main-logo'><h1>FMEA</h1>SYSTEM</div>", unsafe_allow_html=True)
    u = st.text_input("Użytkownik"); p = st.text_input("Hasło", type="password")
    if st.button("ZALOGUJ", use_container_width=True):
        hp = hashlib.sha256(p.encode()).hexdigest()
        res = get_data("SELECT username, role FROM users WHERE username=:u AND password=:p", {"u": u, "p": hp})
        if not res.empty:
            st.session_state.auth = True
            st.session_state.user = res.iloc[0]['username']; st.session_state.role = res.iloc[0]['role']
            st.rerun()
        else: st.error("Błędne dane")
    st.stop()

# --- APP ---
with st.sidebar:
    st.write(f"👤 {st.session_state.user}")
    if st.button("WYLOGUJ"): st.session_state.auth = False; st.rerun()
    st.divider()
    p_df = get_data("SELECT * FROM projekty")
    sel_p = st.selectbox("Projekt:", ["DASHBOARD"] + p_df['nazwa'].tolist())

if sel_p == "DASHBOARD":
    st.markdown("<div class='main-logo'><h1>FMEA</h1>DASHBOARD</div>", unsafe_allow_html=True)
    if st.session_state.role == "admin":
        t1, t2 = st.tabs(["📁 PROJEKTY", "👥 UŻYTKOWNICY"])
        with t1:
            c1, c2 = st.columns([4, 1])
            np = c1.text_input("Nazwa projektu", label_visibility="collapsed", placeholder="Nazwa...")
            if c2.button("UTWÓRZ", use_container_width=True) and np:
                run_query("INSERT INTO projekty (nazwa) VALUES (:n)", {"n": np}); st.rerun()
            st.divider()
            for _, rp in p_df.iterrows():
                r = st.columns([4, 1])
                r[0].write(f"📂 **{rp['nazwa']}**")
                if r[1].button("USUŃ", key=f"delp_{rp['id']}", use_container_width=True):
                    run_query("DELETE FROM projekty WHERE id=:id", {"id": rp['id']}); st.rerun()
        with t2:
            u_list = get_data("SELECT username, role FROM users")
            for _, ru in u_list.iterrows():
                if ru['username'] != 'admin':
                    r = st.columns([4, 0.4, 0.4])
                    r[0].write(f"👤 **{ru['username']}** — `{ru['role']}`")
                    if r[1].button("📝", key=f"u_{ru['username']}", use_container_width=True): modal_edit_user(ru)
                    if r[2].button("✖", key=f"d_{ru['username']}", use_container_width=True):
                        run_query("DELETE FROM users WHERE username=:u", {"u": ru['username']}); st.rerun()
else:
    p_id = p_df[p_df['nazwa'] == sel_p]['id'].values[0]
    ch1, ch2 = st.columns([4, 1])
    ch1.markdown(f"### 📑 PROJEKT: {sel_p}")
    df_all = get_data("SELECT w.*, o.nazwa FROM wpisy w JOIN operacje o ON w.op_id = o.id WHERE o.p_id = :p_id", {"p_id": int(p_id)})
    if not df_all.empty:
        pdf_b = generate_pdf(df_all, sel_p, st.session_state.user)
        ch2.download_button("📄 POBIERZ PDF", data=pdf_b, file_name=f"FMEA_{sel_p}.pdf", use_container_width=True)

    if st.session_state.role == "admin":
        with st.container(border=True):
            c1, c2 = st.columns([4, 1])
            new_op = c1.text_input("Krok procesu", label_visibility="collapsed", placeholder="Nowy krok...")
            if c2.button("✚ KROK", use_container_width=True) and new_op:
                run_query("INSERT INTO operacje (p_id, nazwa) VALUES (:p, :n)", {"p": int(p_id), "n": new_op}); st.rerun()

    ops = get_data("SELECT * FROM operacje WHERE p_id=:p", {"p": int(p_id)})
    for _, op in ops.iterrows():
        with st.expander(f"⚙️ {op['nazwa']}", expanded=True):
            cols_size = [1.2, 1.2, 0.4, 1.2, 1.2, 0.4, 1.2, 0.4, 0.5, 2.0, 1.2, 1.0, 0.6, 0.6]
            h = st.columns(cols_size)
            labels = ["Błąd", "Skutek", "S", "Przyczyna", "Prewencja", "O", "Wykrywanie", "D", "AP", "Zalecane działania", "Odpowiedzialny", "Termin", "", ""]
            for i, label in enumerate(labels):
                if label: h[i].caption(f"**{label}**")
            if st.session_state.role == "admin":
                if h[13].button("✚", key=f"add_{op['id']}"): modal_wpis(op['id'], op['nazwa'])
            
            df_w = df_all[df_all['op_id'] == op['id']] if not df_all.empty else pd.DataFrame()
            for _, row in df_w.iterrows():
                r = st.columns(cols_size)
                r[0].write(row['wada']); r[1].write(row['skutek']); r[2].write(f"**{row['s']}**")
                r[3].write(row['przyczyna']); r[4].write(row['prewencja']); r[5].write(str(row['o']))
                r[6].write(row['detekcja']); r[7].write(str(row['d']))
                clr = "#ef4444" if row['ap'] == "H" else "#f59e0b" if row['ap'] == "M" else "#10b981"
                r[8].markdown(f"<p style='color:{clr}; font-weight:bold; margin:0;'>{row['ap']}</p>", unsafe_allow_html=True)
                r[9].write(row['dzialanie']); r[10].write(row['kto']); r[11].write(row['termin'])
                if st.session_state.role == "admin":
                    if r[12].button("📝", key=f"e_{row['id']}"): modal_edycja_wpisu(row)
                    if r[13].button("✖", key=f"del_{row['id']}"):
                        run_query("DELETE FROM wpisy WHERE id=:id", {"id": row['id']}); st.rerun()


