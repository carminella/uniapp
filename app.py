import streamlit as st
import requests
import time

API_URL = "https://uniapp-o6cv.onrender.com"

st.set_page_config(page_title="Uni Study Hub", page_icon="📚", layout="centered")

if "token" not in st.session_state:
    st.session_state.token = None
if "email" not in st.session_state:
    st.session_state.email = None

def get_headers():
    return {"Authorization": f"Bearer {st.session_state.token}"}

if not st.session_state.token:
    st.title("Uni Study Hub 📚")
    st.write("Il tuo spazio personale e protetto per gestire esami, appunti e focus.")
    
    choice = st.radio("Scegli un'opzione", ["Accedi", "Registrati", "Password dimenticata"])
    
    if choice == "Accedi":
        with st.form("login_form"):
            email = st.text_input("La tua Email")
            password = st.text_input("Password", type="password")
            submit_login = st.form_submit_button("Accedi")
            
            if submit_login:
                if email and password:
                    try:
                        res = requests.post(f"{API_URL}/token", data={"username": email, "password": password})
                        if res.status_code == 200:
                            data = res.json()
                            st.session_state.token = data["access_token"]
                            st.session_state.email = email
                            st.success("Login effettuato con successo! 🎉")
                            st.rerun()
                        else:
                            try:
                                error_detail = res.json().get("detail", "Email o password errati.")
                            except:
                                error_detail = f"Errore del server ({res.status_code}): {res.text}"
                            st.error(error_detail)
                    except requests.exceptions.ConnectionError:
                        st.error("Impossibile connettersi al server backend.")
                else:
                    st.warning("Compila tutti i campi.")
                    
    elif choice == "Registrati":
        with st.form("signup_form"):
            username = st.text_input("Scegli un Nome Utente")
            email = st.text_input("La tua Email")
            password = st.text_input("Scegli una Password", type="password")
            submit_signup = st.form_submit_button("Registrati")
            
            if submit_signup:
                if username and email and password:
                    try:
                        res = requests.post(f"{API_URL}/signup", data={"username": username, "email": email, "password": password})
                        if res.status_code == 200:
                            st.success("Registrazione completata! Ora seleziona 'Accedi' per entrare.")
                        else:
                            try:
                                error_detail = res.json().get("detail", "Errore durante la registrazione.")
                            except:
                                error_detail = f"Errore del server ({res.status_code}): {res.text}"
                            st.error(error_detail)
                    except requests.exceptions.ConnectionError:
                        st.error("Impossibile connettersi al server backend.")
                else:
                    st.warning("Compila tutti i campi.")
                    
    else:
        with st.form("reset_form"):
            st.write("Inserisci la tua email e imposta una nuova password.")
            email_reset = st.text_input("La tua Email")
            new_password = st.text_input("Nuova Password", type="password")
            submit_reset = st.form_submit_button("Reimposta Password")
            
            if submit_reset:
                if email_reset and new_password:
                    try:
                        res = requests.post(f"{API_URL}/reset-password", data={"email": email_reset, "new_password": new_password})
                        if res.status_code == 200:
                            st.success("Password reimpostata con successo! Ora seleziona 'Accedi' per entrare.")
                        else:
                            try:
                                error_detail = res.json().get("detail", "Errore durante il reset.")
                            except:
                                error_detail = f"Errore del server ({res.status_code}): {res.text}"
                            st.error(error_detail)
                    except requests.exceptions.ConnectionError:
                        st.error("Impossibile connettersi al server backend.")
                else:
                    st.warning("Compila tutti i campi.")

else:
    st.sidebar.write(f"📧 Email: **{st.session_state.email}**")
    if st.sidebar.button("Esci (Logout)"):
        st.session_state.token = None
        st.session_state.email = None
        st.rerun()

    st.sidebar.divider()
    st.sidebar.subheader("⚙️ Impostazioni Account")
    with st.sidebar.form("change_username_form"):
        new_username = st.text_input("Nuovo Nome Utente")
        submit_change = st.form_submit_button("Aggiorna Nome")
        if submit_change:
            if new_username:
                try:
                    res = requests.put(f"{API_URL}/user/update-username", data={"new_username": new_username}, headers=get_headers())
                    if res.status_code == 200:
                        st.sidebar.success("Nome utente aggiornato!")
                    else:
                        st.sidebar.error(res.json().get("detail", "Errore."))
                except:
                    st.sidebar.error("Errore di connessione.")
            else:
                st.sidebar.warning("Inserisci un nome.")

    st.title("Uni Study Hub 📚")
    st.write(f"Benvenuta nel tuo spazio protetto!")

    is_admin = st.session_state.email.lower() == "tua-email@admin.com"

    if is_admin:
        tab1, tab2, tab3, tab4 = st.tabs(["📚 Corsi & Appunti", "🍅 Pomodoro & Albero", "📊 Situazione Studio", "🔒 Pannello Admin"])
    else:
        tab1, tab2, tab3 = st.tabs(["📚 Corsi & Appunti", "🍅 Pomodoro & Albero", "📊 Situazione Studio"])

    with tab1:
        st.header("Gestione Materiali di Studio")
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Carica Appunti o Intera Cartella")
            with st.form("upload_form", clear_on_submit=True):
                course_name = st.text_input("Nome del Corso", placeholder="es. Sistemi Operativi")
                difficulty = st.slider("Livello di Difficoltà", 1, 5, 3)
                uploaded_files = st.file_uploader("Seleziona i file o l'intera cartella", accept_multiple_files=True)
                
                submitted = st.form_submit_button("Carica nel Database")
                if submitted:
                    if course_name and uploaded_files:
                        files_payload = [("files", (f.name, f.getvalue(), f.type)) for f in uploaded_files]
                        data = {"course_name": course_name, "difficulty_level": difficulty}
                        
                        try:
                            res = requests.post(f"{API_URL}/notes/upload-folder/", data=data, files=files_payload, headers=get_headers())
                            if res.status_code == 200:
                                st.success(f"Caricati con successo {len(uploaded_files)} file! 🎉")
                            else:
                                st.error("Errore durante il caricamento.")
                        except:
                            st.error("Impossibile connettersi al server backend.")
                    else:
                        st.warning("Inserisci il nome del corso e seleziona almeno un file.")

        with col2:
            st.subheader("I tuoi Corsi e Appunti")
            if st.button("Aggiorna Lista"):
                st.rerun()
                
            try:
                courses_res = requests.get(f"{API_URL}/courses/", headers=get_headers())
                notes_res = requests.get(f"{API_URL}/notes/", headers=get_headers())
                
                if courses_res.status_code == 200:
                    courses = courses_res.json()
                    notes = notes_res.json() if notes_res.status_code == 200 else []
                    
                    if not courses:
                        st.info("Nessun corso registrato.")
                    else:
                        for c in courses:
                            with st.expander(f"📖 {c['name']} (Stato: {c['status']})"):
                                course_notes = [n for n in notes if n['course_id'] == c['id']]
                                if course_notes:
                                    st.write("**Appunti caricati:**")
                                    for n in course_notes:
                                        st.markdown(f"- 📄 {n['title']} *(Difficoltà: {n['difficulty_level']}/5)*")
                                else:
                                    st.caption("Nessun appunto caricato per questo corso.")
            except:
                st.error("Impossibile caricare i dati dal server.")

    with tab2:
        st.header("Timer Pomodoro & Foresta del Focus 🌳")
        st.write("Scegli i tuoi intervalli, concentrati senza distrazioni e guarda crescere il tuo albero!")

        if "tree_stage" not in st.session_state:
            st.session_state.tree_stage = 0
        if "total_focus_minutes" not in st.session_state:
            st.session_state.total_focus_minutes = 0

        col_set1, col_set2 = st.columns(2)
        with col_set1:
            work_time = st.selectbox("Tempo di Lavoro (minuti)", [25, 30, 40, 50, 60], index=0)
        with col_set2:
            break_time = st.selectbox("Tempo di Pausa (minuti)", [5, 10], index=0)

        stages = ["🌱 Seme piantato", "🌿 Germoglio", "🌿 Pianta giovane", "🌳 Albero rigoglioso", "🌲🌳🌲 Piccola Foresta"]
        current_stage_text = stages[min(st.session_state.tree_stage, len(stages) - 1)]
        
        st.markdown(f"### Stato attuale: {current_stage_text}")
        st.metric("Minuti di Focus Totali", f"{st.session_state.total_focus_minutes} min")

        if st.button("🚀 Avvia Sessione Pomodoro"):
            st.info(f"Sessione di studio avviata per {work_time} minuti! Mettiti all'opera 💻🎧")
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            total_seconds = work_time * 60
            
            for current_second in range(total_seconds):
                time.sleep(1)
                percent = (current_second + 1) / total_seconds
                progress_bar.progress(min(percent, 1.0))
                
                seconds_left = total_seconds - (current_second + 1)
                mins_left = seconds_left // 60
                secs_left = seconds_left % 60
                
                status_text.text(f"⏱️ Tempo rimanente: {mins_left:02d}:{secs_left:02d} / {work_time}:00 min")
                
            status_text.text("Sessione completata con successo! 🎉")
            st.balloons()
            
            st.session_state.total_focus_minutes += work_time
            st.session_state.tree_stage += 1
            st.rerun()

        if st.button("🔄 Reset Albero"):
            st.session_state.tree_stage = 0
            st.session_state.total_focus_minutes = 0
            st.rerun()

        st.divider()
        st.markdown("### 🎧 Playlist di Sottofondo per lo Studio")
        music_link = st.text_input("Link YouTube della musica:", value="https://www.youtube.com/watch?v=O135u_19gO8&t=783s")
        if music_link:
            st.markdown(f"[🎵 Clicca qui per aprire la musica in una nuova scheda]({music_link})", unsafe_allow_html=True)

    with tab3:
        st.header("La Situazione del mio Studio 📊")
        try:
            courses_res = requests.get(f"{API_URL}/courses/", headers=get_headers())
            if courses_res.status_code == 200:
                courses = courses_res.json()
                if courses:
                    completed_count = sum(1 for c in courses if c['status'] == 'completato')
                    studying_count = sum(1 for c in courses if c['status'] == 'in studio')
                    
                    col_m1, col_m2 = st.columns(2)
                    col_m1.metric("Corsi in Studio", studying_count)
                    col_m2.metric("Corsi Superati", completed_count)
                    
                    st.divider()
                    st.subheader("Panoramica Materie")
                    for c in courses:
                        st.markdown(f"- **{c['name']}** — Stato attuale: `{c['status']}`")
                else:
                    st.info("Nessun corso inserito nel database.")
        except:
            st.error("Impossibile connettersi al backend.")

    if is_admin:
        with tab4:
            st.header("🔒 Pannello Admin - Utenti Registrati")
            if st.button("Aggiorna Lista Utenti"):
                st.rerun()
                
            try:
                users_res = requests.get(f"{API_URL}/users/", headers=get_headers())
                if users_res.status_code == 200:
                    users_list = users_res.json()
                    st.success(f"Totale utenti registrati: {len(users_list)}")
                    for u in users_list:
                        st.markdown(f"- 👤 **{u['username']}** — 📧 `{u['email']}`")
                else:
                    st.error("Errore nel recupero degli utenti.")
            except:
                st.error("Impossibile connettersi al server.")