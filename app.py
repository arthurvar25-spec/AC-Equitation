
import streamlit as st
import sqlite3
import hashlib
import secrets
from datetime import datetime, date, time, timedelta
from pathlib import Path

# =====================================================
# AC EQUITATION - APPLICATION DE GESTION DU CLUB
# =====================================================

st.set_page_config(
    page_title="AC Équitation",
    page_icon="🐴",
    layout="wide"
)

DB = "ac_equitation.db"
PHOTO_DIR = Path("photos")
PHOTO_DIR.mkdir(exist_ok=True)

st.markdown("""
<style>
.stApp { background-color: #F7F5EF; }
h1, h2, h3 { color: #536B58; }
.stButton button {
    background-color: #718873;
    color: white;
    border-radius: 10px;
    border: none;
}
.stButton button:hover {
    background-color: #536B58;
    color: white;
}
div[data-testid="stMetric"] {
    background: #EAEDE4;
    padding: 15px;
    border-radius: 12px;
}
</style>
""", unsafe_allow_html=True)


# ---------------- BASE DE DONNÉES ----------------

def db():
    return sqlite3.connect(DB, check_same_thread=False)


def init_db():
    con = db()
    cur = con.cursor()

    cur.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT,
        nom TEXT,
        email TEXT,
        telephone TEXT
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS children(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        parent_id INTEGER,
        prenom TEXT,
        nom TEXT,
        naissance TEXT,
        age INTEGER,
        poids REAL,
        taille REAL,
        galop TEXT,
        jour TEXT,
        heure TEXT,
        pony_id INTEGER,
        photo TEXT
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS ponies(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT,
        age INTEGER,
        description TEXT,
        photo TEXT
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS courses(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        jour TEXT,
        heure TEXT,
        discipline TEXT,
        niveau TEXT,
        coach TEXT,
        statut TEXT DEFAULT 'Prévu'
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS stages(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT,
        discipline TEXT,
        date_stage TEXT,
        horaire TEXT,
        niveau TEXT,
        places INTEGER,
        tarif REAL
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS stage_bookings(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        stage_id INTEGER,
        enfant TEXT,
        responsable TEXT,
        telephone TEXT,
        email TEXT
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS rides(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        enfant TEXT,
        responsable TEXT,
        telephone TEXT,
        email TEXT,
        date_ride TEXT,
        heure TEXT,
        tarif REAL,
        statut TEXT DEFAULT 'À confirmer'
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS absences(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        child_id INTEGER,
        course_id INTEGER,
        motif TEXT,
        demande TEXT,
        statut TEXT DEFAULT 'En attente'
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS dp_requests(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        child_id INTEGER,
        pony_id INTEGER,
        commentaire TEXT,
        statut TEXT DEFAULT 'En attente'
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS notifications(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        message TEXT,
        date_message TEXT,
        lu INTEGER DEFAULT 0
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS events(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT,
        description TEXT,
        date_event TEXT,
        tarif REAL
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS event_bookings(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id INTEGER,
        enfant TEXT,
        responsable TEXT,
        telephone TEXT,
        email TEXT
    )""")

    # Compte administrateur initial
    cur.execute("SELECT id FROM users WHERE role='admin'")
    if not cur.fetchone():
        cur.execute("""
            INSERT INTO users(username,password,role,nom)
            VALUES(?,?,?,?)
        """, (
            "admin",
            password_hash("AC2026!"),
            "admin",
            "Administrateur"
        ))

    con.commit()
    con.close()


def password_hash(password):
    salt = "AC_Equitation_Salt_2026"
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt.encode(),
        200000
    ).hex()


def query(sql, params=()):
    con = db()
    cur = con.cursor()
    cur.execute(sql, params)
    rows = cur.fetchall()
    con.commit()
    con.close()
    return rows


def execute(sql, params=()):
    con = db()
    cur = con.cursor()
    cur.execute(sql, params)
    con.commit()
    con.close()


def notify(user_id, message):
    execute("""
        INSERT INTO notifications(user_id,message,date_message)
        VALUES(?,?,?)
    """, (user_id, message, datetime.now().strftime("%d/%m/%Y %H:%M")))


def notify_all_families(message):
    families = query("SELECT id FROM users WHERE role='famille'")
    for family in families:
        notify(family[0], message)


def save_photo(uploaded, prefix):
    if uploaded is None:
        return ""
    filename = prefix + "_" + secrets.token_hex(5) + Path(uploaded.name).suffix
    path = PHOTO_DIR / filename
    path.write_bytes(uploaded.getvalue())
    return str(path)


init_db()


# ---------------- SESSION ----------------

if "user" not in st.session_state:
    st.session_state.user = None

if "page" not in st.session_state:
    st.session_state.page = "Accueil"


# ---------------- EN-TÊTE ----------------

st.markdown(
    "<h1 style='text-align:center;'>🐴 AC ÉQUITATION</h1>",
    unsafe_allow_html=True
)
st.markdown(
    "<p style='text-align:center;color:#718873;'>"
    "Le club, les familles et les poneys réunis"
    "</p>",
    unsafe_allow_html=True
)
st.divider()


# ---------------- OUTILS ----------------

def photo_display(path):
    if path and Path(path).exists():
        st.image(path, width=180)


def is_coach():
    return st.session_state.user and st.session_state.user["role"] in (
        "coach", "admin"
    )


def current_user_id():
    return st.session_state.user["id"]


def get_children(parent_id):
    return query(
        "SELECT id,prenom,nom,age,poids,taille,galop,jour,heure,pony_id,photo "
        "FROM children WHERE parent_id=?",
        (parent_id,)
    )


# ---------------- CONNEXION ----------------

def login_page():
    st.subheader("Connexion")

    tab1, tab2 = st.tabs(["Se connecter", "Créer un compte famille"])

    with tab1:
        username = st.text_input("Identifiant", key="login_user")
        password = st.text_input(
            "Mot de passe",
            type="password",
            key="login_password"
        )

        if st.button("Connexion"):
            users = query(
                "SELECT id,username,password,role,nom,email,telephone "
                "FROM users WHERE username=?",
                (username,)
            )

            if users and users[0][2] == password_hash(password):
                u = users[0]
                st.session_state.user = {
                    "id": u[0],
                    "username": u[1],
                    "role": u[3],
                    "nom": u[4],
                    "email": u[5],
                    "telephone": u[6]
                }
                st.success("Connexion réussie !")
                st.rerun()
            else:
                st.error("Identifiant ou mot de passe incorrect.")

    with tab2:
        st.write("Créez un compte pour gérer tous vos enfants avec un seul identifiant.")

        nom = st.text_input("Nom du responsable", key="signup_nom")
        prenom = st.text_input("Prénom du responsable", key="signup_prenom")
        email = st.text_input("Adresse e-mail", key="signup_email")
        telephone = st.text_input("Numéro de téléphone", key="signup_tel")
        username = st.text_input("Choisissez un identifiant", key="signup_user")
        password = st.text_input(
            "Choisissez un mot de passe",
            type="password",
            key="signup_password"
        )
        confirm = st.text_input(
            "Confirmez le mot de passe",
            type="password",
            key="signup_confirm"
        )

        if st.button("Créer mon compte"):
            if not all([nom, prenom, email, telephone, username, password]):
                st.error("Merci de remplir tous les champs.")
            elif password != confirm:
                st.error("Les mots de passe ne correspondent pas.")
            elif len(password) < 10:
                st.error("Choisissez un mot de passe d'au moins 10 caractères.")
            else:
                try:
                    execute("""
                        INSERT INTO users(username,password,role,nom,email,telephone)
                        VALUES(?,?,?,?,?,?)
                    """, (
                        username,
                        password_hash(password),
                        "famille",
                        prenom + " " + nom,
                        email,
                        telephone
                    ))
                    st.success("Compte créé ! Vous pouvez vous connecter.")
                except sqlite3.IntegrityError:
                    st.error("Cet identifiant est déjà utilisé.")


# ---------------- ESPACE PUBLIC ----------------

def public_page():
    st.subheader("Bienvenue au club !")

    st.write(
        "Retrouvez les informations du club, nos poneys, "
        "nos stages et nos animations."
    )

    tabs = st.tabs([
        "Le club",
        "Nos poneys",
        "Réserver une balade",
        "Stages",
        "Événements"
    ])

    with tabs[0]:
        st.write("Bienvenue à AC Équitation !")
        st.info("Les informations et photos du club seront ajoutées ici par les coachs.")

    with tabs[1]:
        ponies = query("SELECT nom,age,description,photo FROM ponies")
        if not ponies:
            st.info("Les poneys seront bientôt présentés ici.")
        for p in ponies:
            with st.container(border=True):
                st.subheader(p[0])
                photo_display(p[3])
                st.write("Âge :", p[1] if p[1] is not None else "Non renseigné")
                st.write(p[2])

    with tabs[2]:
        st.write("Réservez une balade à poney.")
        tarif = st.number_input("Tarif de la balade (€)", min_value=0.0, value=10.0)
        enfant = st.text_input("Prénom et nom de l'enfant", key="ride_enfant")
        responsable = st.text_input("Prénom et nom du responsable", key="ride_parent")
        tel = st.text_input("Numéro de téléphone", key="ride_tel")
        email = st.text_input("Adresse e-mail", key="ride_email")
        jour = st.date_input("Date souhaitée", min_value=date.today())
        heure = st.time_input("Heure souhaitée", value=time(14, 0))

        if st.button("Envoyer ma réservation"):
            if all([enfant, responsable, tel, email]):
                execute("""
                    INSERT INTO rides(enfant,responsable,telephone,email,date_ride,heure,tarif)
                    VALUES(?,?,?,?,?,?,?)
                """, (
                    enfant, responsable, tel, email,
                    str(jour), str(heure), tarif
                ))
                st.success("Demande envoyée ! Le club doit confirmer la réservation.")
            else:
                st.error("Remplissez tous les champs.")

    with tabs[3]:
        stages = query("""
            SELECT id,nom,discipline,date_stage,horaire,niveau,places,tarif
            FROM stages ORDER BY date_stage
        """)
        for s in stages:
            with st.container(border=True):
                st.subheader(s[1])
                st.write("Discipline :", s[2])
                st.write("Date :", s[3])
                st.write("Horaires :", s[4])
                st.write("Niveau minimum :", s[5])
                st.write("Places proposées :", s[6])
                st.write("Tarif :", s[7], "€")

                with st.form("stage_" + str(s[0])):
                    enfant = st.text_input("Prénom et nom de l'enfant")
                    responsable = st.text_input("Prénom et nom du responsable")
                    tel = st.text_input("Téléphone")
                    email = st.text_input("E-mail")
                    submit = st.form_submit_button("S'inscrire au stage")

                    if submit:
                        if all([enfant, responsable, tel, email]):
                            execute("""
                                INSERT INTO stage_bookings(stage_id,enfant,responsable,telephone,email)
                                VALUES(?,?,?,?,?)
                            """, (s[0], enfant, responsable, tel, email))
                            st.success("Demande d'inscription envoyée.")
                        else:
                            st.error("Merci de remplir tous les champs.")

    with tabs[4]:
        events = query("SELECT id,nom,description,date_event,tarif FROM events")
        for e in events:
            with st.container(border=True):
                st.subheader(e[1])
                st.write(e[2])
                st.write("Date :", e[3])
                st.write("Tarif :", e[4], "€")

                with st.form("event_" + str(e[0])):
                    enfant = st.text_input("Nom de l'enfant")
                    responsable = st.text_input("Nom du responsable")
                    tel = st.text_input("Téléphone")
                    email = st.text_input("E-mail")
                    submit = st.form_submit_button("Réserver")

                    if submit:
                        if all([enfant, responsable, tel, email]):
                            execute("""
                                INSERT INTO event_bookings(event_id,enfant,responsable,telephone,email)
                                VALUES(?,?,?,?,?)
                            """, (e[0], enfant, responsable, tel, email))
                            st.success("Demande envoyée.")
                        else:
                            st.error("Remplissez tous les champs.")


# ---------------- ESPACE FAMILLE ----------------

def family_page():
    uid = current_user_id()
    st.subheader("Mon espace famille")

    tabs = st.tabs([
        "Mes enfants",
        "Ajouter un enfant",
        "Mes cours",
        "Absences et rattrapages",
        "Demander une DP",
        "Mes notifications"
    ])

    with tabs[0]:
        children = get_children(uid)
        if not children:
            st.info("Ajoutez votre premier enfant.")
        for c in children:
            with st.container(border=True):
                st.subheader(c[1] + " " + c[2])
                photo_display(c[10])
                st.write("Âge :", c[3])
                st.write("Poids :", c[4], "kg")
                st.write("Taille :", c[5], "cm")
                st.write("Galop :", c[6])
                st.write("Jour :", c[7])
                st.write("Heure :", c[8])
                pony = query("SELECT nom FROM ponies WHERE id=?", (c[9],)) if c[9] else []
                st.write("Poney attribué :", pony[0][0] if pony else "Pas encore attribué")

    with tabs[1]:
        st.write("Les parents peuvent ajouter plusieurs enfants au même compte.")
        prenom = st.text_input("Prénom de l'enfant")
        nom = st.text_input("Nom de l'enfant")
        naissance = st.date_input("Date de naissance", value=date(2015, 1, 1))
        age = st.number_input("Âge", min_value=2, max_value=25, value=10)
        poids = st.number_input("Poids (kg)", min_value=0.0, value=30.0)
        taille = st.number_input("Taille (cm)", min_value=0.0, value=130.0)
        galop = st.selectbox("Niveau / Galop", [
            "Débutant", "Galop 1", "Galop 2", "Galop 3",
            "Galop 4", "Galop 5", "Galop 6", "Galop 7"
        ])
        photo = st.file_uploader("Photo de l'enfant", type=["png", "jpg", "jpeg"])

        if st.button("Ajouter cet enfant"):
            if prenom and nom:
                path = save_photo(photo, "enfant")
                execute("""
                    INSERT INTO children(parent_id,prenom,nom,naissance,age,poids,taille,galop,photo)
                    VALUES(?,?,?,?,?,?,?,?,?)
                """, (
                    uid, prenom, nom, str(naissance), age,
                    poids, taille, galop, path
                ))
                st.success("Enfant ajouté !")
                st.rerun()
            else:
                st.error("Indiquez le prénom et le nom.")

    with tabs[2]:
        children = get_children(uid)
        for c in children:
            st.markdown("### " + c[1])
            courses = query("""
                SELECT jour,heure,discipline,niveau,coach,statut
                FROM courses ORDER BY jour,heure
            """)
            for course in courses:
                st.write(
                    course[0], "-", course[1], "|",
                    course[2], "|", course[3],
                    "| Coach :", course[4], "|", course[5]
                )

    with tabs[3]:
        children = get_children(uid)
        if children:
            choix = st.selectbox(
                "Enfant concerné",
                children,
                format_func=lambda x: x[1] + " " + x[2]
            )
            courses = query("SELECT id,jour,heure,discipline FROM courses")
            if courses:
                cours = st.selectbox(
                    "Cours concerné",
                    courses,
                    format_func=lambda x: x[1] + " " + x[2] + " - " + x[3]
                )
                motif = st.text_area("Motif de l'absence")
                if st.button("Demander une absence / un rattrapage"):
                    try:
                        date_cours = datetime.strptime(
                            cours[1] + " " + cours[2],
                            "%Y-%m-%d %H:%M:%S"
                        )
                        if date_cours - datetime.now() < timedelta(hours=24):
                            st.error("La demande doit être faite au moins 24 h avant le cours.")
                        else:
                            execute("""
                                INSERT INTO absences(child_id,course_id,motif,demande)
                                VALUES(?,?,?,?)
                            """, (
                                choix[0], cours[0], motif,
                                "Absence et demande de rattrapage"
                            ))
                            st.success("Demande transmise aux coachs.")
                    except ValueError:
                        st.error("Le format de l'horaire du cours doit être vérifié.")
            else:
                st.info("Aucun cours n'est encore enregistré.")
        else:
            st.info("Ajoutez d'abord un enfant.")

    with tabs[4]:
        children = get_children(uid)
        ponies = query("SELECT id,nom FROM ponies")
        if children and ponies:
            enfant = st.selectbox(
                "Enfant",
                children,
                format_func=lambda x: x[1] + " " + x[2],
                key="dp_child"
            )
            poney = st.selectbox(
                "Poney souhaité",
                ponies,
                format_func=lambda x: x[1]
            )
            commentaire = st.text_area("Votre demande")
            if st.button("Envoyer ma demande de DP"):
                execute("""
                    INSERT INTO dp_requests(child_id,pony_id,commentaire)
                    VALUES(?,?,?)
                """, (enfant[0], poney[0], commentaire))
                st.success("Demande envoyée aux coachs.")
        else:
            st.info("Il faut au moins un enfant et un poney enregistré.")

    with tabs[5]:
        messages = query("""
            SELECT id,message,date_message,lu FROM notifications
            WHERE user_id=? ORDER BY id DESC
        """, (uid,))
        if not messages:
            st.info("Vous n'avez pas encore de notification.")
        for m in messages:
            st.write(("🔔 " if not m[3] else "✓ ") + m[2] + " : " + m[1])
            if not m[3]:
                if st.button("Marquer comme lu", key="read_" + str(m[0])):
                    execute("UPDATE notifications SET lu=1 WHERE id=?", (m[0],))
                    st.rerun()


# ---------------- ESPACE COACHS / ADMIN ----------------

def coach_page():
    st.subheader("Espace coachs")

    tabs = st.tabs([
        "Tableau de bord",
        "Élèves",
        "Poneys",
        "Planning",
        "Stages",
        "Événements",
        "Balades",
        "Absences",
        "DP",
        "Comptes coachs"
    ])

    with tabs[0]:
        families = query("SELECT COUNT(*) FROM users WHERE role='famille'")[0][0]
        students = query("SELECT COUNT(*) FROM children")[0][0]
        ponies = query("SELECT COUNT(*) FROM ponies")[0][0]
        courses = query("SELECT COUNT(*) FROM courses")[0][0]

        a, b, c, d = st.columns(4)
        a.metric("Familles", families)
        b.metric("Élèves", students)
        c.metric("Poneys", ponies)
        d.metric("Cours", courses)

    with tabs[1]:
        st.write("### Élèves inscrits")
        children = query("""
            SELECT children.id,children.prenom,children.nom,children.age,
            children.galop,users.nom,children.pony_id
            FROM children LEFT JOIN users ON children.parent_id=users.id
        """)
        for c in children:
            pony = query("SELECT nom FROM ponies WHERE id=?", (c[6],)) if c[6] else []
            st.write(
                c[1], c[2], "|", c[3], "ans |", c[4],
                "| Responsable :", c[5],
                "| Poney :", pony[0][0] if pony else "Non attribué"
            )

        st.divider()
        st.write("### Ajouter un élève temporaire")
        prenom = st.text_input("Prénom", key="temp_prenom")
        nom = st.text_input("Nom", key="temp_nom")
        age = st.number_input("Âge", min_value=2, max_value=25, value=10, key="temp_age")
        responsable = st.text_input("Responsable", key="temp_parent")
        telephone = st.text_input("Téléphone", key="temp_tel")

        if st.button("Ajouter l'élève temporaire"):
            if prenom and nom:
                # Élève temporaire enregistré dans un compte spécial
                temp = query("SELECT id FROM users WHERE username='eleves_temporaires'")
                if not temp:
                    execute("""
                        INSERT INTO users(username,password,role,nom)
                        VALUES(?,?,?,?)
                    """, (
                        "eleves_temporaires",
                        password_hash(secrets.token_urlsafe(20)),
                        "temporaire",
                        "Élèves temporaires"
                    ))
                    temp = query("SELECT id FROM users WHERE username='eleves_temporaires'")
                execute("""
                    INSERT INTO children(parent_id,prenom,nom,age)
                    VALUES(?,?,?,?)
                """, (temp[0][0], prenom, nom, age))
                st.success("Élève temporaire ajouté.")
            else:
                st.error("Prénom et nom obligatoires.")

        st.divider()
        st.write("### Attribuer un poney à un enfant")
        all_children = query("SELECT id,prenom,nom FROM children")
        all_ponies = query("SELECT id,nom FROM ponies")
        if all_children and all_ponies:
            child = st.selectbox(
                "Choisir un enfant",
                all_children,
                format_func=lambda x: x[1] + " " + x[2],
                key="assign_child"
            )
            pony = st.selectbox(
                "Choisir un poney",
                all_ponies,
                format_func=lambda x: x[1],
                key="assign_pony"
            )
            if st.button("Valider l'attribution"):
                execute(
                    "UPDATE children SET pony_id=? WHERE id=?",
                    (pony[0], child[0])
                )
                st.success("Poney attribué.")
                st.rerun()

    with tabs[2]:
        st.write("### Ajouter un poney")
        nom = st.text_input("Nom du poney")
        age = st.number_input("Âge du poney", min_value=0, max_value=40, value=10)
        description = st.text_area("Caractère et présentation")
        photo = st.file_uploader("Photo du poney", type=["png", "jpg", "jpeg"], key="pony_photo")

        if st.button("Ajouter le poney"):
            if nom:
                path = save_photo(photo, "poney")
                execute(
                    "INSERT INTO ponies(nom,age,description,photo) VALUES(?,?,?,?)",
                    (nom, age, description, path)
                )
                st.success("Poney ajouté.")
                st.rerun()

        st.divider()
        for p in query("SELECT id,nom,age,description,photo FROM ponies"):
            with st.container(border=True):
                st.subheader(p[1])
                photo_display(p[4])
                st.write("Âge :", p[2])
                st.write(p[3])
                if st.button("Supprimer " + p[1], key="delpony" + str(p[0])):
                    execute("DELETE FROM ponies WHERE id=?", (p[0],))
                    st.rerun()

    with tabs[3]:
        st.write("### Planning hebdomadaire")
        st.caption("Les cours sont enregistrés chaque semaine avec un jour et une heure.")

        jours = [
            "Lundi", "Mardi", "Mercredi", "Jeudi",
            "Vendredi", "Samedi", "Dimanche"
        ]
        jour = st.selectbox("Jour", jours)
        heure = st.time_input("Heure du cours", value=time(14, 0))
        discipline = st.selectbox(
            "Discipline",
            ["Baby-poney", "Dressage", "Saut", "Obstacle",
             "Balade", "Travail à pied", "Autre"]
        )
        niveau = st.selectbox(
            "Niveau",
            ["Débutant", "Galop 1", "Galop 2", "Galop 3",
             "Galop 4", "Galop 5", "Galop 6", "Galop 7"]
        )
        coachs = query("SELECT nom FROM users WHERE role IN ('coach','admin')")
        coach = st.selectbox(
            "Coach",
            [x[0] for x in coachs] if coachs else ["À définir"]
        )

        if st.button("Ajouter le cours"):
            execute("""
                INSERT INTO courses(jour,heure,discipline,niveau,coach)
                VALUES(?,?,?,?,?)
            """, (jour, str(heure), discipline, niveau, coach))
            st.success("Cours ajouté au planning.")

        st.divider()
        st.write("### Cours de la semaine")
        for c in query("SELECT id,jour,heure,discipline,niveau,coach,statut FROM courses"):
            with st.container(border=True):
                st.write(
                    c[1], c[2], "|", c[3], "|", c[4],
                    "| Coach :", c[5], "|", c[6]
                )
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Annuler le cours", key="cancel" + str(c[0])):
                        execute(
                            "UPDATE courses SET statut='Annulé' WHERE id=?",
                            (c[0],)
                        )
                        notify_all_families(
                            "Un cours a été annulé : " + c[1] + " à " + c[2]
                        )
                        st.rerun()
                with col2:
                    if st.button("Déplacer le cours", key="move" + str(c[0])):
                        st.session_state["move_course"] = c[0]

                if st.session_state.get("move_course") == c[0]:
                    new_day = st.selectbox(
                        "Nouveau jour",
                        jours,
                        key="newday" + str(c[0])
                    )
                    new_hour = st.time_input(
                        "Nouvelle heure",
                        value=time(15, 0),
                        key="newhour" + str(c[0])
                    )
                    if st.button("Confirmer le déplacement", key="confirmmove" + str(c[0])):
                        execute("""
                            UPDATE courses SET jour=?,heure=?,statut='Déplacé'
                            WHERE id=?
                        """, (new_day, str(new_hour), c[0]))
                        notify_all_families(
                            "Un cours a été déplacé au " + new_day + " à " + str(new_hour)
                        )
                        del st.session_state["move_course"]
                        st.rerun()

    with tabs[4]:
        st.write("### Créer un stage")
        nom = st.text_input("Nom du stage")
        discipline = st.selectbox(
            "Discipline du stage",
            ["Dressage", "Saut", "Baby-poney", "Équifun",
             "Travail à pied", "Balade", "Autre"]
        )
        date_stage = st.date_input("Date du stage", min_value=date.today())
        horaire = st.text_input("Horaire", placeholder="Ex : 9h - 17h")
        niveau = st.selectbox(
            "Niveau minimum",
            ["Tous niveaux", "Débutant", "Galop 1", "Galop 2",
             "Galop 3", "Galop 4", "Galop 5"]
        )
        places = st.number_input("Nombre de places", min_value=1, value=8)
        tarif = st.number_input("Tarif (€)", min_value=0.0, value=30.0)

        if st.button("Publier le stage"):
            if nom and horaire:
                execute("""
                    INSERT INTO stages(nom,discipline,date_stage,horaire,niveau,places,tarif)
                    VALUES(?,?,?,?,?,?,?)
                """, (
                    nom, discipline, str(date_stage), horaire,
                    niveau, places, tarif
                ))
                notify_all_families("Nouveau stage disponible : " + nom)
                st.success("Stage publié.")
                st.rerun()

        st.divider()
        st.write("### Inscriptions aux stages")
        bookings = query("""
            SELECT stage_bookings.id,stages.nom,stage_bookings.enfant,
            stage_bookings.responsable,stage_bookings.telephone,
            stage_bookings.email
            FROM stage_bookings
            JOIN stages ON stages.id=stage_bookings.stage_id
        """)
        for b in bookings:
            st.write(b[1], "|", b[2], "| Responsable :", b[3], "|", b[4], "|", b[5])

    with tabs[5]:
        st.write("### Ajouter un événement ou un concours")
        nom = st.text_input("Nom de l'événement")
        description = st.text_area("Description")
        date_event = st.date_input("Date de l'événement", key="event_date")
        tarif = st.number_input("Tarif de l'événement (€)", min_value=0.0, value=0.0)

        if st.button("Publier l'événement"):
            if nom:
                execute("""
                    INSERT INTO events(nom,description,date_event,tarif)
                    VALUES(?,?,?,?)
                """, (nom, description, str(date_event), tarif))
                notify_all_families("Nouvel événement : " + nom)
                st.success("Événement publié.")
                st.rerun()

        st.divider()
        for e in query("SELECT id,nom,description,date_event,tarif FROM events"):
            st.write(e[1], "|", e[3], "|", e[4], "€")
            st.write(e[2])

        st.write("### Inscriptions aux événements")
        for b in query("""
            SELECT events.nom,event_bookings.enfant,
            event_bookings.responsable,event_bookings.telephone,
            event_bookings.email
            FROM event_bookings JOIN events ON events.id=event_bookings.event_id
        """):
            st.write(b)

    with tabs[6]:
        st.write("### Réservations de balades")
        rides = query("""
            SELECT id,enfant,responsable,telephone,email,date_ride,heure,tarif,statut
            FROM rides ORDER BY date_ride
        """)
        for r in rides:
            with st.container(border=True):
                st.write(
                    r[1], "| Responsable :", r[2],
                    "| Téléphone :", r[3],
                    "| E-mail :", r[4]
                )
                st.write(r[5], r[6], "|", r[7], "€ |", r[8])
                statut = st.selectbox(
                    "Statut",
                    ["À confirmer", "Confirmée", "Refusée"],
                    index=["À confirmer", "Confirmée", "Refusée"].index(r[8]),
                    key="ride_status" + str(r[0])
                )
                if st.button("Enregistrer le statut", key="ride_save" + str(r[0])):
                    execute("UPDATE rides SET statut=? WHERE id=?", (statut, r[0]))
                    st.success("Statut enregistré.")
                    st.rerun()

    with tabs[7]:
        st.write("### Demandes d'absence et de rattrapage")
        absences = query("""
            SELECT absences.id,children.prenom,children.nom,
            absences.motif,absences.demande,absences.statut,children.parent_id
            FROM absences JOIN children ON children.id=absences.child_id
        """)
        for a in absences:
            with st.container(border=True):
                st.write(a[1], a[2], "|", a[4], "|", a[3], "|", a[5])
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Accepter", key="accept_abs" + str(a[0])):
                        execute(
                            "UPDATE absences SET statut='Acceptée' WHERE id=?",
                            (a[0],)
                        )
                        notify(a[6], "Votre demande d'absence a été acceptée.")
                        st.rerun()
                with col2:
                    if st.button("Refuser", key="refuse_abs" + str(a[0])):
                        execute(
                            "UPDATE absences SET statut='Refusée' WHERE id=?",
                            (a[0],)
                        )
                        notify(a[6], "Votre demande d'absence a été refusée.")
                        st.rerun()

    with tabs[8]:
        st.write("### Demandes de demi-pension")
        requests = query("""
            SELECT dp_requests.id,children.prenom,children.nom,
            ponies.nom,dp_requests.commentaire,dp_requests.statut,
            children.parent_id,children.id,dp_requests.pony_id
            FROM dp_requests
            JOIN children ON children.id=dp_requests.child_id
            JOIN ponies ON ponies.id=dp_requests.pony_id
        """)
        for r in requests:
            with st.container(border=True):
                st.write(r[1], r[2], "| Poney :", r[3])
                st.write(r[4], "|", r[5])
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Accepter la DP", key="dpaccept" + str(r[0])):
                        execute(
                            "UPDATE dp_requests SET statut='Acceptée' WHERE id=?",
                            (r[0],)
                        )
                        execute(
                            "UPDATE children SET pony_id=? WHERE id=?",
                            (r[8], r[7])
                        )
                        # Trois cours DP sont ajoutés au planning
                        for j in ["Mercredi", "Samedi", "Dimanche"]:
                            execute("""
                                INSERT INTO courses(jour,heure,discipline,niveau,coach,statut)
                                VALUES(?,?,?,?,?,'Prévu')
                            """, (
                                j, "10:00:00",
                                "DP - " + r[3],
                                "À définir",
                                "À attribuer"
                            ))
                        notify(r[6], "Votre demande de DP a été acceptée.")
                        st.rerun()
                with col2:
                    if st.button("Refuser la DP", key="dprefuse" + str(r[0])):
                        execute(
                            "UPDATE dp_requests SET statut='Refusée' WHERE id=?",
                            (r[0],)
                        )
                        notify(r[6], "Votre demande de DP a été refusée.")
                        st.rerun()

    with tabs[9]:
        if st.session_state.user["role"] != "admin":
            st.info("Seul l'administrateur peut créer les comptes coachs.")
        else:
            st.write("### Gestion des comptes coachs")
            coachs = query("SELECT id,username,nom FROM users WHERE role='coach'")
            st.write("Nombre de coachs :", len(coachs), "/ 2")
            for c in coachs:
                st.write(c[2], "-", c[1])

            if len(coachs) < 2:
                nom = st.text_input("Nom du coach")
                username = st.text_input("Identifiant du coach")
                password = st.text_input("Mot de passe du coach", type="password")
                if st.button("Créer le compte coach"):
                    if nom and username and len(password) >= 10:
                        try:
                            execute("""
                                INSERT INTO users(username,password,role,nom)
                                VALUES(?,?,?,?)
                            """, (
                                username,
                                password_hash(password),
                                "coach",
                                nom
                            ))
                            st.success("Compte coach créé.")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("Identifiant déjà utilisé.")
                    else:
                        st.error("Remplissez les champs et utilisez un mot de passe de 10 caractères minimum.")


# ---------------- NAVIGATION ----------------

with st.sidebar:
    st.title("🐴 AC Équitation")

    if st.session_state.user:
        st.success("Connecté : " + st.session_state.user["nom"])
        role = st.session_state.user["role"]

        if role == "famille":
            page = st.radio(
                "Navigation",
                ["Mon espace famille", "Déconnexion"]
            )
        else:
            page = st.radio(
                "Navigation",
                ["Espace coachs", "Déconnexion"]
            )

        if page == "Déconnexion":
            st.session_state.user = None
            st.rerun()

    else:
        page = st.radio(
            "Navigation",
            ["Accueil", "Connexion"]
        )

    st.divider()
    st.caption("AC Équitation • Espace club")


if not st.session_state.user:
    if page == "Accueil":
        public_page()
    else:
        login_page()

elif st.session_state.user["role"] == "famille":
    family_page()

else:
    coach_page()

st.divider()
st.caption("© AC Équitation - Application de gestion du club")
