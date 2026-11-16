
import streamlit as st
import sqlite3
import hashlib
import secrets
import json
from datetime import date, datetime, timedelta

# =========================================================
# AC EQUITATION - APPLICATION DU CLUB
# =========================================================

st.set_page_config(
    page_title="AC Équitation",
    page_icon="🐴",
    layout="wide"
)

DB = "ac_equitation.db"

# -------------------- DESIGN --------------------

st.markdown("""
<style>
.stApp {
    background-color: #f7f6f0;
}
h1, h2, h3 {
    color: #425747;
}
section[data-testid="stSidebar"] {
    background-color: #e9ede4;
}
div.stButton > button {
    background-color: #607a62;
    color: white;
    border-radius: 10px;
    border: none;
}
div.stButton > button:hover {
    background-color: #425747;
    color: white;
}
div[data-testid="stForm"] {
    background-color: white;
    padding: 18px;
    border-radius: 12px;
}
</style>
""", unsafe_allow_html=True)

# -------------------- BASE DE DONNEES --------------------

db = sqlite3.connect(DB, check_same_thread=False)
db.row_factory = sqlite3.Row


def execute(sql, values=()):
    cur = db.execute(sql, values)
    db.commit()
    return cur


def rows(sql, values=()):
    return db.execute(sql, values).fetchall()


def one(sql, values=()):
    return db.execute(sql, values).fetchone()


def init_db():
    tables = [
        """CREATE TABLE IF NOT EXISTS families (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT, email TEXT, telephone TEXT,
            username TEXT UNIQUE, password TEXT
        )""",
        
        """CREATE TABLE IF NOT EXISTS weekly_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            semaine_debut TEXT,
            child_id INTEGER,
            lesson_id INTEGER,
            pony_id INTEGER,
            UNIQUE(semaine_debut, child_id, lesson_id)
        )""",

        
        """CREATE TABLE IF NOT EXISTS weekly_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            semaine_debut TEXT,
            child_id INTEGER,
            pony_id INTEGER,
            lesson_id INTEGER,
            UNIQUE(semaine_debut, child_id, lesson_id)
        )""",
        
        """CREATE TABLE IF NOT EXISTS coaches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            nom TEXT
        )""",

        """CREATE TABLE IF NOT EXISTS children (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            family_id INTEGER,
            prenom TEXT,
            age INTEGER,
            galop TEXT,
            photo TEXT
        )""",

        """CREATE TABLE IF NOT EXISTS ponies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT,
            age INTEGER,
            description TEXT,
            photo TEXT,
            actif INTEGER DEFAULT 1
        )""",

        """CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jour TEXT,
            heure TEXT,
            duree INTEGER,
            niveau TEXT,
            places INTEGER
        )""",

        """CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            child_id INTEGER,
            pony_id INTEGER,
            lesson_id INTEGER
        )""",

        """CREATE TABLE IF NOT EXISTS dp_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            family_id INTEGER,
            child_id INTEGER,
            courses TEXT,
            poney_souhaite TEXT DEFAULT '',
            statut TEXT DEFAULT 'En attente'
        )""",# Ajouter la colonne du poney souhaité si elle n'existe pas
       
    """CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            family_id INTEGER,
            child_id INTEGER,
            type TEXT,
            details TEXT,
            created TEXT,
            statut TEXT DEFAULT 'En attente'
        )""",

        """CREATE TABLE IF NOT EXISTS lesson_changes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lesson_id INTEGER,
            date_cours TEXT,
            action TEXT,
            nouvelle_date TEXT,
            nouvelle_heure TEXT,
            message TEXT
        )""",

        """CREATE TABLE IF NOT EXISTS stages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT,
            discipline TEXT,
            date_stage TEXT,
            horaire TEXT,
            niveau TEXT,
            places INTEGER,
            tarif REAL
        )""",

        """CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT,
            date_event TEXT,
            description TEXT,
            tarif REAL
        )""",

        """CREATE TABLE IF NOT EXISTS registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            family_id INTEGER,
            child_id INTEGER,
            type TEXT,
            item_id INTEGER,
            statut TEXT DEFAULT 'Inscrit'
        )""",

        """CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titre TEXT,
            contenu TEXT,
            photo TEXT,
            date_post TEXT
        )""",

        """CREATE TABLE IF NOT EXISTS rides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom_responsable TEXT,
            telephone TEXT,
            email TEXT,
            prenom_enfant TEXT,
            date_balade TEXT,
            horaire TEXT,
            tarif REAL,
            statut TEXT DEFAULT 'En attente'
        )""",

        """CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            family_id INTEGER,
            message TEXT,
            date_creation TEXT
        )"""
    ]

    for table in tables:
        db.execute(table)
    # Attributions hebdomadaires des poneys et chevaux
    db.execute("""
        CREATE TABLE IF NOT EXISTS pony_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            child_id INTEGER,
            lesson_id INTEGER,
            pony_id INTEGER,
            semaine TEXT,
            UNIQUE(child_id, lesson_id, semaine)
        )
    """)
    db.commit()   
    # Vérifier la colonne du poney souhaité
    columns = [
        row[1] for row in db.execute(
            "PRAGMA table_info(dp_requests)"
        ).fetchall()
    ]

    if "poney_souhaite" not in columns:
        db.execute(
            "ALTER TABLE dp_requests ADD COLUMN poney_souhaite TEXT DEFAULT ''"
        )

    # Ajouter la date aux attributions des poneys
    assignment_columns = [
        row[1] for row in db.execute(
            "PRAGMA table_info(assignments)"
        ).fetchall()
    ]

    if "date_cours" not in assignment_columns:
        db.execute(
            "ALTER TABLE assignments ADD COLUMN date_cours TEXT"
        )

    db.commit()

init_db()

# -------------------- SECURITE --------------------

def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt.encode(),
        200000
    ).hex()
    return salt + "$" + digest


def check_password(password, stored):
    try:
        salt, digest = stored.split("$", 1)
        return secrets.compare_digest(
            hash_password(password, salt),
            stored
        )
    except Exception:
        return False


def coach_setup_code():
    try:
        return st.secrets["COACH_SETUP_CODE"]
    except Exception:
        return ""


def notify_family(family_id, message):
    execute(
        """INSERT INTO notifications
        (family_id, message, date_creation)
        VALUES (?, ?, ?)""",
        (family_id, message, datetime.now().strftime("%d/%m/%Y %H:%M"))
    )


def notify_all_families(message):
    for family in rows("SELECT id FROM families"):
        notify_family(family["id"], message)


# -------------------- SESSION --------------------

if "role" not in st.session_state:
    st.session_state.role = None

if "user_id" not in st.session_state:
    st.session_state.user_id = None

if "username" not in st.session_state:
    st.session_state.username = None


def logout():
    st.session_state.role = None
    st.session_state.user_id = None
    st.session_state.username = None
    st.rerun()


# -------------------- TITRE --------------------

st.title("🐴 AC ÉQUITATION")
st.caption("Le club, les cavaliers et les poneys réunis au même endroit.")

if st.session_state.role:
    st.sidebar.success(
        "Connecté : " + str(st.session_state.username)
    )
    if st.sidebar.button("Déconnexion"):
        logout()


# =========================================================
# ESPACE PUBLIC
# =========================================================

def public_page():

    menu = st.radio(
        "Navigation",
        [
            "Accueil",
            "Nos poneys",
            "Planning",
            "Stages",
            "Concours et événements",
            "Actualités",
            "Balades",
            "Connexion",
            "Créer un compte"
        ],
        horizontal=True
    )

    st.divider()

    # ---------------- ACCUEIL ----------------

    if menu == "Accueil":
        st.header("Bienvenue à AC Équitation")
        st.write(
            "Bienvenue sur l'espace en ligne du club. "
            "Retrouvez les informations, les poneys, "
            "les activités et les actualités."
        )

        a, b, c = st.columns(3)
        a.metric("Poneys", len(rows(
            "SELECT id FROM ponies WHERE actif=1"
        )))
        b.metric("Stages", len(rows("SELECT id FROM stages")))
        c.metric("Événements", len(rows("SELECT id FROM events")))

        st.subheader("Les dernières actualités")
        for post in rows(
            "SELECT * FROM posts ORDER BY id DESC LIMIT 5"
        ):
            with st.container(border=True):
                st.subheader(post["titre"])
                st.write(post["contenu"])
                if post["photo"]:
                    st.image(post["photo"], use_container_width=True)
                st.caption(post["date_post"])

    # ---------------- PONEYS ----------------

    elif menu == "Nos poneys":
        st.header("Nos poneys")
        ponies = rows(
            "SELECT * FROM ponies WHERE actif=1 ORDER BY nom"
        )

        if not ponies:
            st.info("Les fiches des poneys seront bientôt disponibles.")

        cols = st.columns(3)
        for i, pony in enumerate(ponies):
            with cols[i % 3]:
                with st.container(border=True):
                    st.subheader("🐴 " + pony["nom"])
                    if pony["photo"]:
                        st.image(pony["photo"], use_container_width=True)
                    st.write("Âge :", pony["age"] or "Non renseigné")
                    st.write(pony["description"] or "")

    # ---------------- PLANNING ----------------

    elif menu == "Planning":
        st.header("Planning hebdomadaire")
        lessons = rows(
            """SELECT * FROM lessons
            ORDER BY
            CASE jour
                WHEN 'Lundi' THEN 1
                WHEN 'Mardi' THEN 2
                WHEN 'Mercredi' THEN 3
                WHEN 'Jeudi' THEN 4
                WHEN 'Vendredi' THEN 5
                WHEN 'Samedi' THEN 6
                WHEN 'Dimanche' THEN 7
            END, heure"""
        )

        if not lessons:
            st.info("Le planning sera bientôt disponible.")
        for lesson in lessons:
            with st.container(border=True):
                st.write(
                    f"**{lesson['jour']} — {lesson['heure']}**"
                )
                st.write(
                    f"Niveau : {lesson['niveau']} | "
                    f"Durée : {lesson['duree']} min | "
                    f"Places : {lesson['places']}"
                )

    # ---------------- STAGES ----------------

    elif menu == "Stages":
        st.header("Stages")
        stages = rows("SELECT * FROM stages ORDER BY date_stage")

        if not stages:
            st.info("Aucun stage publié pour le moment.")

        for stage in stages:
            with st.container(border=True):
                st.subheader(stage["nom"])
                st.write("Discipline :", stage["discipline"])
                st.write("Date :", stage["date_stage"])
                st.write("Horaire :", stage["horaire"])
                st.write("Niveau minimum :", stage["niveau"])
                st.write("Places :", stage["places"])
                st.write("Tarif :", stage["tarif"], "€")

    # ---------------- EVENEMENTS ----------------

    elif menu == "Concours et événements":
        st.header("Concours et événements")

        events = rows(
            "SELECT * FROM events ORDER BY date_event"
        )

        if not events:
            st.info("Aucun événement publié pour le moment.")

        for event in events:
            with st.container(border=True):
                st.subheader(event["nom"])
                st.write("Date :", event["date_event"])
                st.write(event["description"])
                st.write("Tarif :", event["tarif"], "€")

    # ---------------- ACTUALITES ----------------

    elif menu == "Actualités":
        st.header("Les actualités du club")

        for post in rows(
            "SELECT * FROM posts ORDER BY id DESC"
        ):
            with st.container(border=True):
                st.subheader(post["titre"])
                st.caption(post["date_post"])
                st.write(post["contenu"])
                if post["photo"]:
                    st.image(post["photo"], use_container_width=True)

    # ---------------- BALADES ----------------

    elif menu == "Balades":
        st.header("Réserver une balade à poney")
        st.write("Remplissez le formulaire pour demander une réservation.")

        with st.form("public_ride"):
            nom = st.text_input("Nom du responsable")
            prenom = st.text_input("Prénom du responsable")
            enfant = st.text_input("Prénom de l'enfant")
            telephone = st.text_input("Numéro de téléphone")
            email = st.text_input("Adresse mail")
            jour = st.date_input("Date souhaitée", min_value=date.today())
            heure = st.selectbox(
                "Horaire souhaité",
                ["10h00", "11h00", "14h00", "15h00", "16h00"]
            )
            tarif = st.number_input("Tarif annoncé (€)", min_value=0.0)
            ok = st.form_submit_button("Envoyer la demande")

            if ok:
                if not all([nom, prenom, enfant, telephone, email]):
                    st.error("Merci de remplir tous les champs.")
                else:
                    execute(
                        """INSERT INTO rides
                        (nom_responsable, telephone, email,
                        prenom_enfant, date_balade, horaire, tarif)
                        VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (
                            nom + " " + prenom,
                            telephone,
                            email,
                            enfant,
                            str(jour),
                            heure,
                            tarif
                        )
                    )
                    st.success("Demande envoyée au club !")

    # ---------------- CONNEXION ----------------

    elif menu == "Connexion":
        st.header("Connexion")

        type_compte = st.radio(
            "Je suis :",
            ["Famille", "Coach"],
            horizontal=True
        )

        with st.form("login_form"):
            identifiant = st.text_input("Identifiant")
            password = st.text_input("Mot de passe", type="password")
            ok = st.form_submit_button("Se connecter")

            if ok:
                if type_compte == "Famille":
                    user = one(
                        "SELECT * FROM families WHERE username=?",
                        (identifiant.strip(),)
                    )
                    if user and check_password(password, user["password"]):
                        st.session_state.role = "family"
                        st.session_state.user_id = user["id"]
                        st.session_state.username = user["username"]
                        st.rerun()
                    else:
                        st.error("Identifiant ou mot de passe incorrect.")

                else:
                    user = one(
                        "SELECT * FROM coaches WHERE username=?",
                        (identifiant.strip(),)
                    )
                    if user and check_password(password, user["password"]):
                        st.session_state.role = "coach"
                        st.session_state.user_id = user["id"]
                        st.session_state.username = user["username"]
                        st.rerun()
                    else:
                        st.error("Identifiant ou mot de passe incorrect.")

    # ---------------- CREATION FAMILLE ----------------

    elif menu == "Créer un compte":
        st.header("Créer un compte famille")

        with st.form("family_register"):
            nom = st.text_input("Nom du responsable")
            email = st.text_input("Adresse mail")
            telephone = st.text_input("Numéro de téléphone")
            username = st.text_input("Choisir un identifiant")
            password = st.text_input("Choisir un mot de passe", type="password")
            confirm = st.text_input("Confirmer le mot de passe", type="password")
            ok = st.form_submit_button("Créer mon compte")

            if ok:
                if not all([nom, email, telephone, username, password]):
                    st.error("Tous les champs sont obligatoires.")
                elif len(password) < 8:
                    st.error("Le mot de passe doit contenir au moins 8 caractères.")
                elif password != confirm:
                    st.error("Les deux mots de passe sont différents.")
                elif one(
                    "SELECT id FROM families WHERE username=?",
                    (username.strip(),)
                ):
                    st.error("Cet identifiant existe déjà.")
                else:
                    try:
                        execute(
                            """INSERT INTO families
                            (nom,email,telephone,username,password)
                            VALUES (?,?,?,?,?)""",
                            (
                                nom, email, telephone,
                                username.strip(),
                                hash_password(password)
                            )
                        )
                        st.success(
                            "Compte créé ! Vous pouvez maintenant vous connecter."
                        )
                    except sqlite3.Error:
                        st.error("Impossible de créer le compte.")


# =========================================================
# ESPACE FAMILLE
# =========================================================

def family_page():

    family_id = st.session_state.user_id
    family = one("SELECT * FROM families WHERE id=?", (family_id,))

    st.header("Espace famille")
    st.write("Bienvenue", family["nom"])

    tabs = st.tabs([
        "Mes enfants",
        "Ajouter un enfant",
        "Mes cours",
        "Absences et rattrapages",
        "Demi-pension",
        "Stages et événements",
        "Notifications"
    ])

    # ---------------- ENFANTS ----------------

    with tabs[0]:
        children = rows(
            "SELECT * FROM children WHERE family_id=?",
            (family_id,)
        )

        if not children:
            st.info("Ajoutez votre premier enfant dans l'onglet suivant.")

        for child in children:
            with st.container(border=True):
                st.subheader(child["prenom"])
                st.write("Âge :", child["age"])
                st.write("Galop :", child["galop"])
                if child["photo"]:
                    st.image(child["photo"], width=180)

                pony = one(
                    """SELECT ponies.nom FROM assignments
                    JOIN ponies ON ponies.id=assignments.pony_id
                    WHERE assignments.child_id=?
                    ORDER BY assignments.id DESC LIMIT 1""",
                    (child["id"],)
                )
                st.write(
                    "Poney attribué :",
                    pony["nom"] if pony else "Pas encore attribué"
                )

    # ---------------- AJOUT ENFANT ----------------

    with tabs[1]:
        with st.form("add_child"):
            prenom = st.text_input("Prénom de l'enfant")
            age = st.number_input("Âge", min_value=2, max_value=99, value=8)
            galop = st.selectbox(
                "Niveau",
                ["Débutant", "Galop 1", "Galop 2", "Galop 3",
                 "Galop 4", "Galop 5", "Galop 6", "Galop 7"]
            )
            photo = st.text_input("Lien de la photo (facultatif)")
            ok = st.form_submit_button("Ajouter l'enfant")

            if ok:
                if prenom.strip():
                    execute(
                        """INSERT INTO children
                        (family_id,prenom,age,galop,photo)
                        VALUES (?,?,?,?,?)""",
                        (family_id, prenom, age, galop, photo)
                    )
                    st.success("Enfant ajouté.")
                    st.rerun()
                else:
                    st.error("Indique le prénom.")

    # ---------------- COURS ----------------

    with tabs[2]:
        children = rows(
            "SELECT * FROM children WHERE family_id=?",
            (family_id,)
        )

        for child in children:
            st.subheader(child["prenom"])
            assigned = rows(
                """SELECT lessons.* FROM assignments
                JOIN lessons ON lessons.id=assignments.lesson_id
                WHERE assignments.child_id=?""",
                (child["id"],)
            )

            if not assigned:
                st.info("Aucun cours attribué pour le moment.")

            for lesson in assigned:
                st.write(
                    f"{lesson['jour']} à {lesson['heure']} "
                    f"— {lesson['niveau']}"
                )

    # ---------------- ABSENCES ----------------

    with tabs[3]:
        children = rows(
            "SELECT * FROM children WHERE family_id=?",
            (family_id,)
        )

        if children:
            with st.form("absence_request"):
                child_names = {
                    c["prenom"]: c["id"] for c in children
                }
                child_name = st.selectbox(
                    "Enfant",
                    list(child_names.keys())
                )
                kind = st.selectbox(
                    "Demande",
                    ["Absence", "Rattrapage"]
                )
                details = st.text_area(
                    "Date du cours concerné et explications"
                )
                ok = st.form_submit_button("Envoyer la demande")

                if ok:
                    if not details.strip():
                        st.error("Précise la date et le cours.")
                    else:
                        execute(
                            """INSERT INTO requests
                            (family_id,child_id,type,details,created)
                            VALUES (?,?,?,?,?)""",
                            (
                                family_id,
                                child_names[child_name],
                                kind,
                                details,
                                datetime.now().isoformat()
                            )
                        )
                        st.success("Demande envoyée.")
        else:
            st.info("Ajoutez d'abord un enfant.")

        st.caption(
            "Les demandes doivent être envoyées au moins 24 heures avant le cours."
        )

        for req in rows(
            "SELECT * FROM requests WHERE family_id=? ORDER BY id DESC",
            (family_id,)
        ):
            st.write(
                req["type"], " — ", req["details"],
                " — Statut :", req["statut"]
            )

   
    # ---------------- DP ----------------

    with tabs[4]:
        st.subheader("Demander une demi-pension")

        children = rows(
            "SELECT * FROM children WHERE family_id=?",
            (family_id,)
        )

        lessons = rows(
            "SELECT * FROM lessons ORDER BY jour, heure"
        )

        if children and lessons:

            with st.form("dp_request"):

                child_names = {
                    c["prenom"]: c["id"] for c in children
                }

                child_name = st.selectbox(
                    "Enfant concerné",
                    list(child_names.keys())
                )

                pony_rows = rows(
                    "SELECT nom FROM ponies ORDER BY nom"
                )

                pony_names = [
                    p["nom"] for p in pony_rows
                ]

                if pony_names:
                    poney_souhaite = st.selectbox(
                        "Poney ou cheval souhaité pour la DP",
                        pony_names
                    )
                else:
                    poney_souhaite = ""
                    st.warning(
                        "Aucun poney n'est encore enregistré."
                    )

                lesson_options = {
                    f"{l['jour']} - {l['heure']} - {l['niveau']}": l["id"]
                    for l in lessons
                }

                selected = st.multiselect(
                    "Choisissez les 3 cours de la semaine",
                    list(lesson_options.keys())
                )

                ok = st.form_submit_button(
                    "Envoyer ma demande de DP"
                )

            if ok:

                if len(selected) != 3:
                    st.error(
                        "Il faut sélectionner exactement 3 cours."
                    )

                else:
                    existing = one(
                        """
                        SELECT id FROM dp_requests
                        WHERE family_id=? AND child_id=?
                        AND statut='En attente'
                        """,
                        (
                            family_id,
                            child_names[child_name]
                        )
                    )

                    if existing:
                        st.error(
                            "Une demande est déjà en attente."
                        )

                    else:
                        course_ids = [
                            lesson_options[x] for x in selected
                        ]

                        execute(
                            """
                            INSERT INTO dp_requests
                            (family_id, child_id, courses, poney_souhaite)
                            VALUES (?, ?, ?, ?)
                            """,
                            (
                                family_id,
                                child_names[child_name],
                                json.dumps(course_ids),
                                poney_souhaite
                            )
                        )

                        st.success(
                            "Demande envoyée. Elle doit être validée par un coach."
                        )
                        st.rerun()

        else:
            st.info(
                "Il faut un enfant et des cours publiés."
            )

        st.divider()
        st.subheader("Mes demandes de demi-pension")

        for dp in rows(
            "SELECT * FROM dp_requests WHERE family_id=?",
            (family_id,)
        ):
            st.write("Statut :", dp["statut"])

            st.write(
                "Poney ou cheval souhaité :",
                dp["poney_souhaite"] or "Non renseigné"
            )

    # ---------------- STAGES ET EVENEMENTS ----------------

    with tabs[5]:
        children = rows(
            "SELECT * FROM children WHERE family_id=?",
            (family_id,)
        )

        st.subheader("Inscription aux stages")

        stages = rows("SELECT * FROM stages ORDER BY date_stage")

        if children and stages:
            with st.form("register_stage"):
                child_names = {
                    c["prenom"]: c["id"] for c in children
                }
                child_name = st.selectbox(
                    "Enfant",
                    list(child_names.keys()),
                    key="stage_child"
                )

                stage_names = {
                    f"{s['nom']} - {s['date_stage']}": s["id"]
                    for s in stages
                }
                stage_name = st.selectbox(
                    "Stage",
                    list(stage_names.keys())
                )

                ok = st.form_submit_button("S'inscrire au stage")

                if ok:
                    execute(
                        """INSERT INTO registrations
                        (family_id,child_id,type,item_id)
                        VALUES (?,?,?,?)""",
                        (
                            family_id,
                            child_names[child_name],
                            "stage",
                            stage_names[stage_name]
                        )
                    )
                    st.success("Demande d'inscription envoyée.")

        st.divider()
        st.subheader("Inscription aux événements")

        events = rows("SELECT * FROM events ORDER BY date_event")

        if children and events:
            with st.form("register_event"):
                child_names = {
                    c["prenom"]: c["id"] for c in children
                }
                child_name = st.selectbox(
                    "Enfant",
                    list(child_names.keys()),
                    key="event_child"
                )
                event_names = {
                    f"{e['nom']} - {e['date_event']}": e["id"]
                    for e in events
                }
                event_name = st.selectbox(
                    "Événement",
                    list(event_names.keys())
                )
                ok = st.form_submit_button("S'inscrire à l'événement")

                if ok:
                    execute(
                        """INSERT INTO registrations
                        (family_id,child_id,type,item_id)
                        VALUES (?,?,?,?)""",
                        (
                            family_id,
                            child_names[child_name],
                            "evenement",
                            event_names[event_name]
                        )
                    )
                    st.success("Inscription envoyée.")

    # ---------------- NOTIFICATIONS ----------------

    with tabs[6]:
        notifications = rows(
            """SELECT * FROM notifications
            WHERE family_id=? ORDER BY id DESC""",
            (family_id,)
        )

        if not notifications:
            st.info("Aucune notification pour le moment.")

        for notification in notifications:
            with st.container(border=True):
                st.write(notification["message"])
                st.caption(notification["date_creation"])


# =========================================================
# ESPACE COACH
# =========================================================

def coach_page():

    st.header("Espace coach")
    st.caption("Gestion du club AC Équitation")

    tabs = st.tabs([
        "Tableau de bord",
        "Cavaliers",
        "Poneys",
        "Planning",
        "Demi-pension",
        "Demandes",
        "Stages",
        "Événements",
        "Actualités",
        "Balades",
        "Attributions semaine",
        "Gestion équidés"
    ])       

    # ---------------- TABLEAU DE BORD ----------------

    with tabs[0]:

        c1, c2, c3, c4 = st.columns(4)

        c1.metric("Familles", len(rows("SELECT id FROM families")))
        c2.metric("Enfants", len(rows("SELECT id FROM children")))
        c3.metric("Poneys", len(rows("SELECT id FROM ponies")))
        c4.metric("Cours", len(rows("SELECT id FROM lessons")))

        st.subheader("Demandes en attente")

        st.write(
            "Absences et rattrapages :",
            len(rows(
                "SELECT id FROM requests WHERE statut='En attente'"
            ))
        )

        st.write(
            "Demi-pensions :",
            len(rows(
                "SELECT id FROM dp_requests WHERE statut='En attente'"
            ))
        )

    # ---------------- CAVALIERS ----------------

    with tabs[1]:

        st.subheader("Liste des cavaliers")

        for child in rows("""
            SELECT children.*, families.nom AS famille
            FROM children
            LEFT JOIN families ON families.id=children.family_id
            ORDER BY prenom
        """):

            with st.container(border=True):

                st.write(
                    f"**{child['prenom']}** — "
                    f"{child['age']} ans — {child['galop']}"
                )

                st.write("Famille :", child["famille"])

                if child["photo"]:
                    st.image(child["photo"], width=130)

                ponies = rows(
                    "SELECT id,nom FROM ponies WHERE actif=1 ORDER BY nom"
                )

                lessons = rows(
                    "SELECT id,jour,heure,niveau FROM lessons ORDER BY jour,heure"
                )

                if ponies and lessons:

                    with st.form(f"assign_{child['id']}"):

                        pony_map = {
                            p["nom"]: p["id"] for p in ponies
                        }

                        lesson_map = {
                            f"{l['jour']} {l['heure']} ({l['niveau']})": l["id"]
                            for l in lessons
                        }

                        pony_name = st.selectbox(
                            "Attribuer un poney",
                            list(pony_map.keys()),
                            key=f"pony_{child['id']}"
                        )

                        lesson_name = st.selectbox(
                            "Cours",
                            list(lesson_map.keys()),
                            key=f"lesson_{child['id']}"
                        )

                        ok = st.form_submit_button(
                            "Enregistrer l'attribution"
                        )

                        if ok:

                            execute("""
                                INSERT INTO assignments
                                (child_id,pony_id,lesson_id)
                                VALUES (?,?,?)
                            """, (
                                child["id"],
                                pony_map[pony_name],
                                lesson_map[lesson_name]
                            ))

                            st.success("Poney attribué.")

    # ---------------- PONEYS ----------------

    with tabs[2]:

        st.subheader("Ajouter un poney")

        with st.form("add_pony"):

            nom = st.text_input("Nom du poney")

            age = st.number_input(
                "Âge",
                min_value=0,
                max_value=50,
                value=5
            )

            description = st.text_area("Description et caractère")
            photo = st.text_input("Lien de la photo")

            ok = st.form_submit_button("Ajouter le poney")

            if ok:

                if nom.strip():

                    execute("""
                        INSERT INTO ponies
                        (nom,age,description,photo)
                        VALUES (?,?,?,?)
                    """, (nom, age, description, photo))

                    st.success("Poney ajouté.")
                    st.rerun()

                else:
                    st.error("Indique le nom.")

        st.divider()
        st.subheader("Poneys du club")

        for pony in rows("SELECT * FROM ponies ORDER BY nom"):

            with st.container(border=True):

                st.write("**" + pony["nom"] + "**")
                st.write(pony["description"])

                if pony["photo"]:
                    st.image(pony["photo"], width=150)

                if pony["actif"] == 1:

                    if st.button(
                        "Désactiver " + pony["nom"],
                        key=f"off_{pony['id']}"
                    ):

                        execute(
                            "UPDATE ponies SET actif=0 WHERE id=?",
                            (pony["id"],)
                        )

                        st.rerun()

                else:

                    if st.button(
                        "Réactiver " + pony["nom"],
                        key=f"on_{pony['id']}"
                    ):

                        execute(
                            "UPDATE ponies SET actif=1 WHERE id=?",
                            (pony["id"],)
                        )

                        st.rerun()

    # ---------------- PLANNING ----------------

    with tabs[3]:

        st.subheader("Créer un cours hebdomadaire")

        with st.form("add_lesson"):

            jour = st.selectbox(
                "Jour",
                ["Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"]
            )

            heure = st.time_input("Heure")

            duree = st.number_input(
                "Durée en minutes",
                min_value=15,
                max_value=240,
                value=60
            )

            niveau = st.text_input("Niveau du cours")

            places = st.number_input(
                "Nombre de places",
                min_value=1,
                max_value=30,
                value=8
            )

            ok = st.form_submit_button("Ajouter au planning")

            if ok:

                execute("""
                    INSERT INTO lessons
                    (jour,heure,duree,niveau,places)
                    VALUES (?,?,?,?,?)
                """, (jour, str(heure), duree, niveau, places))

                st.success("Cours ajouté.")
                st.rerun()

        st.divider()
        st.subheader("Cours de la semaine")

        lessons = rows("SELECT * FROM lessons ORDER BY jour,heure")

        for lesson in lessons:

            with st.expander(
                f"{lesson['jour']} — {lesson['heure']} — {lesson['niveau']}"
            ):

                st.write("Durée :", lesson["duree"], "minutes")
                st.write("Places :", lesson["places"])

                with st.form(f"change_{lesson['id']}"):

                    date_cours = st.date_input(
                        "Date du cours concerné",
                        value=date.today(),
                        key=f"date_{lesson['id']}"
                    )

                    action = st.selectbox(
                        "Action",
                        ["Annuler ce cours", "Déplacer ce cours"],
                        key=f"action_{lesson['id']}"
                    )

                    nouvelle_date = st.date_input(
                        "Nouvelle date (si déplacement)",
                        value=date.today() + timedelta(days=1),
                        key=f"newdate_{lesson['id']}"
                    )

                    nouvelle_heure = st.time_input(
                        "Nouvelle heure",
                        key=f"newtime_{lesson['id']}"
                    )

                    message = st.text_input(
                        "Message aux familles",
                        key=f"msg_{lesson['id']}"
                    )

                    ok = st.form_submit_button("Confirmer")

                    if ok:

                        execute("""
                            INSERT INTO lesson_changes
                            (lesson_id,date_cours,action,nouvelle_date,
                            nouvelle_heure,message)
                            VALUES (?,?,?,?,?,?)
                        """, (
                            lesson["id"],
                            str(date_cours),
                            action,
                            str(nouvelle_date),
                            str(nouvelle_heure),
                            message
                        ))

                        assigned_families = rows("""
                            SELECT DISTINCT children.family_id
                            FROM assignments
                            JOIN children
                            ON children.id=assignments.child_id
                            WHERE assignments.lesson_id=?
                        """, (lesson["id"],))

                        notification = (
                            f"Cours du {date_cours} : {action}. {message}"
                        )

                        if action == "Déplacer ce cours":

                            notification += (
                                f" Nouveau créneau : "
                                f"{nouvelle_date} à {nouvelle_heure}."
                            )

                        for fam in assigned_families:

                            if fam["family_id"]:

                                notify_family(
                                    fam["family_id"],
                                    notification
                                )

                        st.success("Modification enregistrée.")
                        st.rerun()

                if st.button(
                    "Supprimer ce cours du planning",
                    key=f"delete_lesson_{lesson['id']}"
                ):

                    execute(
                        "DELETE FROM lessons WHERE id=?",
                        (lesson["id"],)
                    )

                    st.rerun()

        st.caption(
            "Les cours sont hebdomadaires. Une annulation ou un "
            "déplacement concerne uniquement la date choisie."
        )

    # ---------------- DEMI-PENSION ----------------

    with tabs[4]:

        st.subheader("Demandes de demi-pension")

        for dp in rows(
            "SELECT * FROM dp_requests ORDER BY id DESC"
        ):

            child = one(
                "SELECT prenom FROM children WHERE id=?",
                (dp["child_id"],)
            )

            family = one(
                "SELECT nom FROM families WHERE id=?",
                (dp["family_id"],)
            )

            with st.container(border=True):

                st.write(
                    "Enfant :",
                    child["prenom"] if child else "Inconnu"
                )

                st.write(
                    "Famille :",
                    family["nom"] if family else "Inconnue"
                )

                st.write(
                    "Poney ou cheval souhaité :",
                    dp["poney_souhaite"] or "Non renseigné"
                )

                st.write("Statut :", dp["statut"])

                try:

                    ids = json.loads(dp["courses"])

                    for lesson_id in ids:

                        lesson = one(
                            "SELECT * FROM lessons WHERE id=?",
                            (lesson_id,)
                        )

                        if lesson:

                            st.write(
                                lesson["jour"],
                                lesson["heure"],
                                lesson["niveau"]
                            )

                except Exception:

                    st.write("Détails des cours indisponibles.")

                if dp["statut"] == "En attente":

                    a, b = st.columns(2)

                    if a.button(
                        "Valider",
                        key=f"dp_yes_{dp['id']}"
                    ):

                        execute(
                            "UPDATE dp_requests SET statut='Acceptée' WHERE id=?",
                            (dp["id"],)
                        )

                        notify_family(
                            dp["family_id"],
                            "Votre demande de demi-pension a été acceptée."
                        )

                        st.rerun()

                    if b.button(
                        "Refuser",
                        key=f"dp_no_{dp['id']}"
                    ):

                        execute(
                            "UPDATE dp_requests SET statut='Refusée' WHERE id=?",
                            (dp["id"],)
                        )

                        notify_family(
                            dp["family_id"],
                            "Votre demande de demi-pension a été refusée."
                        )

                        st.rerun()

    # ---------------- DEMANDES ----------------

    with tabs[5]:

        st.subheader("Absences et rattrapages")

        for req in rows("SELECT * FROM requests ORDER BY id DESC"):

            child = one(
                "SELECT prenom FROM children WHERE id=?",
                (req["child_id"],)
            )

            with st.container(border=True):

                st.write(
                    req["type"],
                    " — ",
                    child["prenom"] if child else "Enfant inconnu"
                )

                st.write(req["details"])
                st.write("Statut :", req["statut"])

                if req["statut"] == "En attente":

                    a, b = st.columns(2)

                    if a.button(
                        "Accepter",
                        key=f"req_yes_{req['id']}"
                    ):

                        execute(
                            "UPDATE requests SET statut='Acceptée' WHERE id=?",
                            (req["id"],)
                        )

                        notify_family(
                            req["family_id"],
                            "Votre demande de " + req["type"] + " a été acceptée."
                        )

                        st.rerun()

                    if b.button(
                        "Refuser",
                        key=f"req_no_{req['id']}"
                    ):

                        execute(
                            "UPDATE requests SET statut='Refusée' WHERE id=?",
                            (req["id"],)
                        )

                        notify_family(
                            req["family_id"],
                            "Votre demande de " + req["type"] + " a été refusée."
                        )

                        st.rerun()

    # ---------------- STAGES ----------------

    with tabs[6]:

        st.subheader("Ajouter un stage")

        with st.form("add_stage"):

            nom = st.text_input("Nom du stage")
            discipline = st.text_input("Discipline")
            date_stage = st.date_input("Date du stage")
            horaire = st.text_input("Horaires")
            niveau = st.text_input("Niveau minimum")

            places = st.number_input(
                "Nombre de places",
                min_value=1,
                value=8
            )

            tarif = st.number_input("Tarif (€)", min_value=0.0)

            ok = st.form_submit_button("Publier le stage")

            if ok:

                if nom.strip() and discipline.strip():

                    execute("""
                        INSERT INTO stages
                        (nom,discipline,date_stage,horaire,niveau,places,tarif)
                        VALUES (?,?,?,?,?,?,?)
                    """, (
                        nom,
                        discipline,
                        str(date_stage),
                        horaire,
                        niveau,
                        places,
                        tarif
                    ))

                    notify_all_families(
                        "Un nouveau stage est disponible : " + nom
                    )

                    st.success("Stage publié.")
                    st.rerun()

                else:
                    st.error("Indique le nom et la discipline.")

        st.divider()

        for stage in rows("SELECT * FROM stages ORDER BY date_stage"):

            with st.container(border=True):

                st.write(
                    f"**{stage['nom']}** — {stage['date_stage']}"
                )

                st.write(stage["discipline"], stage["horaire"])
                st.write("Places :", stage["places"])
                st.write("Tarif :", stage["tarif"], "€")

                if st.button(
                    "Supprimer ce stage",
                    key=f"del_stage_{stage['id']}"
                ):

                    execute(
                        "DELETE FROM stages WHERE id=?",
                        (stage["id"],)
                    )

                    st.rerun()

    # ---------------- EVENEMENTS ----------------

    with tabs[7]:

        st.subheader("Ajouter un concours ou événement")

        with st.form("add_event"):

            nom = st.text_input("Nom de l'événement")
            date_event = st.date_input("Date")
            description = st.text_area("Description")
            tarif = st.number_input("Tarif (€)", min_value=0.0)

            ok = st.form_submit_button("Publier l'événement")

            if ok:

                if nom.strip():

                    execute("""
                        INSERT INTO events
                        (nom,date_event,description,tarif)
                        VALUES (?,?,?,?)
                    """, (nom, str(date_event), description, tarif))

                    notify_all_families(
                        "Nouvel événement : " + nom
                    )

                    st.success("Événement publié.")
                    st.rerun()

        st.divider()

        for event in rows("SELECT * FROM events ORDER BY date_event"):

            with st.container(border=True):

                st.write(
                    f"**{event['nom']}** — {event['date_event']}"
                )

                st.write(event["description"])

                if st.button(
                    "Supprimer",
                    key=f"del_event_{event['id']}"
                ):

                    execute(
                        "DELETE FROM events WHERE id=?",
                        (event["id"],)
                    )

                    st.rerun()

    # ---------------- ACTUALITES ----------------

    with tabs[8]:

        st.subheader("Rédiger un article")

        with st.form("add_post"):

            titre = st.text_input("Titre de l'article")
            contenu = st.text_area("Texte de l'article")
            photo = st.text_input("Lien de la photo (facultatif)")

            ok = st.form_submit_button("Publier l'article")

            if ok:

                if titre.strip() and contenu.strip():

                    execute("""
                        INSERT INTO posts
                        (titre,contenu,photo,date_post)
                        VALUES (?,?,?,?)
                    """, (
                        titre,
                        contenu,
                        photo,
                        date.today().strftime("%d/%m/%Y")
                    ))

                    notify_all_families(
                        "Nouvelle actualité : " + titre
                    )

                    st.success("Article publié.")
                    st.rerun()

        st.divider()

        for post in rows("SELECT * FROM posts ORDER BY id DESC"):

            with st.container(border=True):

                st.write("**" + post["titre"] + "**")
                st.write(post["contenu"])

                if post["photo"]:
                    st.image(post["photo"], width=200)

                if st.button(
                    "Supprimer l'article",
                    key=f"del_post_{post['id']}"
                ):

                    execute(
                        "DELETE FROM posts WHERE id=?",
                        (post["id"],)
                    )

                    st.rerun()

    # ---------------- BALADES ----------------

    with tabs[9]:

        st.subheader("Demandes de balades")

        for ride in rows("SELECT * FROM rides ORDER BY id DESC"):

            with st.container(border=True):

                st.write("Responsable :", ride["nom_responsable"])
                st.write("Enfant :", ride["prenom_enfant"])
                st.write("Téléphone :", ride["telephone"])
                st.write("Mail :", ride["email"])

                st.write(
                    ride["date_balade"],
                    "à",
                    ride["horaire"]
                )

                st.write("Tarif :", ride["tarif"], "€")
                st.write("Statut :", ride["statut"])

                if ride["statut"] == "En attente":

                    a, b = st.columns(2)

                    if a.button(
                        "Confirmer",
                        key=f"ride_yes_{ride['id']}"
                    ):

                        execute(
                            "UPDATE rides SET statut='Confirmée' WHERE id=?",
                            (ride["id"],)
                        )

                        st.rerun()

                    if b.button(
                        "Refuser",
                        key=f"ride_no_{ride['id']}"
                    ):

                        execute(
                            "UPDATE rides SET statut='Refusée' WHERE id=?",
                            (ride["id"],)
                        )

                        st.rerun()

    # ---------------- ATTRIBUTIONS SEMAINE ----------------

    with tabs[10]:

        st.subheader("Attributions des poneys par semaine")

        semaine = st.date_input(
            "Choisir une date dans la semaine",
            value=date.today(),
            key="choix_semaine_attributions"
        )

        lundi = semaine - timedelta(days=semaine.weekday())
        semaine_debut = str(lundi)

        st.info(
            f"Attributions de la semaine du {lundi.strftime('%d/%m/%Y')}"
        )

        lessons = rows("""
            SELECT * FROM lessons
            WHERE jour IN ('Mardi', 'Mercredi', 'Jeudi',
                           'Vendredi', 'Samedi')
            ORDER BY
                CASE jour
                    WHEN 'Mardi' THEN 1
                    WHEN 'Mercredi' THEN 2
                    WHEN 'Jeudi' THEN 3
                    WHEN 'Vendredi' THEN 4
                    WHEN 'Samedi' THEN 5
                END,
                heure
        """)

        children = rows(
            "SELECT * FROM children ORDER BY prenom"
        )

        ponies = rows(
            "SELECT * FROM ponies WHERE actif=1 ORDER BY nom"
        )

        if not lessons:

            st.warning("Aucun cours du mardi au samedi n'est enregistré.")

        elif not children:

            st.warning("Aucun cavalier enregistré.")

        elif not ponies:

            st.warning("Aucun poney actif enregistré.")

        else:

            child_map = {
                f"{c['prenom']} (n°{c['id']})": c["id"]
                for c in children
            }

            pony_map = {
                p["nom"]: p["id"] for p in ponies
            }

            for lesson in lessons:

                with st.expander(
                    f"{lesson['jour']} — {lesson['heure']} — {lesson['niveau']}"
                ):

                    st.write("Cavaliers et poneys de ce cours :")

                    inscriptions = rows("""
                        SELECT weekly_assignments.*,
                               children.prenom,
                               ponies.nom AS poney
                        FROM weekly_assignments
                        JOIN children
                            ON children.id=weekly_assignments.child_id
                        JOIN ponies
                            ON ponies.id=weekly_assignments.pony_id
                        WHERE semaine_debut=? AND lesson_id=?
                        ORDER BY children.prenom
                    """, (semaine_debut, lesson["id"]))

                    if inscriptions:

                        for inscription in inscriptions:

                            st.write(
                                f"• {inscription['prenom']} — "
                                f"{inscription['poney']}"
                            )

                    else:

                        st.info("Aucune attribution pour cette semaine.")

                    st.divider()
                    st.write("Ajouter ou modifier une attribution")

                    with st.form(
                        f"weekly_{semaine_debut}_{lesson['id']}"
                    ):

                        child_name = st.selectbox(
                            "Cavalier",
                            list(child_map.keys())
                        )

                        pony_name = st.selectbox(
                            "Poney ou cheval",
                            list(pony_map.keys())
                        )

                        ok = st.form_submit_button(
                            "Enregistrer l'attribution"
                        )

                        if ok:

                            execute("""
                                INSERT INTO weekly_assignments
                                (semaine_debut, child_id, pony_id, lesson_id)
                                VALUES (?, ?, ?, ?)
                                ON CONFLICT(semaine_debut, child_id, lesson_id)
                                DO UPDATE SET pony_id=excluded.pony_id
                            """, (
                                semaine_debut,
                                child_map[child_name],
                                pony_map[pony_name],
                                lesson["id"]
                            ))

                            st.success("Attribution enregistrée.")
                            st.rerun()
 # ---------------- GESTION EQUIDES ----------------

    with tabs[11]:
        st.subheader("Gestion des chevaux et poneys")

        # Ton code de gestion des équidés ici

# =========================================================
# CREATION DES COMPTES COACHS
# =========================================================

def coach_registration_page():

    st.header("Créer un compte coach")

    st.info(
        "Deux comptes coach maximum peuvent être créés. "
        "Chaque coach choisit son propre identifiant et son mot de passe."
    )

    code_secret = coach_setup_code()

    if not code_secret:
        st.error(
            "Le responsable doit d'abord configurer COACH_SETUP_CODE "
            "dans les Secrets de Streamlit."
        )
        return

    nombre_coachs = one("SELECT COUNT(*) AS total FROM coaches")["total"]

    if nombre_coachs >= 2:
        st.warning("Les deux comptes coachs sont déjà créés.")
        return

    with st.form("coach_registration"):
        nom = st.text_input("Nom du coach")
        username = st.text_input("Choisir son identifiant")
        password = st.text_input(
            "Choisir son mot de passe",
            type="password"
        )
        confirm = st.text_input(
            "Confirmer le mot de passe",
            type="password"
        )
        code = st.text_input(
            "Code d'inscription fourni par le responsable",
            type="password"
        )

        ok = st.form_submit_button("Créer mon compte coach")

        if ok:
            if not all([nom, username, password, confirm, code]):
                st.error("Tous les champs sont obligatoires.")
            elif code != code_secret:
                st.error("Code d'inscription incorrect.")
            elif len(password) < 10:
                st.error("Choisis un mot de passe d'au moins 10 caractères.")
            elif password != confirm:
                st.error("Les deux mots de passe ne correspondent pas.")
            elif one(
                "SELECT id FROM coaches WHERE username=?",
                (username.strip(),)
            ):
                st.error("Cet identifiant est déjà utilisé.")
            else:
                try:
                    execute(
                        """INSERT INTO coaches (username,password,nom)
                        VALUES (?,?,?)""",
                        (
                            username.strip(),
                            hash_password(password),
                            nom.strip()
                        )
                    )
                    st.success(
                        "Compte coach créé ! Tu peux maintenant te connecter."
                    )
                except sqlite3.Error:
                    st.error("Erreur pendant la création du compte.")


# =========================================================
# NAVIGATION GENERALE
# =========================================================

if st.session_state.role == "family":
    family_page()

elif st.session_state.role == "coach":
    coach_page()

else:
    public_page()

    st.divider()

    with st.expander("Espace réservé à la création des comptes coachs"):
        coach_registration_page()

st.divider()
st.caption("AC Équitation — Application de gestion du club")
