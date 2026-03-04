import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import os
from fpdf import FPDF
import sqlalchemy

from sqlalchemy import text

# Połączenie z Supabase (URL musi być w Secrets na Streamlit Cloud)
# Format w Secrets: DB_URL = "postgresql://postgres:haslo@db.xyz.supabase.co:5432/postgres"
DB_URL = st.secrets["DB_URL"]
engine = sqlalchemy.create_engine(DB_URL)

# Pomocnicza funkcja do pobierania danych (zastępuje pd.read_sql)
def get_data(query, params=None):
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn, params=params)

# Pomocnicza funkcja do zapisu (zastępuje conn.execute)
def run_query(query, params=None):
    with engine.begin() as conn:
        conn.execute(text(query), params)

# --- KONFIGURACJA ---
st.set_page_config(page_title="FMEA Industrial System", layout="wide")
DB_NAME = "fmea_industrial_v5.db"

# --- TWOJA STYLIZACJA + POPRAWKI PRZYCISKÓW ---
st.markdown("""
    <style>
    div[data-testid="stVerticalBlock"] > div { gap: 0rem !important; }
    [data-testid="column"] { display: flex; flex-direction: column; justify-content: flex-end !important; }
    
    /* Główne przyciski (KROK, PDF, ZALOGUJ) */
    .stButton > button { 
        height: 38px !important; border-radius: 4px !important;
        border: 1px solid #4b5563 !important;
        background-color: #1f2937 !important; color: #e5e7eb !important;
        width: 100%;
    }
    
    /* Specyficzne ustawienia dla ikon w tabeli (📝, ✖, ✚) */
    div[data-testid="column"] button {
        height: 28px !important;
        min-height: 28px !important;
        padding: 0px !important;
        font-size: 14px !important;
        line-height: 1 !important;
    }

    .stButton > button:hover { border-color: #3b82f6 !important; color: #3b82f6 !important; }
    input, textarea { background-color: #111827 !important; color: #f3f4f6 !important; border: 1px solid #374151 !important; }
    .main-logo { font-family: 'Inter', sans-serif; font-weight: 800; color: #f3f4f6; border-left: 5px solid #3b82f6; padding-left: 15px; margin-bottom: 25px; }
    </style>
    """, unsafe_allow_html=True)

# --- PDF ---
class FMEA_PDF(FPDF):
    def __init__(self, user_name, **kwargs):
        super().__init__(**kwargs)
        self.user_name = user_name
        # Próba załadowania Arial, jeśli nie ma - używamy standardowej Helvetici
        try:
            path = "C:\\Windows\\Fonts\\arial.ttf"
            if os.path.exists(path):
                self.add_font('ArialPL', '', path, uni=True)
                self.pl_font = 'ArialPL'
            else:
                self.pl_font = 'Helvetica' # Standardowa czcionka Linuxa
        except:
            self.pl_font = 'Helvetica'

def generate_pdf(df, project_name, user_name):
    pdf = FMEA_PDF(user_name=user_name, orientation='L', unit='mm', format='A4')
    pdf.alias_nb_pages(); pdf.add_page(); f = pdf.pl_font
    pdf.set_font(f, 'B', 14); pdf.set_fill_color(30, 41, 59); pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 12, f"  ARKUSZ ANALIZY RYZYKA FMEA: {project_name.upper()}", border=1, ln=True, fill=True)
    pdf.set_text_color(0, 0, 0)
    current_op = None
    w = [30, 30, 7, 30, 35, 7, 35, 7, 10, 50, 18, 18]
    for _, row in df.iterrows():
        if row['nazwa'] != current_op:
            current_op = row['nazwa']; pdf.ln(4)
            pdf.set_font(f, 'B', 8); pdf.set_fill_color(226, 232, 240)
            pdf.cell(0, 8, f" KROK: {row['nazwa']}", border='LTR', ln=True, fill=True)
            headers = ["Wada", "Skutek", "S", "Przyczyna", "Prewencja", "O", "Detekcja", "D", "AP", "Zalecane dzialania", "Odpowiedzialny", "Termin"]
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
      # --- KOLOROWANIE AP ---
        ap_val = str(row['ap']).upper()
        if ap_val == "H":
            pdf.set_fill_color(255, 200, 200) # Jasny czerwony
        elif ap_val == "M":
            pdf.set_fill_color(255, 255, 200) # Jasny żółty
        elif ap_val == "L":
            pdf.set_fill_color(200, 255, 200) # Jasny zielony
        else:
            pdf.set_fill_color(255, 255, 255) # Biały dla n/a

        # Rysowanie komórki AP (ustaw szerokość taką, jaką masz w nagłówku, np. 10)
        pdf.cell(10, 8, ap_val, border=1, align='C', fill=True)
        
        # WAŻNE: Po narysowaniu komórki AP zresetuj kolor tła na biały dla reszty wiersza
        pdf.set_fill_color(255, 255, 255)
        pdf.cell(w[9], 8, str(row['dzialanie'])[:45], border=1)
        pdf.cell(w[10], 8, str(row['kto'])[:12], border=1, align='C')
        pdf.cell(w[11], 8, str(row['termin'])[:12], border=1, align='C'); pdf.ln()
    return bytes(pdf.output())

# --- DATABASE ---


# Pobieranie URL z bezpiecznych ustawień Streamlit
DB_URL = st.secrets["DB_URL"]
engine = sqlalchemy.create_engine(DB_URL)

def run_query(query, params=None, is_select=False):
    with engine.connect() as conn:
        if is_select:
            return pd.read_sql(query, conn, params=params)
        else:
            conn.execute(sqlalchemy.text(query), params)
            conn.commit()

# --- MODALS ---

@st.dialog("➕ Dodaj analizę", width="large")
def modal_wpis(op_id, op_nazwa):
    st.write(f"Krok: **{op_nazwa}**")
    # Suwak decydujący o sekcji działań
    show_actions = st.toggle("Dodaj zalecane działania naprawcze", value=False)
    
    with st.form("fm_new"):
        # Układ pionowy - jeden pod drugim
        wada = st.text_input("Błąd")
        skutek = st.text_input("Skutek błędu")
        prz = st.text_input("Przyczyna")
        pre = st.text_area("Prewencja (obecne działania)", height=68)
        det = st.text_area("Wykrywanie (obecne metody)", height=68)
        
        st.markdown("---")
        st.subheader("Ocena Ryzyka")
        s = st.select_slider("Znaczenie (S)", options=range(1, 11), value=5)
        o = st.select_slider("Występowanie (O)", options=range(1, 11), value=5)
        d = st.select_slider("Wykrywalność (D)", options=range(1, 11), value=5)
        
        if show_actions:
            st.markdown("---")
            st.subheader("Plan Działań")
            dz = st.text_input("Zalecane działania")
            kt = st.text_input("Odpowiedzialny")
            tr = st.text_input("Termin")
        else:
            dz, kt, tr = "n/a", "n/a", "n/a"

        if st.form_submit_button("ZAPISZ DO BAZY", use_container_width=True):
            ap = get_vda_ap(s, o, d)
            conn = sqlite3.connect(DB_NAME)
            conn.execute("INSERT INTO wpisy (op_id, wada, skutek, s, przyczyna, prewencja, o, detekcja, d, ap, dzialanie, kto, termin) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", 
                         (op_id, wada, skutek, s, prz, pre, o, det, d, ap, dz, kt, tr))
            conn.commit(); conn.close(); st.rerun()

@st.dialog("📝 Edytuj wpis", width="large")
def modal_edycja_wpisu(row):
    st.write(f"Edycja dla: **{row['nazwa']}**")
    has_actions = row['dzialanie'] != "n/a"
    show_actions = st.toggle("Edytuj zalecane działania", value=has_actions)
    
    with st.form("fm_edit"):
        # Układ pionowy - boxy po kolei od góry do dołu
        wada = st.text_input("Rodzaj błędu", value=row['wada'])
        skutek = st.text_input("Skutek błędu", value=row['skutek'])
        prz = st.text_input("Przyczyna", value=row['przyczyna'])
        pre = st.text_area("Prewencja", value=row['prewencja'], height=68)
        det = st.text_area("Wykrywanie", value=row['detekcja'], height=68)
        
        st.markdown("---")
        st.subheader("Ocena Ryzyka (S, O, D)")
        s = st.select_slider("Znaczenie (S) ", options=range(1, 11), value=row['s'])
        o = st.select_slider("Występowanie (O) ", options=range(1, 11), value=row['o'])
        d = st.select_slider("Wykrywalność (D) ", options=range(1, 11), value=row['d'])
        
        if show_actions:
            st.markdown("---")
            st.subheader("Plan Działań")
            dz = st.text_input("Zalecane działania", value=row['dzialanie'] if row['dzialanie'] != "n/a" else "")
            kt = st.text_input("Odpowiedzialny", value=row['kto'] if row['kto'] != "n/a" else "")
            tr = st.text_input("Termin", value=row['termin'] if row['termin'] != "n/a" else "")
        else:
            dz, kt, tr = "n/a", "n/a", "n/a"

        if st.form_submit_button("ZAKTUALIZUJ WPIS", use_container_width=True):
            ap = get_vda_ap(s, o, d)
            conn = sqlite3.connect(DB_NAME)
            conn.execute("""UPDATE wpisy SET wada=?, skutek=?, s=?, przyczyna=?, prewencja=?, o=?, 
                            detekcja=?, d=?, ap=?, dzialanie=?, kto=?, termin=? WHERE id=?""", 
                         (wada, skutek, s, prz, pre, o, det, d, ap, dz, kt, tr, row['id']))
            conn.commit(); conn.close(); st.rerun()
            
@st.dialog("👤 Edytuj użytkownika")
def modal_edit_user(u_data):
    with st.form("edit_user_form"):
        new_name = st.text_input("Nazwa użytkownika", value=u_data['username'])
        new_pass = st.text_input("Nowe hasło (zostaw puste, by nie zmieniać)", type="password")
        new_role = st.selectbox("Rola", ["user", "admin"], index=0 if u_data['role'] == "user" else 1)
        
        if st.form_submit_button("ZAPISZ ZMIANY", use_container_width=True):
            conn = sqlite3.connect(DB_NAME)
            if new_pass:
                hp = hashlib.sha256(new_pass.encode()).hexdigest()
                conn.execute("UPDATE users SET username=?, password=?, role=? WHERE username=?", 
                             (new_name, hp, new_role, u_data['username']))
            else:
                conn.execute("UPDATE users SET username=?, role=? WHERE username=?", 
                             (new_name, new_role, u_data['username']))
            conn.commit(); conn.close()
            st.success("Zaktualizowano!"); st.rerun()


# --- SIDEBAR ---
with st.sidebar:
    st.write(f"👤 {st.session_state.user}")
    if st.button("WYLOGUJ"): st.session_state.auth = False; st.rerun()
    st.divider()
    conn = sqlite3.connect(DB_NAME); p_df = pd.read_sql("SELECT * FROM projekty", conn); conn.close()
    sel_p = st.selectbox("Projekt:", ["DASHBOARD"] + p_df['nazwa'].tolist())

# --- DASHBOARD ---
if sel_p == "DASHBOARD":
    st.markdown("<div class='main-logo'><h1>FMEA</h1>DASHBOARD</div>", unsafe_allow_html=True)
    
    if st.session_state.role == "admin":
        t1, t2 = st.tabs(["📁 PROJEKTY", "👥 UŻYTKOWNICY"])
        
        with t1:
            # Górna belka dodawania
            c_p1, c_p2 = st.columns([4, 1])
            np = c_p1.text_input("Nazwa projektu", label_visibility="collapsed", placeholder="Nazwa nowego projektu...")
            if c_p2.button("UTWÓRZ", use_container_width=True):
                if np:
                    conn = sqlite3.connect(DB_NAME)
                    conn.execute("INSERT INTO projekty (nazwa) VALUES (?)", (np,))
                    conn.commit(); conn.close(); st.rerun()
            
            st.divider()
            # Lista projektów
            for _, rp in p_df.iterrows():
                r_p = st.columns([4, 1])
                r_p[0].write(f"📂 **{rp['nazwa']}**")
                if r_p[1].button("USUŃ", key=f"delp_{rp['id']}", use_container_width=True):
                    conn = sqlite3.connect(DB_NAME)
                    conn.execute("DELETE FROM projekty WHERE id=?", (rp['id'],))
                    conn.execute("DELETE FROM operacje WHERE p_id=?", (rp['id'],))
                    conn.commit(); conn.close(); st.rerun()

        with t2:
            # Górna belka dodawania użytkownika
            c_u1, c_u2, c_u3 = st.columns([2, 2, 1])
            nu = c_u1.text_input("Login", label_visibility="collapsed", placeholder="Nowy login")
            nup = c_u2.text_input("Hasło", type="password", label_visibility="collapsed", placeholder="Hasło")
            if c_u3.button("DODAJ", use_container_width=True):
                if nu and nup:
                    nhp = hashlib.sha256(nup.encode()).hexdigest()
                    conn = sqlite3.connect(DB_NAME)
                    conn.execute("INSERT OR IGNORE INTO users VALUES (?,?,'user')", (nu, nhp))
                    conn.commit(); conn.close(); st.rerun()
            
            st.divider()
            
            conn = sqlite3.connect(DB_NAME)
            u_list = pd.read_sql("SELECT username, role FROM users", conn); conn.close()
            
            # Lista użytkowników - wyrównana
            for _, ru in u_list.iterrows():
                if ru['username'] != 'admin':
                    # Sztywne kolumny: nazwa (szeroka), ikony (wąskie)
                    r_u = st.columns([4, 0.4, 0.4])
                    r_u[0].write(f"👤 **{ru['username']}** — `{ru['role']}`")
                    
                    if r_u[1].button("📝", key=f"ed_u_{ru['username']}", use_container_width=True):
                        modal_edit_user(ru)
                    
                    if r_u[2].button("✖", key=f"de_u_{ru['username']}", use_container_width=True):
                        conn = sqlite3.connect(DB_NAME)
                        conn.execute("DELETE FROM users WHERE username=?", (ru['username'],))
                        conn.commit(); conn.close(); st.rerun()
# --- WIDOK PROJEKTU ---
else:
    p_id = p_df[p_df['nazwa'] == sel_p]['id'].values[0]
    
    ch1, ch2 = st.columns([4, 1])
    ch1.markdown(f"### 📑 PROJEKT: {sel_p}")
    
    conn = sqlite3.connect(DB_NAME)
    df_all = pd.read_sql(f"SELECT w.*, o.nazwa FROM wpisy w JOIN operacje o ON w.op_id = o.id WHERE o.p_id = {p_id}", conn)
    if not df_all.empty:
        pdf_b = generate_pdf(df_all, sel_p, st.session_state.user)
        ch2.download_button("📄 POBIERZ PDF", data=pdf_b, file_name=f"FMEA_{sel_p}.pdf", use_container_width=True)

    if st.session_state.role == "admin":
        with st.container(border=True):
            c_op1, c_op2 = st.columns([4, 1])
            new_op = c_op1.text_input("Krok procesu", label_visibility="collapsed", placeholder="Nowy krok...")
            if c_op2.button("✚ KROK") and new_op:
                conn.execute("INSERT INTO operacje (p_id, nazwa) VALUES (?,?)", (int(p_id), new_op)); conn.commit(); st.rerun()

    st.divider()
    ops = pd.read_sql(f"SELECT * FROM operacje WHERE p_id={p_id}", conn); conn.close()
    
    for _, op in ops.iterrows():
        with st.expander(f"⚙️ {op['nazwa']}", expanded=True):
            cols_size = [1.2, 1.2, 0.4, 1.2, 1.2, 0.4, 1.2, 0.4, 0.5, 2.0, 1.2, 1.0, 0.6, 0.6]
            h = st.columns(cols_size)
            labels = ["Błąd", "Skutek", "S", "Przyczyna", "Prewencja", "O", "Wykrywanie", "D", "AP", "Zalecane działania", "Odpowiedzialny", "Termin", "", ""]
            for i, label in enumerate(labels):
                if label: h[i].caption(f"**{label}**")
            
            if st.session_state.role == "admin":
                if h[13].button("✚", key=f"add_{op['id']}"): modal_wpis(op['id'], op['nazwa'])

            df_w = df_all[df_all['op_id'] == op['id']]
            for _, row in df_w.iterrows():
                r = st.columns(cols_size)
                r[0].write(row['wada']); r[1].write(row['skutek']); r[2].write(f"**{row['s']}**")
                r[3].write(row['przyczyna']); r[4].write(row['prewencja']); r[5].write(str(row['o']))
                r[6].write(row['detekcja']); r[7].write(str(row['d']))
                clr = "#ef4444" if row['ap'] == "H" else "#f59e0b" if row['ap'] == "M" else "#10b981"
                r[8].markdown(f"<p style='color:{clr}; font-weight:bold; margin:0;'>{row['ap']}</p>", unsafe_allow_html=True)
                r[9].write(row['dzialanie']); r[10].write(row['kto']); r[11].write(row['termin'])
                
                if st.session_state.role == "admin":
                    # --- EDYCJA ---
                    if r[12].button("📝", key=f"e_{row['id']}"): 
                        modal_edycja_wpisu(row)
                    # --- USUWANIE ---
                    if r[13].button("✖", key=f"d_{row['id']}"):

                        conn = sqlite3.connect(DB_NAME); conn.execute(f"DELETE FROM wpisy WHERE id={row['id']}"); conn.commit(); conn.close(); st.rerun()





