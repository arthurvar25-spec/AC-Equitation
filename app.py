
import streamlit as st
import sqlite3
import hashlib
import secrets
import json
from datetime import date, datetime, time, timedelta

# =========================================================
# AC EQUITATION - APPLICATION COMPLETE
# =========================================================

st.set_page_config(
    page_title="AC Équitation",
    page_icon="🐴",
    layout="wide"
)

DB = "ac_equitation_v3.db"

JOURS = [
    "Lundi", "Mardi", "Mercredi", "Jeudi",
    "Vendredi", "Samedi", "Dimanche"
]

# Identifiants des deux coachs
# Change les mots de passe après le premier lancement.
COACHS = {
    "coach1": ("Coach 1", "ACcoach2026!"),
    "coach2": ("Coach 2", "ACcoach2027!")
}

# =========================================================
# DESIGN
# =========================================================

st.markdown("""
<style>
.stApp {
    background-color: #f5f4ed;
}
h1, h2, h3 {
    color: #405b49;
}
.stButton button {
    background-color: #607b65;
    color: white;
    border-radius: 10px;
    border: none;
}
.stButton button:hover {
    background-color: #405b49;
    color: white;
}
div[data-testid="stForm"] {
    background: white;
    padding: 18px;
    border-radius: 14px;
    border: 1px solid #e3e0d5;
}
div[data-testid="stMetric"] {
    background: white;
    padding: 12px;
    border-radius: 12px;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# BASE DE DONNEES
# =========================================================

def connect():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def execute(sql, values=()):
    with connect() as db:
        cur = db.execute(sql, values)
        db.commit()
        return cur.lastrowid


def query(sql, values=()):
    with connect() as db:
        return db.execute(sql, values).fetchall()


def init_db():
    with connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS families (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            telephone TEXT,
            adresse TEXT,
            password TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS coaches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            identifiant TEXT UNIQUE NOT NULL,
            nom TEXT NOT NULL,
            password TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS children (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            family_id INTEGER,
            prenom TEXT NOT NULL,
            age INTEGER,
            poids REAL,
            taille REAL,
            galop TEXT,
            photo BLOB,
            temporaire INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS ponies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            age TEXT,
            description TEXT,
            photo BLOB,
            actif INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS slots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jour TEXT NOT NULL,
            heure TEXT NOT NULL,
            niveau TEXT,
            places INTEGER DEFAULT 8,
            actif INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            child_id INTEGER NOT NULL,
            slot_id INTEGER NOT NULL,
            pony_id INTEGER,
            UNIQUE(child_id, slot_id)
        );

        CREATE TABLE IF NOT EXISTS dp_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            child_id INTEGER NOT NULL,
            slot_ids TEXT NOT NULL,
            statut TEXT DEFAULT 'En attente'
        );

        CREATE TABLE IF NOT EXISTS absences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            child_id INTEGER,
            slot_id INTEGER,
            date_absence TEXT,
            motif TEXT,
            type_demande TEXT,
            statut TEXT DEFAULT 'En attente',
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS stages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT,
            discipline TEXT,
            date_stage TEXT,
            horaire TEXT,
            niveau TEXT,
            places INTEGER,
            tarif REAL
        );

        CREATE TABLE IF NOT EXISTS stage_regs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stage_id INTEGER,
            nom_enfant TEXT,
            nom_responsable TEXT,
            telephone TEXT,
            email TEXT
        );

        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT,
            date_event TEXT,
            description TEXT
        );

        CREATE TABLE IF NOT EXISTS event_regs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            nom_enfant TEXT,
            nom_responsable TEXT,
            telephone TEXT,
            email TEXT
        );

        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titre TEXT,
            contenu TEXT,
            photo BLOB,
            date_article TEXT
        );

        CREATE TABLE IF NOT EXISTS walk_bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            enfant TEXT,
            responsable TEXT,
            telephone TEXT,
            email TEXT,
            date_balade TEXT,
            heure TEXT,
            tarif REAL,
            statut TEXT DEFAULT 'En attente'
        );

        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            family_id INTEGER,
            message TEXT,
            date_creation TEXT,
            lu INTEGER DEFAULT 0
        );
        """)
        db.commit()


init_db()

# =========================================================
# COMPTES COACHS
# =========================================================

def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt.encode(),
        200000
    ).hex()
    return salt + "$" + digest


def check_password(password, stored):
    try:
        salt, digest = stored.split("$")
        test = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            salt.encode(),
            200000
        ).hex()
        return secrets.compare_digest(test, digest)
    except Exception:
        return False


def initialiser_coachs():
    for identifiant, informations in COACHS.items():
        nom, password = informations
        exists = query(
            "SELECT id FROM coaches WHERE identifiant=?",
            (identifiant,)
        )
        if not exists:
            execute("""
                INSERT INTO coaches (identifiant, nom, password)
                VALUES (?, ?, ?)
            """, (identifiant, nom, hash_password(password)))


initialiser_coachs()

# =========================================================
# OUTILS
# =========================================================

def notifier(family_id, message):
    if family_id:
        execute("""
            INSERT INTO notifications
            (family_id, message, date_creation)
            VALUES (?, ?, ?)
        """, (
            family_id,
            message,
            datetime.now().strftime("%d/%m/%Y à %H:%M")
        ))


def notifier_enfant(child_id, message):
    rows = query(
        "SELECT family_id FROM children WHERE id=?",
        (child_id,)
    )
    if rows and rows[0]["family_id"]:
        notifier(rows[0]["family_id"], message)


def notifier_toutes_familles(message):
    families = query("SELECT id FROM families")
    for family in families:
        notifier(family["id"], message)


def photo_widget(photo):
    if photo:
        st.image(photo, use_container_width=True)


def slot_label(slot):
    return (
        f"{slot['jour']} à {slot['heure']} "
        f"— {slot['niveau']}"
    )


def get_children(family_id):
    return query("""
        SELECT * FROM children
        WHERE family_id=? AND temporaire=0
        ORDER BY prenom
    """, (family_id,))


def get_slot(slot_id):
    rows = query(
        "SELECT * FROM slots WHERE id=?",
        (slot_id,)
    )
    return rows[0] if rows else None


def ordre_jours(jour):
    return JOURS.index(jour) if jour in JOURS else 7


def photo_bytes(upload):
    return upload.getvalue() if upload else None


# =========================================================
# SESSION
# =========================================================

if "role" not in st.session_state:
    st.session_state.role = None

if "user_id" not in st.session_state:
    st.session_state.user_id = None

if "user_name" not in st.session_state:
    st.session_state.user_name = None


def logout():
    st.session_state.role = None
    st.session_state.user_id = None
    st.session_state.user_name = None
    st.rerun()


# =========================================================
# EN-TETE
# =========================================================

st.title("🐴 AC ÉQUITATION")
st.caption("Le club, les familles, les cavaliers et les poneys réunis.")
st.divider()


# =========================================================
# PAGE PUBLIQUE
# =========================================================

def public_page():

    tabs = st.tabs([
        "Accueil",
        "Nos poneys",
        "Planning",
        "Stages",
        "Concours et événements",
        "Actualités",
        "Balades",
        "Connexion",
        "Créer un compte"
    ])

    # ACCUEIL
    with tabs[0]:
        st.header("Bienvenue chez AC Équitation 🌿")
        st.write(
            "Retrouvez ici les informations du club, "
            "les poneys, les cours, les stages et les actualités."
        )

        st.subheader("Les dernières nouvelles")

        articles = query("""
            SELECT * FROM articles
            ORDER BY id DESC LIMIT 3
        """)

        if not articles:
            st.info("Les actualités arriveront bientôt.")

        for article in articles:
            with st.container(border=True):
                st.subheader(article["titre"])
                photo_widget(article["photo"])
                st.write(article["contenu"])
                st.caption(article["date_article"])

    # PONEYS
    with tabs[1]:
        st.header("Les poneys du club")

        ponies = query("""
            SELECT * FROM ponies
            WHERE actif=1 ORDER BY nom
        """)

        if not ponies:
            st.info("Les fiches des poneys seront bientôt disponibles.")

        for pony in ponies:
            with st.container(border=True):
                st.subheader(pony["nom"])
                photo_widget(pony["photo"])
                st.write("Âge :", pony["age"] or "Non renseigné")
                st.write(pony["description"] or "")

    # PLANNING
    with tabs[2]:
        st.header("Planning hebdomadaire")

        slots = query("""
            SELECT * FROM slots
            WHERE actif=1
        """)

        slots = sorted(
            slots,
            key=lambda s: (ordre_jours(s["jour"]), s["heure"])
        )

        if not slots:
            st.info("Le planning sera bientôt disponible.")

        for slot in slots:
            st.write(
                f"**{slot['jour']} à {slot['heure']}** "
                f"— {slot['niveau']} — {slot['places']} places"
            )

    # STAGES
    with tabs[3]:
        st.header("Stages disponibles")

        stages = query("""
            SELECT * FROM stages
            ORDER BY date_stage
        """)

        for stage in stages:
            inscrits = query("""
                SELECT COUNT(*) AS n
                FROM stage_regs WHERE stage_id=?
            """, (stage["id"],))[0]["n"]

            restantes = max(0, stage["places"] - inscrits)

            with st.container(border=True):
                st.subheader(stage["nom"])
                st.write("Discipline :", stage["discipline"])
                st.write("Date :", stage["date_stage"])
                st.write("Horaire :", stage["horaire"])
                st.write("Niveau minimum :", stage["niveau"])
                st.write("Places restantes :", restantes)
                st.write("Tarif :", stage["tarif"], "€")

                with st.form(f"stage_{stage['id']}"):
                    enfant = st.text_input(
                        "Prénom et nom de l'enfant",
                        key=f"se_{stage['id']}"
                    )
                    responsable = st.text_input(
                        "Prénom et nom du responsable",
                        key=f"sr_{stage['id']}"
                    )
                    tel = st.text_input(
                        "Téléphone",
                        key=f"st_{stage['id']}"
                    )
                    email = st.text_input(
                        "Adresse e-mail",
                        key=f"sm_{stage['id']}"
                    )

                    ok = st.form_submit_button("Réserver ce stage")

                    if ok:
                        if not all([enfant, responsable, tel, email]):
                            st.error("Remplis tous les champs.")
                        elif restantes <= 0:
                            st.error("Ce stage est complet.")
                        else:
                            execute("""
                                INSERT INTO stage_regs
                                (stage_id, nom_enfant, nom_responsable,
                                 telephone, email)
                                VALUES (?, ?, ?, ?, ?)
                            """, (
                                stage["id"], enfant, responsable,
                                tel, email
                            ))
                            st.success("Inscription enregistrée.")

    # CONCOURS ET EVENEMENTS
    with tabs[4]:
        st.header("Concours et événements")

        events = query("""
            SELECT * FROM events
            ORDER BY date_event
        """)

        if not events:
            st.info("Aucun événement publié pour le moment.")

        for event in events:
            with st.container(border=True):
                st.subheader(event["nom"])
                st.write(event["date_event"])
                st.write(event["description"])

                with st.form(f"event_{event['id']}"):
                    enfant = st.text_input(
                        "Prénom de l'enfant",
                        key=f"ee_{event['id']}"
                    )
                    responsable = st.text_input(
                        "Nom du responsable",
                        key=f"er_{event['id']}"
                    )
                    tel = st.text_input(
                        "Téléphone",
                        key=f"et_{event['id']}"
                    )
                    email = st.text_input(
                        "E-mail",
                        key=f"em_{event['id']}"
                    )

                    ok = st.form_submit_button("S'inscrire")

                    if ok:
                        if not all([enfant, responsable, tel, email]):
                            st.error("Remplis tous les champs.")
                        else:
                            execute("""
                                INSERT INTO event_regs
                                (event_id, nom_enfant, nom_responsable,
                                 telephone, email)
                                VALUES (?, ?, ?, ?, ?)
                            """, (
                                event["id"], enfant, responsable,
                                tel, email
                            ))
                            st.success("Inscription envoyée.")

    # ACTUALITES
    with tabs[5]:
        st.header("Actualités du club")

        for article in query("""
            SELECT * FROM articles ORDER BY id DESC
        """):
            with st.container(border=True):
                st.subheader(article["titre"])
                photo_widget(article["photo"])
                st.write(article["contenu"])
                st.caption(article["date_article"])

    # BALADES
    with tabs[6]:
        st.header("Réserver une balade à poney")

        st.write(
            "Remplis le formulaire pour envoyer une demande "
            "de réservation au club."
        )

        with st.form("walk_form"):
            enfant = st.text_input("Prénom et nom de l'enfant")
            age = st.number_input(
                "Âge de l'enfant",
                min_value=1,
                max_value=18,
                value=8
            )
            responsable = st.text_input(
                "Prénom et nom du responsable"
            )
            telephone = st.text_input("Téléphone")
            email = st.text_input("Adresse e-mail")
            jour = st.date_input(
                "Date souhaitée",
                min_value=date.today()
            )
            heure = st.selectbox(
                "Horaire",
                [
                    "10h00", "10h30", "11h00",
                    "14h00", "14h30", "15h00",
                    "15h30", "16h00"
                ]
            )
            tarif = st.number_input(
                "Tarif de la balade (€)",
                min_value=0.0,
                value=10.0
            )

            ok = st.form_submit_button("Envoyer ma réservation")

            if ok:
                if not all([enfant, responsable, telephone, email]):
                    st.error("Remplis tous les champs.")
                else:
                    execute("""
                        INSERT INTO walk_bookings
                        (enfant, responsable, telephone, email,
                         date_balade, heure, tarif)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        enfant, responsable, telephone, email,
                        str(jour), heure, tarif
                    ))
                    st.success("Demande envoyée au club.")

    # CONNEXION
    with tabs[7]:
        st.header("Connexion")

        role = st.radio(
            "Je suis :",
            ["Famille", "Coach"],
            horizontal=True
        )

        with st.form("login_form"):
            if role == "Famille":
                email = st.text_input("Adresse e-mail")
                password = st.text_input(
                    "Mot de passe",
                    type="password"
                )
            else:
                identifiant = st.text_input("Identifiant coach")
                password = st.text_input(
                    "Mot de passe coach",
                    type="password"
                )

            ok = st.form_submit_button("Se connecter")

            if ok:
                if role == "Famille":
                    users = query(
                        "SELECT * FROM families WHERE email=?",
                        (email.strip().lower(),)
                    )

                    if users and check_password(
                        password, users[0]["password"]
                    ):
                        st.session_state.role = "family"
                        st.session_state.user_id = users[0]["id"]
                        st.session_state.user_name = users[0]["nom"]
                        st.rerun()
                    else:
                        st.error("Adresse e-mail ou mot de passe incorrect.")

                else:
                    coaches = query(
                        "SELECT * FROM coaches WHERE identifiant=?",
                        (identifiant.strip(),)
                    )

                    if coaches and check_password(
                        password, coaches[0]["password"]
                    ):
                        st.session_state.role = "coach"
                        st.session_state.user_id = coaches[0]["id"]
                        st.session_state.user_name = coaches[0]["nom"]
                        st.rerun()
                    else:
                        st.error("Identifiant ou mot de passe incorrect.")

    # CREATION COMPTE FAMILLE
    with tabs[8]:
        st.header("Créer un compte famille")
        st.write("Un compte parent peut gérer plusieurs enfants.")

        with st.form("register_form"):
            nom = st.text_input("Nom et prénom du responsable")
            email = st.text_input("Adresse e-mail")
            tel = st.text_input("Téléphone")
            adresse = st.text_input("Adresse postale")
            password = st.text_input(
                "Créer un mot de passe",
                type="password"
            )
            password2 = st.text_input(
                "Confirmer le mot de passe",
                type="password"
            )

            ok = st.form_submit_button("Créer mon compte")

            if ok:
                if not all([nom, email, tel, adresse, password, password2]):
                    st.error("Tous les champs sont obligatoires.")
                elif password != password2:
                    st.error("Les mots de passe ne correspondent pas.")
                elif len(password) < 8:
                    st.error("Le mot de passe doit contenir 8 caractères minimum.")
                elif query(
                    "SELECT id FROM families WHERE email=?",
                    (email.strip().lower(),)
                ):
                    st.error("Cette adresse e-mail est déjà utilisée.")
                else:
                    execute("""
                        INSERT INTO families
                        (nom, email, telephone, adresse, password)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        nom, email.strip().lower(), tel,
                        adresse, hash_password(password)
                    ))
                    st.success(
                        "Compte créé ! Tu peux maintenant te connecter."
                    )


# =========================================================
# ESPACE FAMILLE
# =========================================================

def family_page():

    fid = st.session_state.user_id

    families = query(
        "SELECT * FROM families WHERE id=?",
        (fid,)
    )

    if not families:
        st.error("Compte introuvable.")
        logout()
        return

    family = families[0]
    children = get_children(fid)

    st.header(f"Bonjour {family['nom']} !")

    tabs = st.tabs([
        "Accueil",
        "Mes enfants",
        "Mon planning",
        "Demi-pension",
        "Absences et rattrapages",
        "Stages et événements",
        "Notifications"
    ])

    # ACCUEIL
    with tabs[0]:
        st.subheader("Mon espace famille")
        st.write("E-mail :", family["email"])
        st.write("Téléphone :", family["telephone"])
        st.write("Adresse :", family["adresse"])
        st.metric("Nombre d'enfants", len(children))

    # ENFANTS
    with tabs[1]:
        st.subheader("Mes enfants")

        for child in children:
            with st.container(border=True):
                st.subheader(child["prenom"])
                photo_widget(child["photo"])
                st.write("Âge :", child["age"], "ans")
                st.write("Poids :", child["poids"], "kg")
                st.write("Taille :", child["taille"], "cm")
                st.write("Galop :", child["galop"])

                assigned = query("""
                    SELECT ponies.nom
                    FROM assignments
                    LEFT JOIN ponies ON ponies.id=assignments.pony_id
                    WHERE assignments.child_id=?
                    AND assignments.pony_id IS NOT NULL
                """, (child["id"],))

                poneys = sorted(set(
                    row["nom"] for row in assigned if row["nom"]
                ))

                st.write(
                    "Poney(s) attribué(s) :",
                    ", ".join(poneys) if poneys else "Pas encore attribué"
                )

        st.markdown("### Ajouter un enfant")

        with st.form("add_child_form"):
            prenom = st.text_input("Prénom")
            age = st.number_input(
                "Âge",
                min_value=3,
                max_value=99,
                value=8
            )
            poids = st.number_input(
                "Poids (kg)",
                min_value=0.0,
                value=25.0
            )
            taille = st.number_input(
                "Taille (cm)",
                min_value=0.0,
                value=120.0
            )
            galop = st.selectbox(
                "Niveau",
                [
                    "Débutant", "Galop 1", "Galop 2",
                    "Galop 3", "Galop 4", "Galop 5",
                    "Galop 6", "Galop 7"
                ]
            )
            photo = st.file_uploader(
                "Photo de l'enfant",
                type=["png", "jpg", "jpeg"]
            )

            ok = st.form_submit_button("Ajouter l'enfant")

            if ok:
                if not prenom.strip():
                    st.error("Indique le prénom.")
                else:
                    execute("""
                        INSERT INTO children
                        (family_id, prenom, age, poids, taille,
                         galop, photo, temporaire)
                        VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                    """, (
                        fid, prenom, age, poids, taille,
                        galop, photo_bytes(photo)
                    ))
                    st.success("Enfant ajouté.")
                    st.rerun()

    # PLANNING
    with tabs[2]:
        st.subheader("Mon planning hebdomadaire")

        if children:
            child = st.selectbox(
                "Choisir un enfant",
                children,
                format_func=lambda x: x["prenom"],
                key="family_planning_child"
            )

            rows = query("""
                SELECT slots.*, ponies.nom AS poney
                FROM assignments
                JOIN slots ON slots.id=assignments.slot_id
                LEFT JOIN ponies ON ponies.id=assignments.pony_id
                WHERE assignments.child_id=?
            """, (child["id"],))

            rows = sorted(
                rows,
                key=lambda r: (ordre_jours(r["jour"]), r["heure"])
            )

            if rows:
                for row in rows:
                    st.write(
                        f"**{row['jour']} à {row['heure']}** "
                        f"— {row['niveau']} "
                        f"— Poney : {row['poney'] or 'À définir'}"
                    )
            else:
                st.info("Aucun cours attribué pour le moment.")
        else:
            st.info("Ajoute d'abord un enfant.")

    # DEMI-PENSION
    with tabs[3]:
        st.subheader("Espace demi-pension")
        st.write(
            "Choisis exactement trois cours hebdomadaires. "
            "La demande devra être validée par un coach."
        )

        if children:
            child = st.selectbox(
                "Enfant concerné",
                children,
                format_func=lambda x: x["prenom"],
                key="dp_child"
            )

            slots = query("""
                SELECT * FROM slots WHERE actif=1
            """)

            slots = sorted(
                slots,
                key=lambda s: (ordre_jours(s["jour"]), s["heure"])
            )

            if slots:
                slot_names = {
                    s["id"]: slot_label(s) for s in slots
                }

                choices = st.multiselect(
                    "Choisir trois cours",
                    options=list(slot_names.keys()),
                    format_func=lambda sid: slot_names[sid],
                    max_selections=3,
                    key=f"dp_choices_{child['id']}"
                )

                if st.button(
                    "Envoyer ma demande de DP",
                    key=f"send_dp_{child['id']}"
                ):
                    if len(choices) != 3:
                        st.error("Tu dois choisir exactement trois cours.")
                    else:
                        pending = query("""
                            SELECT id FROM dp_requests
                            WHERE child_id=? AND statut='En attente'
                        """, (child["id"],))

                        if pending:
                            st.warning("Une demande est déjà en attente.")
                        else:
                            execute("""
                                INSERT INTO dp_requests
                                (child_id, slot_ids, statut)
                                VALUES (?, ?, 'En attente')
                            """, (
                                child["id"],
                                json.dumps(choices)
                            ))
                            st.success("Demande envoyée aux coachs.")
                            st.rerun()

                requests = query("""
                    SELECT * FROM dp_requests
                    WHERE child_id=? ORDER BY id DESC
                """, (child["id"],))

                for req in requests:
                    st.write("Demande :", req["statut"])
                    try:
                        for sid in json.loads(req["slot_ids"]):
                            slot = get_slot(sid)
                            if slot:
                                st.caption(slot_label(slot))
                    except (ValueError, TypeError):
                        st.caption("Détails indisponibles.")
            else:
                st.info("Aucun cours n'a encore été créé.")
        else:
            st.info("Ajoute d'abord un enfant.")

    # ABSENCES
    with tabs[4]:
        st.subheader("Absences et rattrapages")

        if children:
            child = st.selectbox(
                "Enfant concerné",
                children,
                format_func=lambda x: x["prenom"],
                key="absence_child"
            )

            slots = query("""
                SELECT * FROM slots WHERE actif=1
            """)

            slots = sorted(
                slots,
                key=lambda s: (ordre_jours(s["jour"]), s["heure"])
            )

            with st.form("absence_form"):
                type_demande = st.selectbox(
                    "Type de demande",
                    ["Signaler une absence", "Demander un rattrapage"]
                )

                slot_id = st.selectbox(
                    "Cours concerné",
                    [s["id"] for s in slots],
                    format_func=lambda sid: slot_label(get_slot(sid))
                ) if slots else None

                jour = st.date_input(
                    "Date du cours",
                    min_value=date.today()
                )
                motif = st.text_area("Message pour le coach")

                ok = st.form_submit_button("Envoyer la demande")

                if ok:
                    debut = datetime.combine(jour, time.min)

                    if debut < datetime.now() + timedelta(hours=24):
                        st.error(
                            "La demande doit être faite au moins "
                            "24 heures à l'avance."
                        )
                    elif slot_id is None:
                        st.error("Aucun cours disponible.")
                    else:
                        execute("""
                            INSERT INTO absences
                            (child_id, slot_id, date_absence, motif,
                             type_demande, statut, created_at)
                            VALUES (?, ?, ?, ?, ?, 'En attente', ?)
                        """, (
                            child["id"], slot_id, str(jour),
                            motif, type_demande,
                            datetime.now().isoformat()
                        ))
                        st.success("Demande envoyée aux coachs.")
                        st.rerun()

            for item in query("""
                SELECT * FROM absences
                WHERE child_id=? ORDER BY id DESC
            """, (child["id"],)):
                st.write(
                    f"**{item['type_demande']}** — "
                    f"{item['date_absence']} — {item['statut']}"
                )
        else:
            st.info("Ajoute d'abord un enfant.")

    # STAGES ET EVENEMENTS
    with tabs[5]:
        st.subheader("Stages")

        for stage in query("""
            SELECT * FROM stages ORDER BY date_stage
        """):
            st.write(
                f"**{stage['nom']}** — {stage['date_stage']} "
                f"— {stage['tarif']} €"
            )

        st.divider()
        st.subheader("Concours et événements")

        for event in query("""
            SELECT * FROM events ORDER BY date_event
        """):
            st.write(f"**{event['nom']}** — {event['date_event']}")
            st.write(event["description"])

    # NOTIFICATIONS
    with tabs[6]:
        st.subheader("Mes notifications")

        notifications = query("""
            SELECT * FROM notifications
            WHERE family_id=? ORDER BY id DESC
        """, (fid,))

        if not notifications:
            st.info("Aucune notification pour le moment.")

        for n in notifications:
            with st.container(border=True):
                st.write("🔔", n["message"])
                st.caption(n["date_creation"])


# =========================================================
# ESPACE COACH
# =========================================================

def coach_page():

    st.header(f"Bienvenue {st.session_state.user_name}")

    tabs = st.tabs([
        "Tableau de bord",
        "Élèves",
        "Poneys",
        "Planning",
        "Demi-pension",
        "Absences",
        "Stages",
        "Concours et événements",
        "Actualités",
        "Balades",
        "Notifications"
    ])

    # TABLEAU DE BORD
    with tabs[0]:
        st.subheader("Administration du club")

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "Familles",
            len(query("SELECT id FROM families"))
        )
        c2.metric(
            "Élèves",
            len(query("SELECT id FROM children"))
        )
        c3.metric(
            "Poneys",
            len(query("SELECT id FROM ponies WHERE actif=1"))
        )

        st.info(
            "Utilise les onglets pour gérer les familles, "
            "les poneys, les cours et les activités."
        )

    # ELEVES
    with tabs[1]:
        st.subheader("Liste des élèves")

        families = query("SELECT * FROM families ORDER BY nom")

        for family in families:
            with st.expander(f"Famille : {family['nom']}"):
                st.write("E-mail :", family["email"])
                st.write("Téléphone :", family["telephone"])
                st.write("Adresse :", family["adresse"])

                for child in get_children(family["id"]):
                    st.write(
                        f"**{child['prenom']}** — "
                        f"{child['age']} ans — {child['galop']}"
                    )

        st.divider()
        st.subheader("Ajouter un élève temporaire")

        with st.form("temporary_child_form"):
            prenom = st.text_input("Prénom et nom de l'élève")
            age = st.number_input(
                "Âge",
                min_value=3,
                max_value=99,
                value=8
            )
            galop = st.selectbox(
                "Niveau",
                [
                    "Débutant", "Galop 1", "Galop 2",
                    "Galop 3", "Galop 4", "Galop 5",
                    "Galop 6", "Galop 7"
                ],
                key="temp_galop"
            )

            ok = st.form_submit_button("Ajouter l'élève temporaire")

            if ok:
                if not prenom.strip():
                    st.error("Indique le nom de l'élève.")
                else:
                    execute("""
                        INSERT INTO children
                        (family_id, prenom, age, galop, temporaire)
                        VALUES (NULL, ?, ?, ?, 1)
                    """, (prenom, age, galop))
                    st.success("Élève temporaire ajouté.")
                    st.rerun()

        st.subheader("Élèves temporaires")

        for child in query("""
            SELECT * FROM children
            WHERE temporaire=1 ORDER BY prenom
        """):
            st.write(
                f"{child['prenom']} — {child['age']} ans "
                f"— {child['galop']}"
            )

    # PONEYS
    with tabs[2]:
        st.subheader("Gestion des poneys")

        with st.form("add_pony_form"):
            nom = st.text_input("Nom du poney")
            age = st.text_input("Âge")
            description = st.text_area("Caractère et description")
            photo = st.file_uploader(
                "Photo du poney",
                type=["png", "jpg", "jpeg"],
                key="pony_photo"
            )

            ok = st.form_submit_button("Ajouter le poney")

            if ok:
                if not nom.strip():
                    st.error("Indique le nom du poney.")
                else:
                    execute("""
                        INSERT INTO ponies
                        (nom, age, description, photo, actif)
                        VALUES (?, ?, ?, ?, 1)
                    """, (
                        nom, age, description, photo_bytes(photo)
                    ))
                    st.success("Poney ajouté.")
                    st.rerun()

        ponies = query("""
            SELECT * FROM ponies WHERE actif=1 ORDER BY nom
        """)

        for pony in ponies:
            with st.expander(pony["nom"]):
                photo_widget(pony["photo"])
                st.write("Âge :", pony["age"])
                st.write(pony["description"])

                if st.button(
                    "Retirer du club",
                    key=f"delete_pony_{pony['id']}"
                ):
                    execute(
                        "UPDATE ponies SET actif=0 WHERE id=?",
                        (pony["id"],)
                    )
                    st.rerun()

        st.divider()
        st.subheader("Attribuer un poney à un enfant")

        all_children = query("""
            SELECT * FROM children ORDER BY prenom
        """)

        slots = query("""
            SELECT * FROM slots WHERE actif=1
        """)

        if all_children and slots and ponies:
            child = st.selectbox(
                "Enfant",
                all_children,
                format_func=lambda x: x["prenom"],
                key="assign_child"
            )

            slot = st.selectbox(
                "Cours",
                slots,
                format_func=lambda x: slot_label(x),
                key="assign_slot"
            )

            pony = st.selectbox(
                "Poney",
                ponies,
                format_func=lambda x: x["nom"],
                key="assign_pony"
            )

            if st.button("Attribuer le poney"):
                execute("""
                    INSERT INTO assignments
                    (child_id, slot_id, pony_id)
                    VALUES (?, ?, ?)
                    ON CONFLICT(child_id, slot_id)
                    DO UPDATE SET pony_id=excluded.pony_id
                """, (child["id"], slot["id"], pony["id"]))

                if child["family_id"]:
                    notifier(
                        child["family_id"],
                        f"{pony['nom']} a été attribué à "
                        f"{child['prenom']} pour son cours."
                    )

                st.success("Poney attribué.")
                st.rerun()
        else:
            st.info("Il faut créer des poneys, des élèves et des cours.")

    # PLANNING
    with tabs[3]:
        st.subheader("Planning hebdomadaire")

        with st.form("add_slot_form"):
            jour = st.selectbox("Jour", JOURS)
            heure = st.time_input(
                "Heure du cours",
                value=time(14, 0)
            )
            niveau = st.selectbox(
                "Niveau",
                [
                    "Baby poney", "Débutant",
                    "Galop 1-2", "Galop 3-4",
                    "Galop 5-7", "Tous niveaux"
                ]
            )
            places = st.number_input(
                "Nombre de places",
                min_value=1,
                max_value=30,
                value=8
            )

            ok = st.form_submit_button("Ajouter le cours récurrent")

            if ok:
                execute("""
                    INSERT INTO slots
                    (jour, heure, niveau, places, actif)
                    VALUES (?, ?, ?, ?, 1)
                """, (
                    jour, heure.strftime("%H:%M"),
                    niveau, places
                ))
                st.success("Cours ajouté au planning.")
                st.rerun()

        slots = query("SELECT * FROM slots ORDER BY id")

        slots = sorted(
            slots,
            key=lambda s: (ordre_jours(s["jour"]), s["heure"])
        )

        for slot in slots:
            with st.container(border=True):
                st.write(
                    f"**{slot_label(slot)}** "
                    f"— {slot['places']} places"
                )

                if slot["actif"]:
                    c1, c2 = st.columns(2)

                    with c1:
                        if st.button(
                            "Annuler ce cours chaque semaine",
                            key=f"cancel_slot_{slot['id']}"
                        ):
                            execute("""
                                UPDATE slots SET actif=0 WHERE id=?
                            """, (slot["id"],))
                            notifier_toutes_familles(
                                f"Le cours du {slot['jour']} "
                                f"à {slot['heure']} a été annulé."
                            )
                            st.success("Cours désactivé.")
                            st.rerun()

                    with c2:
                        if st.button(
                            "Déplacer / modifier",
                            key=f"move_slot_{slot['id']}"
                        ):
                            st.session_state.edit_slot = slot["id"]

                else:
                    if st.button(
                        "Réactiver le cours",
                        key=f"react_slot_{slot['id']}"
                    ):
                        execute("""
                            UPDATE slots SET actif=1 WHERE id=?
                        """, (slot["id"],))
                        st.rerun()

        if "edit_slot" in st.session_state:
            slot = get_slot(st.session_state.edit_slot)

            if slot:
                st.divider()
                st.subheader("Déplacer le cours sélectionné")

                new_day = st.selectbox(
                    "Nouveau jour",
                    JOURS,
                    index=ordre_jours(slot["jour"]),
                    key="new_slot_day"
                )
                new_hour = st.time_input(
                    "Nouvelle heure",
                    value=datetime.strptime(
                        slot["heure"], "%H:%M"
                    ).time(),
                    key="new_slot_hour"
                )

                if st.button("Enregistrer le déplacement"):
                    execute("""
                        UPDATE slots SET jour=?, heure=? WHERE id=?
                    """, (
                        new_day,
                        new_hour.strftime("%H:%M"),
                        slot["id"]
                    ))

                    notifier_toutes_familles(
                        f"Un cours a été déplacé au "
                        f"{new_day} à {new_hour.strftime('%H:%M')}."
                    )

                    del st.session_state.edit_slot
                    st.success("Planning modifié.")
                    st.rerun()

    # DEMI-PENSION
    with tabs[4]:
        st.subheader("Demandes de demi-pension")

        requests = query("""
            SELECT dp_requests.*, children.prenom
            FROM dp_requests
            JOIN children ON children.id=dp_requests.child_id
            ORDER BY dp_requests.id DESC
        """)

        if not requests:
            st.info("Aucune demande de demi-pension.")

        for req in requests:
            with st.container(border=True):
                st.write(
                    f"**{req['prenom']}** — {req['statut']}"
                )

                try:
                    for sid in json.loads(req["slot_ids"]):
                        slot = get_slot(sid)
                        if slot:
                            st.write(slot_label(slot))
                except (ValueError, TypeError):
                    st.write("Détails des cours indisponibles.")

                if req["statut"] == "En attente":
                    c1, c2 = st.columns(2)

                    with c1:
                        if st.button(
                            "Valider la DP",
                            key=f"accept_dp_{req['id']}"
                        ):
                            try:
                                ids = json.loads(req["slot_ids"])
                                for sid in ids:
                                    execute("""
                                        INSERT INTO assignments
                                        (child_id, slot_id, pony_id)
                                        VALUES (?, ?, NULL)
                                        ON CONFLICT(child_id, slot_id)
                                        DO NOTHING
                                    """, (req["child_id"], sid))

                                execute("""
                                    UPDATE dp_requests
                                    SET statut='Validée' WHERE id=?
                                """, (req["id"],))

                                notifier_enfant(
                                    req["child_id"],
                                    "Ta demande de demi-pension a été validée."
                                )
                                st.success("Demi-pension validée.")
                                st.rerun()
                            except (ValueError, TypeError):
                                st.error("La sélection des cours est invalide.")

                    with c2:
                        if st.button(
                            "Refuser la DP",
                            key=f"refuse_dp_{req['id']}"
                        ):
                            execute("""
                                UPDATE dp_requests
                                SET statut='Refusée' WHERE id=?
                            """, (req["id"],))
                            notifier_enfant(
                                req["child_id"],
                                "Ta demande de demi-pension a été refusée."
                            )
                            st.rerun()

    # ABSENCES
    with tabs[5]:
        st.subheader("Demandes d'absences et de rattrapages")

        requests = query("""
            SELECT absences.*, children.prenom
            FROM absences
            JOIN children ON children.id=absences.child_id
            ORDER BY absences.id DESC
        """)

        if not requests:
            st.info("Aucune demande.")

        for item in requests:
            with st.container(border=True):
                st.write(
                    f"**{item['prenom']}** — "
                    f"{item['type_demande']}"
                )
                st.write("Date :", item["date_absence"])
                st.write("Motif :", item["motif"])
                st.write("Statut :", item["statut"])

                if item["statut"] == "En attente":
                    c1, c2 = st.columns(2)

                    with c1:
                        if st.button(
                            "Accepter",
                            key=f"accept_abs_{item['id']}"
                        ):
                            execute("""
                                UPDATE absences
                                SET statut='Acceptée' WHERE id=?
                            """, (item["id"],))
                            notifier_enfant(
                                item["child_id"],
                                "Ta demande a été acceptée par le club."
                            )
                            st.rerun()

                    with c2:
                        if st.button(
                            "Refuser",
                            key=f"refuse_abs_{item['id']}"
                        ):
                            execute("""
                                UPDATE absences
                                SET statut='Refusée' WHERE id=?
                            """, (item["id"],))
                            notifier_enfant(
                                item["child_id"],
                                "Ta demande a été refusée par le club."
                            )
                            st.rerun()

    # STAGES
    with tabs[6]:
        st.subheader("Créer un stage")

        with st.form("create_stage_form"):
            nom = st.text_input("Nom du stage")
            discipline = st.text_input("Discipline")
            jour = st.date_input("Date du stage")
            horaire = st.text_input("Horaires")
            niveau = st.text_input("Niveau minimum")
            places = st.number_input(
                "Nombre de places",
                min_value=1,
                max_value=100,
                value=8
            )
            tarif = st.number_input(
                "Tarif (€)",
                min_value=0.0,
                value=25.0
            )

            ok = st.form_submit_button("Publier le stage")

            if ok:
                if not nom.strip():
                    st.error("Indique le nom du stage.")
                else:
                    execute("""
                        INSERT INTO stages
                        (nom, discipline, date_stage, horaire,
                         niveau, places, tarif)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        nom, discipline, str(jour), horaire,
                        niveau, places, tarif
                    ))
                    notifier_toutes_familles(
                        f"Nouveau stage publié : {nom}, le {jour}."
                    )
                    st.success("Stage publié.")
                    st.rerun()

        st.divider()
        st.subheader("Stages publiés")

        for stage in query("SELECT * FROM stages ORDER BY date_stage"):
            with st.container(border=True):
                st.write(
                    f"**{stage['nom']}** — {stage['date_stage']} "
                    f"— {stage['tarif']} €"
                )
                inscrits = query("""
                    SELECT * FROM stage_regs WHERE stage_id=?
                """, (stage["id"],))

                st.write("Inscriptions :", len(inscrits))
                for reg in inscrits:
                    st.caption(
                        f"{reg['nom_enfant']} — {reg['nom_responsable']} "
                        f"— {reg['telephone']} — {reg['email']}"
                    )

    # CONCOURS ET EVENEMENTS
    with tabs[7]:
        st.subheader("Ajouter un concours ou un événement")

        with st.form("create_event_form"):
            nom = st.text_input("Nom du concours ou événement")
            jour = st.date_input(
                "Date",
                key="event_date"
            )
            description = st.text_area("Description")

            ok = st.form_submit_button("Publier")

            if ok:
                if not nom.strip():
                    st.error("Indique un nom.")
                else:
                    execute("""
                        INSERT INTO events
                        (nom, date_event, description)
                        VALUES (?, ?, ?)
                    """, (nom, str(jour), description))

                    notifier_toutes_familles(
                        f"Nouvel événement publié : {nom}."
                    )
                    st.success("Événement publié.")
                    st.rerun()

        st.divider()

        for event in query("""
            SELECT * FROM events ORDER BY date_event
        """):
            with st.container(border=True):
                st.write(
                    f"**{event['nom']}** — {event['date_event']}"
                )
                st.write(event["description"])

                regs = query("""
                    SELECT * FROM event_regs WHERE event_id=?
                """, (event["id"],))

                st.write("Inscriptions :", len(regs))
                for reg in regs:
                    st.caption(
                        f"{reg['nom_enfant']} — "
                        f"{reg['nom_responsable']} — {reg['telephone']}"
                    )

    # ACTUALITES
    with tabs[8]:
        st.subheader("Rédiger un article")

        with st.form("article_form"):
            titre = st.text_input("Titre de l'article")
            contenu = st.text_area(
                "Texte de l'article",
                height=180
            )
            photo = st.file_uploader(
                "Photo du club ou du concours",
                type=["png", "jpg", "jpeg"],
                key="article_photo"
            )

            ok = st.form_submit_button("Publier l'article")

            if ok:
                if not titre.strip() or not contenu.strip():
                    st.error("Le titre et le texte sont obligatoires.")
                else:
                    execute("""
                        INSERT INTO articles
                        (titre, contenu, photo, date_article)
                        VALUES (?, ?, ?, ?)
                    """, (
                        titre, contenu, photo_bytes(photo),
                        date.today().strftime("%d/%m/%Y")
                    ))
                    notifier_toutes_familles(
                        f"Nouvel article : {titre}."
                    )
                    st.success("Article publié.")
                    st.rerun()

        st.divider()
        st.subheader("Articles publiés")

        for article in query("""
            SELECT * FROM articles ORDER BY id DESC
        """):
            with st.expander(article["titre"]):
                photo_widget(article["photo"])
                st.write(article["contenu"])
                st.caption(article["date_article"])

    # BALADES
    with tabs[9]:
        st.subheader("Demandes de balades")

        bookings = query("""
            SELECT * FROM walk_bookings
            ORDER BY date_balade, heure
        """)

        if not bookings:
            st.info("Aucune demande de balade.")

        for booking in bookings:
            with st.container(border=True):
                st.write(f"**{booking['enfant']}**")
                st.write("Responsable :", booking["responsable"])
                st.write("Téléphone :", booking["telephone"])
                st.write("E-mail :", booking["email"])
                st.write("Date :", booking["date_balade"])
                st.write("Heure :", booking["heure"])
                st.write("Tarif :", booking["tarif"], "€")
                st.write("Statut :", booking["statut"])

                if booking["statut"] == "En attente":
                    c1, c2 = st.columns(2)

                    with c1:
                        if st.button(
                            "Confirmer",
                            key=f"confirm_walk_{booking['id']}"
                        ):
                            execute("""
                                UPDATE walk_bookings
                                SET statut='Confirmée' WHERE id=?
                            """, (booking["id"],))
                            st.rerun()

                    with c2:
                        if st.button(
                            "Refuser",
                            key=f"refuse_walk_{booking['id']}"
                        ):
                            execute("""
                                UPDATE walk_bookings
                                SET statut='Refusée' WHERE id=?
                            """, (booking["id"],))
                            st.rerun()

    # NOTIFICATIONS
    with tabs[10]:
        st.subheader("Envoyer une notification")

        with st.form("notification_form"):
            message = st.text_area("Message à envoyer aux familles")
            ok = st.form_submit_button("Envoyer")

            if ok:
                if not message.strip():
                    st.error("Écris un message.")
                else:
                    notifier_toutes_familles(message)
                    st.success("Notification ajoutée aux espaces familles.")


# =========================================================
# NAVIGATION
# =========================================================

if st.session_state.role == "family":
    col1, col2 = st.columns([5, 1])
    with col2:
        if st.button("Déconnexion"):
            logout()
    family_page()

elif st.session_state.role == "coach":
    col1, col2 = st.columns([5, 1])
    with col2:
        if st.button("Déconnexion"):
            logout()
    coach_page()

else:
    public_page()
