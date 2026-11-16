
import streamlit as st
import sqlite3
import hashlib
import secrets
import json
from datetime import date, datetime, time, timedelta

# =========================================================
# AC EQUITATION
# =========================================================

st.set_page_config(
    page_title="AC Équitation",
    page_icon="🐴",
    layout="wide"
)

DB = "ac_equitation.db"

JOURS = [
    "Lundi", "Mardi", "Mercredi", "Jeudi",
    "Vendredi", "Samedi", "Dimanche"
]

NIVEAUX = [
    "Baby poney", "Débutant", "Galop 1",
    "Galop 2", "Galop 3", "Galop 4",
    "Galop 5", "Galop 6", "Galop 7",
    "Tous niveaux"
]

# =========================================================
# DESIGN
# =========================================================

st.markdown("""
<style>
.stApp {
    background: #f5f4ed;
}
h1, h2, h3 {
    color: #405b49;
}
.stButton button {
    background: #607b65;
    color: white;
    border-radius: 10px;
    border: none;
}
.stButton button:hover {
    background: #405b49;
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
# CONNEXION BASE DE DONNEES
# =========================================================

def connect():
    db = sqlite3.connect(DB, timeout=30)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def execute(sql, values=()):
    with connect() as db:
        db.execute(sql, values)
        db.commit()


def query(sql, values=()):
    with connect() as db:
        return db.execute(sql, values).fetchall()


def add_column(table, column, definition):
    columns = [
        row["name"]
        for row in query(f"PRAGMA table_info({table})")
    ]
    if column not in columns:
        execute(
            f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
        )


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
            nom TEXT UNIQUE NOT NULL,
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

        CREATE TABLE IF NOT EXISTS exceptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slot_id INTEGER NOT NULL,
            date_cours TEXT NOT NULL,
            action TEXT NOT NULL,
            nouveau_jour TEXT,
            nouvelle_heure TEXT,
            message TEXT
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

    # Compatibilité avec les anciennes versions de la base
    add_column("coaches", "identifiant", "TEXT")
    add_column("children", "temporaire", "INTEGER DEFAULT 0")
    add_column("ponies", "actif", "INTEGER DEFAULT 1")
    add_column("slots", "actif", "INTEGER DEFAULT 1")


init_db()

# =========================================================
# MOTS DE PASSE ET COACHS
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


def configure_coaches():
    comptes = [
        ("Coach 1", "coach1", "COACH1_PASSWORD"),
        ("Coach 2", "coach2", "COACH2_PASSWORD")
    ]

    for nom, identifiant, secret_name in comptes:
        password = st.secrets.get(secret_name, "")

        if not password:
            continue

        old = query(
            "SELECT id FROM coaches WHERE nom=?",
            (nom,)
        )

        hashed = hash_password(password)

        if old:
            execute("""
                UPDATE coaches
                SET password=?, identifiant=?
                WHERE nom=?
            """, (hashed, identifiant, nom))
        else:
            execute("""
                INSERT INTO coaches (nom, password, identifiant)
                VALUES (?, ?, ?)
            """, (nom, hashed, identifiant))


try:
    configure_coaches()
except Exception:
    pass

# =========================================================
# OUTILS
# =========================================================

def notify(family_id, message):
    if family_id:
        execute("""
            INSERT INTO notifications
            (family_id, message, date_creation)
            VALUES (?, ?, ?)
        """, (
            family_id,
            message,
            datetime.now().strftime("%d/%m/%Y %H:%M")
        ))


def notify_child(child_id, message):
    rows = query(
        "SELECT family_id FROM children WHERE id=?",
        (child_id,)
    )
    if rows and rows[0]["family_id"]:
        notify(rows[0]["family_id"], message)


def photo_widget(photo):
    if photo:
        st.image(photo, use_container_width=True)


def get_children(family_id):
    return query("""
        SELECT * FROM children
        WHERE family_id=?
        ORDER BY prenom
    """, (family_id,))


def get_slot(slot_id):
    rows = query(
        "SELECT * FROM slots WHERE id=?",
        (slot_id,)
    )
    return rows[0] if rows else None


def slot_label(slot):
    return (
        f"{slot['jour']} à {slot['heure']} "
        f"— {slot['niveau']}"
    )


def ordered_slots(active_only=True):
    condition = "WHERE actif=1" if active_only else ""
    return query(f"""
        SELECT * FROM slots
        {condition}
        ORDER BY
        CASE jour
            WHEN 'Lundi' THEN 1
            WHEN 'Mardi' THEN 2
            WHEN 'Mercredi' THEN 3
            WHEN 'Jeudi' THEN 4
            WHEN 'Vendredi' THEN 5
            WHEN 'Samedi' THEN 6
            ELSE 7
        END, heure
    """)


# =========================================================
# SESSION
# =========================================================

for key, value in {
    "role": None,
    "user_id": None,
    "user_name": None
}.items():
    if key not in st.session_state:
        st.session_state[key] = value


def logout():
    st.session_state.role = None
    st.session_state.user_id = None
    st.session_state.user_name = None
    st.rerun()


# =========================================================
# EN-TETE
# =========================================================

st.title("🐴 AC ÉQUITATION")
st.caption("Le club, les poneys et les cavaliers réunis au même endroit.")
st.divider()


# =========================================================
# ESPACE PUBLIC
# =========================================================

def public_page():

    tabs = st.tabs([
        "Accueil",
        "Nos poneys",
        "Planning",
        "Stages",
        "Concours",
        "Actualités",
        "Balades",
        "Connexion",
        "Créer un compte"
    ])

    with tabs[0]:
        st.header("Bienvenue chez AC Équitation 🌿")
        st.write(
            "Retrouvez ici les informations du club, "
            "les poneys, les horaires, les stages et les actualités."
        )

        st.subheader("À la une")

        for article in query(
            "SELECT * FROM articles ORDER BY id DESC LIMIT 3"
        ):
            with st.container(border=True):
                st.subheader(article["titre"])
                photo_widget(article["photo"])
                st.write(article["contenu"])
                st.caption(article["date_article"])

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
                st.write("Âge :", pony["age"])
                st.write(pony["description"])

    with tabs[2]:
        st.header("Planning hebdomadaire")

        slots = ordered_slots()

        if not slots:
            st.info("Le planning sera bientôt disponible.")

        for slot in slots:
            st.write(
                f"**{slot['jour']} — {slot['heure']}** "
                f"• {slot['niveau']} • {slot['places']} places"
            )

    with tabs[3]:
        st.header("Les stages")

        for stage in query(
            "SELECT * FROM stages ORDER BY date_stage"
        ):
            inscrits = query("""
                SELECT COUNT(*) AS total
                FROM stage_regs WHERE stage_id=?
            """, (stage["id"],))[0]["total"]

            restantes = max(0, stage["places"] - inscrits)

            with st.container(border=True):
                st.subheader(stage["nom"])
                st.write("Discipline :", stage["discipline"])
                st.write("Date :", stage["date_stage"])
                st.write("Horaires :", stage["horaire"])
                st.write("Niveau minimum :", stage["niveau"])
                st.write("Places restantes :", restantes)
                st.write("Tarif :", stage["tarif"], "€")

                with st.form(f"stage_public_{stage['id']}"):
                    enfant = st.text_input("Prénom et nom de l'enfant")
                    responsable = st.text_input(
                        "Prénom et nom du responsable"
                    )
                    tel = st.text_input("Téléphone")
                    email = st.text_input("Adresse e-mail")

                    ok = st.form_submit_button("S'inscrire")

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
                            st.success("Inscription envoyée.")

    with tabs[4]:
        st.header("Concours et événements")

        events = query(
            "SELECT * FROM events ORDER BY date_event"
        )

        if not events:
            st.info("Aucun événement publié pour le moment.")

        for event in events:
            with st.container(border=True):
                st.subheader(event["nom"])
                st.write(event["date_event"])
                st.write(event["description"])

    with tabs[5]:
        st.header("Actualités du club")

        for article in query(
            "SELECT * FROM articles ORDER BY id DESC"
        ):
            with st.container(border=True):
                st.subheader(article["titre"])
                photo_widget(article["photo"])
                st.write(article["contenu"])
                st.caption(article["date_article"])

    with tabs[6]:
        st.header("Réserver une balade à poney")
        st.write("Réservation sans création de compte.")

        with st.form("walk_form"):
            enfant = st.text_input("Prénom et nom de l'enfant")
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
                "Tarif (€)",
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
                    "Mot de passe",
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
                        (identifiant.strip().lower(),)
                    )

                    if coaches and check_password(
                        password, coaches[0]["password"]
                    ):
                        st.session_state.role = "coach"
                        st.session_state.user_id = coaches[0]["id"]
                        st.session_state.user_name = coaches[0]["nom"]
                        st.rerun()
                    else:
                        st.error("Identifiant ou mot de passe coach incorrect.")

    # CREATION COMPTE FAMILLE
    with tabs[8]:
        st.header("Créer un compte famille")
        st.write(
            "Un compte parent permet de gérer plusieurs enfants."
        )

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
                    st.error("8 caractères minimum.")
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
                    st.success("Compte créé ! Tu peux te connecter.")


# =========================================================
# ESPACE FAMILLE
# =========================================================

def family_page():

    fid = st.session_state.user_id
    rows = query("SELECT * FROM families WHERE id=?", (fid,))

    if not rows:
        st.error("Compte introuvable.")
        logout()
        return

    family = rows[0]
    children = get_children(fid)

    st.header(f"Bonjour {family['nom']} !")

    tabs = st.tabs([
        "Accueil",
        "Mes enfants",
        "Mon planning",
        "Demi-pension",
        "Absences",
        "Stages et concours",
        "Notifications"
    ])

    with tabs[0]:
        st.subheader("Mon espace famille")
        st.write("E-mail :", family["email"])
        st.write("Téléphone :", family["telephone"])
        st.write("Adresse :", family["adresse"])
        st.metric("Nombre d'enfants", len(children))

    with tabs[1]:
        st.subheader("Mes enfants")

        for child in children:
            with st.container(border=True):
                st.subheader(child["prenom"])
                photo_widget(child["photo"])
                st.write("Âge :", child["age"])
                st.write("Poids :", child["poids"], "kg")
                st.write("Taille :", child["taille"], "cm")
                st.write("Galop :", child["galop"])

        st.markdown("### Ajouter un enfant")

        with st.form("add_child_form"):
            prenom = st.text_input("Prénom")
            age = st.number_input("Âge", 3, 99, 8)
            poids = st.number_input("Poids (kg)", 0.0, 150.0, 25.0)
            taille = st.number_input("Taille (cm)", 0.0, 220.0, 120.0)
            galop = st.selectbox("Niveau", NIVEAUX)
            photo = st.file_uploader(
                "Photo de l'enfant",
                type=["png", "jpg", "jpeg"]
            )

            ok = st.form_submit_button("Ajouter l'enfant")

            if ok and prenom.strip():
                execute("""
                    INSERT INTO children
                    (family_id, prenom, age, poids, taille, galop, photo)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    fid, prenom, age, poids, taille, galop,
                    photo.getvalue() if photo else None
                ))
                st.success("Enfant ajouté.")
                st.rerun()

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
                ORDER BY slots.jour, slots.heure
            """, (child["id"],))

            if rows:
                for row in rows:
                    st.write(
                        f"**{row['jour']} à {row['heure']}** "
                        f"— {row['niveau']} — "
                        f"Poney : {row['poney'] or 'À définir'}"
                    )
            else:
                st.info("Aucun cours attribué.")
        else:
            st.info("Ajoute d'abord un enfant.")

    # DEMI-PENSION : CHOIX DE 3 COURS
    with tabs[3]:
        st.subheader("Espace demi-pension")
        st.write(
            "Choisis trois cours hebdomadaires. "
            "La demande sera validée ou refusée par un coach."
        )

        if children:
            child = st.selectbox(
                "Enfant concerné",
                children,
                format_func=lambda x: x["prenom"],
                key="dp_child"
            )

            slots = ordered_slots()

            if slots:
                slot_ids = [s["id"] for s in slots]
                names = {s["id"]: slot_label(s) for s in slots}

                choices = st.multiselect(
                    "Choisir exactement 3 cours",
                    slot_ids,
                    format_func=lambda sid: names[sid],
                    max_selections=3,
                    key=f"dp_choices_{child['id']}"
                )

                if st.button(
                    "Envoyer ma demande",
                    key=f"send_dp_{child['id']}"
                ):
                    if len(choices) != 3:
                        st.error("Tu dois choisir exactement 3 cours.")
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
                                child["id"], json.dumps(choices)
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
                except Exception:
                    st.caption("Détails indisponibles.")
        else:
            st.info("Ajoute un enfant avant de demander une DP.")

    # ABSENCES ET RATTRAPAGES
    with tabs[4]:
        st.subheader("Absences et rattrapages")

        if children:
            child = st.selectbox(
                "Enfant concerné",
                children,
                format_func=lambda x: x["prenom"],
                key="absence_child"
            )

            slots = ordered_slots()

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
                        st.error("La demande doit être faite au moins 24 h à l'avance.")
                    elif slot_id is None:
                        st.error("Aucun cours disponible.")
                    else:
                        execute("""
                            INSERT INTO absences
                            (child_id, slot_id, date_absence, motif,
                             type_demande, created_at)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            child["id"], slot_id, str(jour),
                            motif, type_demande,
                            datetime.now().isoformat()
                        ))
                        st.success("Demande envoyée.")
                        st.rerun()

            for item in query("""
                SELECT * FROM absences
                WHERE child_id=? ORDER BY id DESC
            """, (child["id"],)):
                st.write(
                    f"**{item['type_demande']}** — "
                    f"{item['date_absence']} — {item['statut']}"
                )

    with tabs[5]:
        st.subheader("Stages")

        for stage in query(
            "SELECT * FROM stages ORDER BY date_stage"
        ):
            st.write(
                f"**{stage['nom']}** — {stage['date_stage']} "
                f"— {stage['tarif']} €"
            )

        st.divider()
        st.subheader("Concours et événements")

        for event in query(
            "SELECT * FROM events ORDER BY date_event"
        ):
            st.write(f"**{event['nom']}** — {event['date_event']}")
            st.write(event["description"])

    with tabs[6]:
        st.subheader("Mes notifications")

        notifications = query("""
            SELECT * FROM notifications
            WHERE family_id=? ORDER BY id DESC
        """, (fid,))

        if not notifications:
            st.info("Aucune notification.")

        for n in notifications:
            with st.container(border=True):
                st.write("🔔", n["message"])
                st.caption(n["date_creation"])

                if not n["lu"]:
                    if st.button(
                        "Marquer comme lue",
                        key=f"read_{n['id']}"
                    ):
                        execute(
                            "UPDATE notifications SET lu=1 WHERE id=?",
                            (n["id"],)
                        )
                        st.rerun()


# =========================================================
# ESPACE COACH
# =========================================================

def coach_page():

    st.header(f"Espace coach — {st.session_state.user_name}")

    tabs = st.tabs([
        "Accueil",
        "Élèves",
        "Poneys",
        "Planning",
        "Demandes DP",
        "Absences",
        "Stages",
        "Concours",
        "Articles",
        "Balades",
        "Inscriptions stages"
    ])

    # ACCUEIL
    with tabs[0]:
        st.subheader("Tableau de bord")

        c1, c2, c3 = st.columns(3)
        c1.metric("Familles", len(query("SELECT id FROM families")))
        c2.metric("Élèves", len(query("SELECT id FROM children")))
        c3.metric(
            "Poneys",
            len(query("SELECT id FROM ponies WHERE actif=1"))
        )

        st.write("Bienvenue dans la gestion du club AC Équitation.")

    # ELEVES
    with tabs[1]:
        st.subheader("Gestion des élèves")

        with st.expander("Ajouter un élève temporaire"):
            with st.form("temporary_student"):
                prenom = st.text_input("Prénom de l'élève")
                age = st.number_input("Âge", 3, 99, 8)
                niveau = st.selectbox("Niveau", NIVEAUX)

                ok = st.form_submit_button("Ajouter")

                if ok and prenom.strip():
                    execute("""
                        INSERT INTO children
                        (family_id, prenom, age, galop, temporaire)
                        VALUES (NULL, ?, ?, ?, 1)
                    """, (prenom, age, niveau))
                    st.success("Élève temporaire ajouté.")
                    st.rerun()

        students = query("""
            SELECT children.*, families.nom AS famille
            FROM children
            LEFT JOIN families ON children.family_id=families.id
            ORDER BY children.prenom
        """)

        ponies = query(
            "SELECT * FROM ponies WHERE actif=1 ORDER BY nom"
        )

        for child in students:
            with st.container(border=True):
                st.subheader(child["prenom"])

                st.caption(
                    "Famille : " + child["famille"]
                    if child["famille"] else "Élève temporaire"
                )

                st.write(
                    f"{child['age']} ans • {child['poids']} kg "
                    f"• {child['taille']} cm • {child['galop']}"
                )
                photo_widget(child["photo"])

                if ponies:
                    current = query("""
                        SELECT pony_id FROM assignments
                        WHERE child_id=? AND pony_id IS NOT NULL
                        LIMIT 1
                    """, (child["id"],))

                    pony_ids = [p["id"] for p in ponies]
                    selected = st.selectbox(
                        "Attribuer un poney",
                        pony_ids,
                        format_func=lambda pid: next(
                            p["nom"] for p in ponies if p["id"] == pid
                        ),
                        index=(
                            pony_ids.index(current[0]["pony_id"])
                            if current and current[0]["pony_id"] in pony_ids
                            else 0
                        ),
                        key=f"pony_{child['id']}"
                    )

                    if st.button(
                        "Enregistrer le poney",
                        key=f"savepony_{child['id']}"
                    ):
                        assignments = query(
                            "SELECT id FROM assignments WHERE child_id=?",
                            (child["id"],)
                        )

                        if assignments:
                            execute("""
                                UPDATE assignments SET pony_id=?
                                WHERE child_id=?
                            """, (selected, child["id"]))
                        else:
                            st.warning(
                                "Inscris d'abord cet élève à un cours."
                            )

                        st.rerun()

    # PONEYS
    with tabs[2]:
        st.subheader("Gestion des poneys")

        with st.form("pony_form"):
            nom = st.text_input("Nom du poney")
            age = st.text_input("Âge")
            description = st.text_area("Caractère et description")
            photo = st.file_uploader(
                "Photo du poney",
                type=["png", "jpg", "jpeg"],
                key="pony_photo"
            )

            ok = st.form_submit_button("Ajouter le poney")

            if ok and nom.strip():
                execute("""
                    INSERT INTO ponies (nom, age, description, photo)
                    VALUES (?, ?, ?, ?)
                """, (
                    nom, age, description,
                    photo.getvalue() if photo else None
                ))
                st.success("Poney ajouté.")
                st.rerun()

        for pony in query("SELECT * FROM ponies ORDER BY nom"):
            with st.container(border=True):
                st.subheader(pony["nom"])
                photo_widget(pony["photo"])
                st.write(pony["age"])
                st.write(pony["description"])

                if pony["actif"]:
                    if st.button(
                        "Désactiver cette fiche",
                        key=f"disablepony_{pony['id']}"
                    ):
                        execute(
                            "UPDATE ponies SET actif=0 WHERE id=?",
                            (pony["id"],)
                        )
                        st.rerun()
                else:
                    st.caption("Fiche désactivée")

    # PLANNING
    with tabs[3]:
        st.subheader("Planning hebdomadaire")
        st.write("Les créneaux créés ici reviennent chaque semaine.")

        with st.form("slot_form"):
            jour = st.selectbox("Jour", JOURS)
            heure = st.time_input("Heure du cours", value=time(14, 0))
            niveau = st.selectbox("Niveau", NIVEAUX)
            places = st.number_input(
                "Nombre de places",
                min_value=1,
                max_value=20,
                value=8
            )

            ok = st.form_submit_button("Ajouter le cours récurrent")

            if ok:
                execute("""
                    INSERT INTO slots (jour, heure, niveau, places)
                    VALUES (?, ?, ?, ?)
                """, (jour, heure.strftime("%H:%M"), niveau, places))
                st.success("Cours ajouté.")
                st.rerun()

        slots = ordered_slots(active_only=False)

        st.markdown("### Les cours de la semaine")

        for slot in slots:
            with st.container(border=True):
                st.write(
                    f"**{slot_label(slot)}** — {slot['places']} places "
                    f"— {'Actif' if slot['actif'] else 'Désactivé'}"
                )

                c1, c2 = st.columns(2)

                with c1:
                    if slot["actif"]:
                        if st.button(
                            "Désactiver",
                            key=f"disable_slot_{slot['id']}"
                        ):
                            execute(
                                "UPDATE slots SET actif=0 WHERE id=?",
                                (slot["id"],)
                            )
                            st.rerun()

                with c2:
                    if not slot["actif"]:
                        if st.button(
                            "Réactiver",
                            key=f"activate_slot_{slot['id']}"
                        ):
                            execute(
                                "UPDATE slots SET actif=1 WHERE id=?",
                                (slot["id"],)
                            )
                            st.rerun()

        # ANNULATION OU DEPLACEMENT D'UNE SEANCE
        st.divider()
        st.subheader("Annuler ou déplacer un cours à une date précise")

        active_slots = ordered_slots()

        if active_slots:
            selected_slot = st.selectbox(
                "Cours concerné",
                [s["id"] for s in active_slots],
                format_func=lambda sid: slot_label(get_slot(sid)),
                key="exception_slot"
            )

            date_cours = st.date_input(
                "Date du cours",
                min_value=date.today(),
                key="exception_date"
            )

            action = st.radio(
                "Action",
                [
                    "Annuler uniquement cette séance",
                    "Déplacer uniquement cette séance"
                ],
                key="exception_action"
            )

            new_day = None
            new_time = None

            if action.startswith("Déplacer"):
                new_day = st.selectbox(
                    "Nouveau jour",
                    JOURS,
                    key="exception_new_day"
                )
                new_time = st.time_input(
                    "Nouvelle heure",
                    value=time(14, 0),
                    key="exception_new_time"
                )

            message = st.text_input(
                "Message à afficher aux familles"
            )

            if st.button("Enregistrer la modification"):
                action_db = (
                    "Annulé" if action.startswith("Annuler")
                    else "Déplacé"
                )

                execute("""
                    INSERT INTO exceptions
                    (slot_id, date_cours, action, nouveau_jour,
                     nouvelle_heure, message)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    selected_slot,
                    str(date_cours),
                    action_db,
                    new_day,
                    new_time.strftime("%H:%M") if new_time else None,
                    message
                ))

                assigned = query("""
                    SELECT DISTINCT children.family_id
                    FROM assignments
                    JOIN children ON children.id=assignments.child_id
                    WHERE assignments.slot_id=?
                """, (selected_slot,))

                for item in assigned:
                    notify(
                        item["family_id"],
                        f"Cours du {date_cours} : {action_db}. {message}"
                    )

                st.success("Modification enregistrée.")
                st.rerun()

        # INSCRIRE UN ELEVE A UN COURS
        st.divider()
        st.subheader("Inscrire un élève à un cours")

        students = query("SELECT * FROM children ORDER BY prenom")
        active_slots = ordered_slots()

        if students and active_slots:
            student_id = st.selectbox(
                "Élève",
                [s["id"] for s in students],
                format_func=lambda sid: next(
                    s["prenom"] for s in students if s["id"] == sid
                ),
                key="assign_student"
            )

            slot_id = st.selectbox(
                "Cours",
                [s["id"] for s in active_slots],
                format_func=lambda sid: slot_label(get_slot(sid)),
                key="assign_slot"
            )

            if st.button("Inscrire au cours"):
                count = query("""
                    SELECT COUNT(*) AS total
                    FROM assignments WHERE slot_id=?
                """, (slot_id,))[0]["total"]

                already = query("""
                    SELECT id FROM assignments
                    WHERE child_id=? AND slot_id=?
                """, (student_id, slot_id))

                slot = get_slot(slot_id)

                if already:
                    st.warning("Cet élève est déjà inscrit.")
                elif count >= slot["places"]:
                    st.error("Ce cours est complet.")
                else:
                    execute("""
                        INSERT INTO assignments (child_id, slot_id)
                        VALUES (?, ?)
                    """, (student_id, slot_id))

                    notify_child(
                        student_id,
                        "Un cours a été ajouté à ton planning."
                    )
                    st.success("Élève inscrit.")
                    st.rerun()

    # DEMANDES DP
    with tabs[4]:
        st.subheader("Demandes de demi-pension")

        requests = query("""
            SELECT dp_requests.*, children.prenom, children.family_id
            FROM dp_requests
            JOIN children ON children.id=dp_requests.child_id
            ORDER BY dp_requests.id DESC
        """)

        for req in requests:
            with st.container(border=True):
                st.subheader(req["prenom"])
                st.write("Statut :", req["statut"])

                try:
                    ids = json.loads(req["slot_ids"])
                except Exception:
                    ids = []

                for sid in ids:
                    slot = get_slot(sid)
                    if slot:
                        st.write(slot_label(slot))

                if req["statut"] == "En attente":
                    c1, c2 = st.columns(2)

                    with c1:
                        if st.button(
                            "Valider la DP",
                            key=f"accept_dp_{req['id']}"
                        ):
                            possible = True

                            for sid in ids:
                                slot = get_slot(sid)
                                if not slot or not slot["actif"]:
                                    possible = False
                                    break

                                count = query("""
                                    SELECT COUNT(*) AS total
                                    FROM assignments WHERE slot_id=?
                                """, (sid,))[0]["total"]

                                already = query("""
                                    SELECT id FROM assignments
                                    WHERE child_id=? AND slot_id=?
                                """, (req["child_id"], sid))

                                if not already and count >= slot["places"]:
                                    possible = False
                                    break

                            if not possible:
                                st.error(
                                    "Un cours est complet ou indisponible."
                                )
                            else:
                                for sid in ids:
                                    execute("""
                                        INSERT OR IGNORE INTO assignments
                                        (child_id, slot_id)
                                        VALUES (?, ?)
                                    """, (req["child_id"], sid))

                                execute("""
                                    UPDATE dp_requests
                                    SET statut='Validée'
                                    WHERE id=?
                                """, (req["id"],))

                                notify(
                                    req["family_id"],
                                    "La demande de demi-pension a été validée."
                                )
                                st.success("Demande validée.")
                                st.rerun()

                    with c2:
                        if st.button(
                            "Refuser",
                            key=f"refuse_dp_{req['id']}"
                        ):
                            execute("""
                                UPDATE dp_requests
                                SET statut='Refusée'
                                WHERE id=?
                            """, (req["id"],))

                            notify(
                                req["family_id"],
                                "La demande de demi-pension a été refusée."
                            )
                            st.rerun()

    # ABSENCES ET RATTRAPAGES
    with tabs[5]:
        st.subheader("Absences et rattrapages")

        absences = query("""
            SELECT absences.*, children.prenom, children.family_id
            FROM absences
            JOIN children ON children.id=absences.child_id
            ORDER BY absences.id DESC
        """)

        for absence in absences:
            with st.container(border=True):
                st.subheader(absence["prenom"])
                st.write(absence["type_demande"])
                st.write("Date :", absence["date_absence"])
                st.write("Motif :", absence["motif"])
                st.write("Statut :", absence["statut"])

                if absence["statut"] == "En attente":
                    c1, c2 = st.columns(2)

                    with c1:
                        if st.button(
                            "Accepter",
                            key=f"accept_abs_{absence['id']}"
                        ):
                            execute("""
                                UPDATE absences
                                SET statut='Acceptée'
                                WHERE id=?
                            """, (absence["id"],))

                            notify(
                                absence["family_id"],
                                f"{absence['type_demande']} acceptée."
                            )
                            st.rerun()

                    with c2:
                        if st.button(
                            "Refuser",
                            key=f"refuse_abs_{absence['id']}"
                        ):
                            execute("""
                                UPDATE absences
                                SET statut='Refusée'
                                WHERE id=?
                            """, (absence["id"],))

                            notify(
                                absence["family_id"],
                                f"{absence['type_demande']} refusée."
                            )
                            st.rerun()

    # STAGES
    with tabs[6]:
        st.subheader("Créer un stage")

        with st.form("create_stage"):
            nom = st.text_input("Nom du stage")
            discipline = st.text_input("Discipline")
            jour = st.date_input("Date du stage")
            horaire = st.text_input("Horaires", "9h-17h")
            niveau = st.text_input("Niveau minimum")
            places = st.number_input(
                "Nombre de places",
                min_value=1,
                value=8
            )
            tarif = st.number_input("Tarif (€)", min_value=0.0)

            ok = st.form_submit_button("Publier le stage")

            if ok and nom.strip():
                execute("""
                    INSERT INTO stages
                    (nom, discipline, date_stage, horaire,
                     niveau, places, tarif)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    nom, discipline, str(jour),
                    horaire, niveau, places, tarif
                ))
                st.success("Stage publié.")
                st.rerun()

        for stage in query("SELECT * FROM stages ORDER BY date_stage"):
            st.write(
                f"**{stage['nom']}** — {stage['date_stage']} "
                f"— {stage['tarif']} €"
            )

    # CONCOURS ET EVENEMENTS
    with tabs[7]:
        st.subheader("Ajouter un concours ou un événement")

        with st.form("create_event"):
            nom = st.text_input("Nom")
            jour = st.date_input("Date", key="event_date")
            description = st.text_area("Description")

            ok = st.form_submit_button("Publier")

            if ok and nom.strip():
                execute("""
                    INSERT INTO events (nom, date_event, description)
                    VALUES (?, ?, ?)
                """, (nom, str(jour), description))
                st.success("Événement publié.")
                st.rerun()

        for event in query(
            "SELECT * FROM events ORDER BY date_event"
        ):
            st.write(f"**{event['nom']}** — {event['date_event']}")
            st.write(event["description"])

    # ARTICLES
    with tabs[8]:
        st.subheader("Rédiger un article")

        with st.form("article_form"):
            titre = st.text_input("Titre")
            contenu = st.text_area("Texte de l'article")
            photo = st.file_uploader(
                "Photo",
                type=["png", "jpg", "jpeg"],
                key="article_photo"
            )

            ok = st.form_submit_button("Publier l'article")

            if ok and titre.strip() and contenu.strip():
                execute("""
                    INSERT INTO articles
                    (titre, contenu, photo, date_article)
                    VALUES (?, ?, ?, ?)
                """, (
                    titre,
                    contenu,
                    photo.getvalue() if photo else None,
                    date.today().strftime("%d/%m/%Y")
                ))
                st.success("Article publié.")
                st.rerun()

        for article in query(
            "SELECT * FROM articles ORDER BY id DESC"
        ):
            with st.container(border=True):
                st.subheader(article["titre"])
                photo_widget(article["photo"])
                st.write(article["contenu"])
                st.caption(article["date_article"])

    # BALADES
    with tabs[9]:
        st.subheader("Réservations de balades")

        for booking in query("""
            SELECT * FROM walk_bookings
            ORDER BY date_balade, heure
        """):
            with st.container(border=True):
                st.subheader(booking["enfant"])
                st.write("Responsable :", booking["responsable"])
                st.write("Téléphone :", booking["telephone"])
                st.write("E-mail :", booking["email"])
                st.write(
                    booking["date_balade"],
                    "à",
                    booking["heure"]
                )
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
                                SET statut='Confirmée'
                                WHERE id=?
                            """, (booking["id"],))
                            st.rerun()

                    with c2:
                        if st.button(
                            "Refuser",
                            key=f"refuse_walk_{booking['id']}"
                        ):
                            execute("""
                                UPDATE walk_bookings
                                SET statut='Refusée'
                                WHERE id=?
                            """, (booking["id"],))
                            st.rerun()

    # INSCRIPTIONS AUX STAGES
    with tabs[10]:
        st.subheader("Inscriptions aux stages")

        registrations = query("""
            SELECT stage_regs.*, stages.nom AS stage
            FROM stage_regs
            JOIN stages ON stages.id=stage_regs.stage_id
            ORDER BY stage_regs.id DESC
        """)

        for reg in registrations:
            with st.container(border=True):
                st.write("**" + reg["nom_enfant"] + "**")
                st.write("Stage :", reg["stage"])
                st.write("Responsable :", reg["nom_responsable"])
                st.write("Téléphone :", reg["telephone"])
                st.write("E-mail :", reg["email"])


# =========================================================
# NAVIGATION GENERALE
# =========================================================

if st.session_state.role == "family":
    if st.button("Déconnexion"):
        logout()
    family_page()

elif st.session_state.role == "coach":
    if st.button("Déconnexion"):
        logout()
    coach_page()

else:
    public_page()
