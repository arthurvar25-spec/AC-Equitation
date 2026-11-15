
import streamlit as st
import sqlite3
import hashlib
import secrets
from datetime import date, time, datetime, timedelta

# =========================================================
# AC EQUITATION
# Application de gestion du club
# =========================================================

st.set_page_config(
    page_title="AC Équitation",
    page_icon="🐴",
    layout="wide"
)

DB = "ac_equitation.db"

# =========================================================
# DESIGN
# =========================================================

st.markdown("""
<style>
.stApp {
    background-color: #F7F6F0;
}
h1, h2, h3 {
    color: #526B53;
}
section[data-testid="stSidebar"] {
    background-color: #E5EBDD;
}
div.stButton > button {
    background-color: #71866B;
    color: white;
    border-radius: 10px;
    border: none;
}
div.stButton > button:hover {
    background-color: #526B53;
    color: white;
}
div[data-testid="stForm"] {
    background-color: white;
    padding: 18px;
    border-radius: 12px;
}
</style>
""", unsafe_allow_html=True)


# =========================================================
# BASE DE DONNEES
# =========================================================

def connect():
    con = sqlite3.connect(DB)
    con.execute("PRAGMA foreign_keys = ON")
    return con


def init_db():
    con = connect()
    cur = con.cursor()

    cur.executescript("""
    CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        salt TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL,
        family_name TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS children (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        family_id INTEGER,
        name TEXT NOT NULL,
        birth TEXT,
        level TEXT,
        FOREIGN KEY(family_id) REFERENCES accounts(id)
    );

    CREATE TABLE IF NOT EXISTS ponies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        age TEXT,
        description TEXT,
        photo BLOB
    );

    CREATE TABLE IF NOT EXISTS weekly_lessons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        day TEXT NOT NULL,
        hour TEXT NOT NULL,
        level TEXT NOT NULL,
        coach TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS lesson_changes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lesson_id INTEGER NOT NULL,
        original_date TEXT NOT NULL,
        status TEXT NOT NULL,
        new_date TEXT,
        new_hour TEXT,
        UNIQUE(lesson_id, original_date),
        FOREIGN KEY(lesson_id) REFERENCES weekly_lessons(id)
    );

    CREATE TABLE IF NOT EXISTS assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        child_id INTEGER NOT NULL,
        pony_id INTEGER NOT NULL,
        activity TEXT NOT NULL,
        activity_date TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS competitions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        discipline TEXT,
        event_date TEXT,
        place TEXT,
        level TEXT,
        details TEXT,
        photo BLOB
    );

    CREATE TABLE IF NOT EXISTS registrations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        competition_id INTEGER,
        child_id INTEGER,
        status TEXT DEFAULT 'En attente'
    );

    CREATE TABLE IF NOT EXISTS absences (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        child_id INTEGER,
        absence_date TEXT,
        reason TEXT,
        status TEXT DEFAULT 'En attente'
    );

    CREATE TABLE IF NOT EXISTS articles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        publication_date TEXT,
        photo BLOB
    );

    CREATE TABLE IF NOT EXISTS gallery (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        photo BLOB,
        photo_date TEXT
    );
    """)

    con.commit()
    con.close()


def query(sql, values=()):
    con = connect()
    cur = con.cursor()
    cur.execute(sql, values)
    result = cur.fetchall()
    con.close()
    return result


def execute(sql, values=()):
    con = connect()
    cur = con.cursor()
    cur.execute(sql, values)
    con.commit()
    result = cur.lastrowid
    con.close()
    return result


init_db()


# =========================================================
# SECURITE DES CODES
# =========================================================

def make_hash(password, salt):
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt.encode(),
        200000
    ).hex()


def create_account(username, password, role, family_name=""):
    salt = secrets.token_hex(16)
    hashed = make_hash(password, salt)

    execute("""
        INSERT INTO accounts
        (username, salt, password_hash, role, family_name)
        VALUES (?, ?, ?, ?, ?)
    """, (username, salt, hashed, role, family_name))


def account_exists(username):
    return bool(query(
        "SELECT id FROM accounts WHERE username=?",
        (username,)
    ))


# =========================================================
# OUTILS
# =========================================================

JOURS = [
    "Lundi", "Mardi", "Mercredi", "Jeudi",
    "Vendredi", "Samedi", "Dimanche"
]


def get_children(family_id=None):
    if family_id is None:
        return query("""
            SELECT id, name, family_id, birth, level
            FROM children ORDER BY name
        """)

    return query("""
        SELECT id, name, family_id, birth, level
        FROM children WHERE family_id=? ORDER BY name
    """, (family_id,))


def get_ponies():
    return query("SELECT id, name FROM ponies ORDER BY name")


def get_families():
    return query("""
        SELECT id, username, family_name
        FROM accounts WHERE role='famille'
        ORDER BY family_name
    """)


def get_coaches():
    return query("""
        SELECT id, username
        FROM accounts WHERE role='coach'
        ORDER BY username
    """)


def show_photo(photo):
    if photo:
        st.image(photo, use_container_width=True)


def family_children_ids():
    return [
        c[0] for c in get_children(st.session_state.user["id"])
    ]


# =========================================================
# CREATION DU PREMIER ADMINISTRATEUR
# =========================================================

if not query("SELECT id FROM accounts LIMIT 1"):

    st.title("🐴 AC ÉQUITATION")
    st.subheader("Créer le compte administrateur")

    st.info(
        "C'est le premier compte du logiciel. "
        "Choisis un identifiant et un code secret."
    )

    with st.form("first_admin"):
        username = st.text_input("Identifiant")
        password = st.text_input("Code secret", type="password")
        confirm = st.text_input("Confirmer le code", type="password")

        submit = st.form_submit_button("Créer mon compte")

        if submit:
            if not username.strip() or not password:
                st.error("Remplis tous les champs.")
            elif password != confirm:
                st.error("Les codes ne correspondent pas.")
            elif len(password) < 8:
                st.error("Le code doit contenir au moins 8 caractères.")
            else:
                create_account(
                    username.strip(),
                    password,
                    "admin"
                )
                st.success("Compte administrateur créé !")
                st.rerun()

    st.stop()


# =========================================================
# CONNEXION
# =========================================================

if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:

    st.markdown(
        "<h1 style='text-align:center'>🐴 AC ÉQUITATION</h1>",
        unsafe_allow_html=True
    )

    st.markdown(
        "<p style='text-align:center;color:#71866B'>"
        "Le club, les cavaliers et les poneys"
        "</p>",
        unsafe_allow_html=True
    )

    gauche, centre, droite = st.columns([1, 2, 1])

    with centre:
        st.subheader("Connexion")

        with st.form("login"):
            username = st.text_input("Identifiant")
            password = st.text_input("Code secret", type="password")

            submit = st.form_submit_button(
                "Se connecter",
                use_container_width=True
            )

            if submit:
                account = query("""
                    SELECT id, username, salt,
                    password_hash, role, family_name
                    FROM accounts WHERE username=?
                """, (username.strip(),))

                if account:
                    a = account[0]

                    if make_hash(password, a[2]) == a[3]:
                        st.session_state.user = {
                            "id": a[0],
                            "username": a[1],
                            "role": a[4],
                            "family_name": a[5]
                        }
                        st.rerun()
                    else:
                        st.error("Code incorrect.")
                else:
                    st.error("Identifiant introuvable.")

    st.stop()


user = st.session_state.user
role = user["role"]


# =========================================================
# MENU
# =========================================================

st.sidebar.title("🐴 AC ÉQUITATION")
st.sidebar.caption("La vie du club")
st.sidebar.divider()

st.sidebar.write(
    "Connecté : **" +
    (user["family_name"] or user["username"]) +
    "**"
)

if role == "admin":
    pages = [
        "Accueil",
        "Familles et cavaliers",
        "Moniteurs",
        "Poneys",
        "Planning",
        "Attribution des poneys",
        "Concours",
        "Absences",
        "Actualités",
        "Galerie photos"
    ]

elif role == "coach":
    pages = [
        "Accueil",
        "Familles et cavaliers",
        "Poneys",
        "Planning",
        "Attribution des poneys",
        "Concours",
        "Absences",
        "Actualités",
        "Galerie photos"
    ]

else:
    pages = [
        "Accueil",
        "Mes enfants",
        "Planning",
        "Mes concours",
        "Mes absences",
        "Actualités",
        "Galerie photos"
    ]

page = st.sidebar.radio("Navigation", pages)

if st.sidebar.button("Déconnexion"):
    st.session_state.user = None
    st.rerun()


# =========================================================
# ACCUEIL
# =========================================================

if page == "Accueil":

    st.title("Bienvenue chez AC Équitation 🐴")
    st.write("Toutes les informations du club au même endroit.")

    if role in ["admin", "coach"]:

        c1, c2, c3 = st.columns(3)

        c1.metric("Cavaliers", len(get_children()))
        c2.metric("Poneys", len(get_ponies()))
        c3.metric("Concours", len(query(
            "SELECT id FROM competitions"
        )))

    st.divider()
    st.subheader("📰 Les dernières actualités")

    articles = query("""
        SELECT title, content, publication_date, photo
        FROM articles ORDER BY id DESC LIMIT 3
    """)

    if not articles:
        st.info("Aucune actualité publiée.")

    for article in articles:
        with st.container(border=True):
            st.subheader(article[0])
            st.caption(article[2])
            st.write(article[1])
            show_photo(article[3])


# =========================================================
# FAMILLES ET CAVALIERS
# =========================================================

elif page in ["Familles et cavaliers", "Mes enfants"]:

    st.title("👨‍👩‍👧 Familles et cavaliers")

    if role == "famille":

        children = get_children(user["id"])

        if not children:
            st.info("Aucun enfant n'est encore rattaché à ce compte.")

        for child in children:
            with st.container(border=True):
                st.subheader(child[1])
                st.write("Date de naissance :", child[3])
                st.write("Niveau :", child[4])

                assignments = query("""
                    SELECT ponies.name, assignments.activity,
                    assignments.activity_date
                    FROM assignments
                    JOIN ponies ON ponies.id=assignments.pony_id
                    WHERE assignments.child_id=?
                    ORDER BY assignments.activity_date DESC
                """, (child[0],))

                st.write("**Poneys attribués :**")

                if assignments:
                    for a in assignments:
                        st.write(
                            f"{a[0]} — {a[1]} — {a[2]}"
                        )
                else:
                    st.caption("Aucune attribution pour le moment.")

    else:

        if role == "admin":

            st.subheader("Créer un compte famille")

            with st.form("new_family"):
                family_name = st.text_input("Nom de la famille")
                username = st.text_input(
                    "Identifiant de connexion de la famille"
                )
                password = st.text_input(
                    "Code de connexion",
                    type="password"
                )
                confirm = st.text_input(
                    "Confirmer le code",
                    type="password"
                )

                submit = st.form_submit_button("Créer la famille")

                if submit:
                    if not family_name.strip() or not username.strip():
                        st.error("Remplis les informations.")
                    elif password != confirm:
                        st.error("Les codes ne correspondent pas.")
                    elif len(password) < 8:
                        st.error("Minimum 8 caractères.")
                    elif account_exists(username.strip()):
                        st.error("Cet identifiant existe déjà.")
                    else:
                        create_account(
                            username.strip(),
                            password,
                            "famille",
                            family_name.strip()
                        )
                        st.success("Famille créée !")
                        st.rerun()

            st.divider()

            families = get_families()

            st.subheader("Ajouter un enfant")

            if families:

                family_options = {
                    f"{f[2]} — {f[1]}": f[0]
                    for f in families
                }

                with st.form("new_child"):
                    selected_family = st.selectbox(
                        "Famille",
                        list(family_options.keys())
                    )
                    name = st.text_input("Nom et prénom de l'enfant")
                    birth = st.date_input(
                        "Date de naissance",
                        value=date(2015, 1, 1)
                    )
                    level = st.selectbox(
                        "Niveau",
                        [
                            "Baby poney", "Débutant",
                            "Galop 1", "Galop 2",
                            "Galop 3", "Galop 4",
                            "Galop 5", "Galop 6", "Galop 7"
                        ]
                    )

                    submit = st.form_submit_button("Ajouter l'enfant")

                    if submit:
                        if name.strip():
                            execute("""
                                INSERT INTO children
                                (family_id, name, birth, level)
                                VALUES (?, ?, ?, ?)
                            """, (
                                family_options[selected_family],
                                name.strip(),
                                str(birth),
                                level
                            ))
                            st.success("Enfant ajouté !")
                            st.rerun()
                        else:
                            st.error("Indique le nom de l'enfant.")

            else:
                st.info("Crée d'abord un compte famille.")

        st.divider()
        st.subheader("Liste des cavaliers")

        for child in get_children():
            with st.expander(child[1] + " — " + child[4]):
                st.write("Date de naissance :", child[3])

                family = query(
                    "SELECT family_name FROM accounts WHERE id=?",
                    (child[2],)
                )

                if family:
                    st.write("Famille :", family[0][0])


# =========================================================
# MONITEURS
# =========================================================

elif page == "Moniteurs":

    st.title("👩‍🏫 Gestion des moniteurs")

    coaches = get_coaches()

    st.metric("Moniteurs enregistrés", f"{len(coaches)} / 2")

    if len(coaches) < 2:

        with st.form("new_coach"):
            username = st.text_input("Identifiant du moniteur")
            password = st.text_input(
                "Code personnel",
                type="password"
            )
            confirm = st.text_input(
                "Confirmer le code",
                type="password"
            )

            submit = st.form_submit_button("Créer le compte moniteur")

            if submit:
                if not username.strip() or not password:
                    st.error("Remplis tous les champs.")
                elif password != confirm:
                    st.error("Les codes ne correspondent pas.")
                elif len(password) < 8:
                    st.error("Minimum 8 caractères.")
                elif account_exists(username.strip()):
                    st.error("Identifiant déjà utilisé.")
                else:
                    if len(get_coaches()) >= 2:
                        st.error("Maximum deux moniteurs.")
                    else:
                        create_account(
                            username.strip(),
                            password,
                            "coach"
                        )
                        st.success("Moniteur créé !")
                        st.rerun()

    else:
        st.info("Les deux comptes moniteurs sont déjà créés.")

    st.divider()
    st.subheader("Comptes moniteurs")

    for coach in get_coaches():
        st.write("👤 " + coach[1])


# =========================================================
# PONEYS
# =========================================================

elif page == "Poneys":

    st.title("🐴 Les poneys du club")

    ponies = query("""
        SELECT id, name, age, description, photo
        FROM ponies ORDER BY name
    """)

    if not ponies:
        st.info("Aucun poney enregistré.")

    for pony in ponies:
        with st.container(border=True):
            st.subheader(pony[1])
            st.write("Âge :", pony[2])
            st.write(pony[3])
            show_photo(pony[4])

    if role in ["admin", "coach"]:

        st.divider()
        st.subheader("Ajouter un poney")

        with st.form("new_pony"):
            name = st.text_input("Nom du poney")
            age = st.text_input("Âge")
            description = st.text_area(
                "Caractère et particularités"
            )
            photo = st.file_uploader(
                "Photo du poney",
                type=["jpg", "jpeg", "png"]
            )

            submit = st.form_submit_button("Ajouter le poney")

            if submit:
                if name.strip():
                    photo_data = photo.getvalue() if photo else None

                    execute("""
                        INSERT INTO ponies
                        (name, age, description, photo)
                        VALUES (?, ?, ?, ?)
                    """, (
                        name.strip(),
                        age,
                        description,
                        photo_data
                    ))

                    st.success("Poney ajouté !")
                    st.rerun()
                else:
                    st.error("Indique le nom du poney.")


# =========================================================
# PLANNING HEBDOMADAIRE
# =========================================================

elif page == "Planning":

    st.title("📅 Planning hebdomadaire")
    st.caption(
        "Les cours sont enregistrés une seule fois "
        "et reviennent chaque semaine."
    )

    weekly_lessons = query("""
        SELECT id, day, hour, level, coach
        FROM weekly_lessons
        ORDER BY
        CASE day
            WHEN 'Lundi' THEN 1
            WHEN 'Mardi' THEN 2
            WHEN 'Mercredi' THEN 3
            WHEN 'Jeudi' THEN 4
            WHEN 'Vendredi' THEN 5
            WHEN 'Samedi' THEN 6
            WHEN 'Dimanche' THEN 7
        END,
        hour
    """)

    st.subheader("Cours habituels")

    if weekly_lessons:
        for lesson in weekly_lessons:
            with st.container(border=True):
                st.write(
                    f"**{lesson[1]} à {lesson[2]}**"
                )
                st.write(
                    f"{lesson[3]} — Moniteur : {lesson[4]}"
                )
    else:
        st.info("Aucun cours hebdomadaire enregistré.")

    # -----------------------------------------------------
    # CREATION DES COURS
    # -----------------------------------------------------

    if role in ["admin", "coach"]:

        st.divider()
        st.subheader("➕ Créer un cours hebdomadaire")

        with st.form("new_weekly_lesson"):

            day = st.selectbox("Jour", JOURS)
            hour = st.time_input("Heure", time(14, 0))

            level = st.selectbox(
                "Niveau",
                [
                    "Baby poney", "Débutant",
                    "Galop 1", "Galop 2",
                    "Galop 3", "Galop 4",
                    "Galop 5", "Galop 6", "Galop 7"
                ]
            )

            coach_options = [
                c[1] for c in get_coaches()
            ]

            if role == "coach":
                coach_options = [user["username"]]

            if coach_options:
                coach = st.selectbox(
                    "Moniteur responsable",
                    coach_options
                )
            else:
                coach = st.text_input("Moniteur responsable")

            submit = st.form_submit_button("Créer le cours")

            if submit:
                if coach.strip():
                    execute("""
                        INSERT INTO weekly_lessons
                        (day, hour, level, coach)
                        VALUES (?, ?, ?, ?)
                    """, (
                        day,
                        hour.strftime("%H:%M"),
                        level,
                        coach
                    ))

                    st.success(
                        "Cours créé ! Il reviendra chaque semaine."
                    )
                    st.rerun()
                else:
                    st.error("Indique un moniteur.")

        # -------------------------------------------------
        # AFFICHAGE DES 8 PROCHAINES SEMAINES
        # -------------------------------------------------

        st.divider()
        st.subheader("📆 Les 8 prochaines semaines")

        today = date.today()
        upcoming = []

        for lesson in weekly_lessons:

            lesson_id, day, hour, level, coach = lesson
            weekday_number = JOURS.index(day)

            days_until = (
                weekday_number - today.weekday()
            ) % 7

            first_date = today + timedelta(days=days_until)

            for week in range(8):

                original_date = (
                    first_date + timedelta(days=7 * week)
                )

                if original_date < today:
                    continue

                changes = query("""
                    SELECT status, new_date, new_hour
                    FROM lesson_changes
                    WHERE lesson_id=? AND original_date=?
                """, (
                    lesson_id,
                    str(original_date)
                ))

                if changes:
                    status, new_date, new_hour = changes[0]

                    if status == "Annulé":
                        continue

                    if status == "Déplacé":
                        display_date = new_date
                        display_hour = new_hour
                    else:
                        display_date = str(original_date)
                        display_hour = hour

                else:
                    status = "Normal"
                    display_date = str(original_date)
                    display_hour = hour

                upcoming.append({
                    "date": display_date,
                    "heure": display_hour,
                    "niveau": level,
                    "moniteur": coach,
                    "cours_id": lesson_id,
                    "date_origine": str(original_date),
                    "statut": status
                })

        upcoming.sort(
            key=lambda x: (x["date"], x["heure"])
        )

        if upcoming:
            st.dataframe(
                [
                    {
                        "Date": c["date"],
                        "Heure": c["heure"],
                        "Cours": c["niveau"],
                        "Moniteur": c["moniteur"],
                        "Statut": c["statut"]
                    }
                    for c in upcoming
                ],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Aucune séance prévue.")

        # -------------------------------------------------
        # ANNULER OU DEPLACER UNE SEANCE
        # -------------------------------------------------

        st.divider()
        st.subheader("🔄 Annuler ou déplacer une séance")

        if weekly_lessons:

            lesson_options = {
                f"{l[1]} à {l[2]} — {l[3]} ({l[4]})": l[0]
                for l in weekly_lessons
            }

            with st.form("change_lesson"):

                selected_label = st.selectbox(
                    "Cours concerné",
                    list(lesson_options.keys())
                )

                selected_id = lesson_options[selected_label]

                possible_dates = [
                    c["date_origine"]
                    for c in upcoming
                    if c["cours_id"] == selected_id
                ]

                if possible_dates:
                    selected_date = st.selectbox(
                        "Séance concernée",
                        possible_dates
                    )
                else:
                    selected_date = st.date_input(
                        "Date de la séance",
                        value=today
                    )
                    selected_date = str(selected_date)

                action = st.radio(
                    "Action",
                    [
                        "Annuler uniquement cette séance",
                        "Déplacer cette séance"
                    ]
                )

                if action == "Déplacer cette séance":
                    new_date = st.date_input(
                        "Nouvelle date",
                        value=today + timedelta(days=1)
                    )

                    new_hour = st.time_input(
                        "Nouvelle heure",
                        time(14, 0)
                    )
                else:
                    new_date = today
                    new_hour = time(14, 0)

                submit = st.form_submit_button("Valider")

                if submit:

                    execute("""
                        DELETE FROM lesson_changes
                        WHERE lesson_id=? AND original_date=?
                    """, (
                        selected_id,
                        selected_date
                    ))

                    if action == "Annuler uniquement cette séance":

                        execute("""
                            INSERT INTO lesson_changes
                            (lesson_id, original_date, status)
                            VALUES (?, ?, ?)
                        """, (
                            selected_id,
                            selected_date,
                            "Annulé"
                        ))

                        st.success("Cette séance a été annulée.")

                    else:

                        execute("""
                            INSERT INTO lesson_changes
                            (lesson_id, original_date, status,
                             new_date, new_hour)
                            VALUES (?, ?, ?, ?, ?)
                        """, (
                            selected_id,
                            selected_date,
                            "Déplacé",
                            str(new_date),
                            new_hour.strftime("%H:%M")
                        ))

                        st.success("Cette séance a été déplacée.")

                    st.rerun()

        # -------------------------------------------------
        # SUPPRESSION D'UN COURS HABITUEL
        # -------------------------------------------------

        st.divider()
        st.subheader("Supprimer un cours hebdomadaire")

        for lesson in weekly_lessons:

            if st.button(
                f"Supprimer : {lesson[1]} {lesson[2]} - {lesson[3]}",
                key=f"delete_lesson_{lesson[0]}"
            ):
                execute(
                    "DELETE FROM lesson_changes WHERE lesson_id=?",
                    (lesson[0],)
                )

                execute(
                    "DELETE FROM weekly_lessons WHERE id=?",
                    (lesson[0],)
                )

                st.success("Cours hebdomadaire supprimé.")
                st.rerun()

    else:

        # Les familles voient les cours des 8 prochaines semaines
        st.subheader("Mes prochains cours")

        today = date.today()
        family_ids = family_children_ids()

        for lesson in weekly_lessons:

            lesson_id, day, hour, level, coach = lesson
            first_date = today + timedelta(
                days=(JOURS.index(day) - today.weekday()) % 7
            )

            for week in range(8):

                original_date = first_date + timedelta(days=week * 7)

                if original_date < today:
                    continue

                changes = query("""
                    SELECT status, new_date, new_hour
                    FROM lesson_changes
                    WHERE lesson_id=? AND original_date=?
                """, (lesson_id, str(original_date)))

                if changes and changes[0][0] == "Annulé":
                    continue

                if changes and changes[0][0] == "Déplacé":
                    display_date = changes[0][1]
                    display_hour = changes[0][2]
                else:
                    display_date = str(original_date)
                    display_hour = hour

                st.write(
                    f"**{display_date} à {display_hour}** — "
                    f"{level} — {coach}"
                )


# =========================================================
# ATTRIBUTION DES PONEYS
# =========================================================

elif page == "Attribution des poneys":

    st.title("🐴 Attribution des poneys")

    children = get_children()
    ponies = get_ponies()

    if children and ponies:

        child_options = {
            c[1]: c[0] for c in children
        }

        pony_options = {
            p[1]: p[0] for p in ponies
        }

        with st.form("pony_assignment"):

            child_name = st.selectbox(
                "Cavalier",
                list(child_options.keys())
            )

            pony_name = st.selectbox(
                "Poney",
                list(pony_options.keys())
            )

            activity = st.selectbox(
                "Activité",
                ["Cours", "Stage", "Concours"]
            )

            activity_date = st.date_input("Date de l'activité")

            submit = st.form_submit_button("Attribuer le poney")

            if submit:
                execute("""
                    INSERT INTO assignments
                    (child_id, pony_id, activity, activity_date)
                    VALUES (?, ?, ?, ?)
                """, (
                    child_options[child_name],
                    pony_options[pony_name],
                    activity,
                    str(activity_date)
                ))

                st.success("Poney attribué !")
                st.rerun()

    else:
        st.info("Ajoute des enfants et des poneys avant de commencer.")

    st.divider()
    st.subheader("Historique des attributions")

    assignments = query("""
        SELECT children.name, ponies.name,
        assignments.activity, assignments.activity_date
        FROM assignments
        JOIN children ON children.id=assignments.child_id
        JOIN ponies ON ponies.id=assignments.pony_id
        ORDER BY assignments.activity_date DESC
    """)

    for a in assignments:
        st.write(
            f"**{a[0]}** — {a[1]} — {a[2]} — {a[3]}"
        )


# =========================================================
# CONCOURS
# =========================================================

elif page in ["Concours", "Mes concours"]:

    st.title("🏆 Concours et compétitions")

    competitions = query("""
        SELECT id, name, discipline, event_date,
        place, level, details, photo
        FROM competitions ORDER BY event_date
    """)

    for comp in competitions:

        with st.container(border=True):

            st.subheader(comp[1])
            st.write("Discipline :", comp[2])
            st.write("Date :", comp[3])
            st.write("Lieu :", comp[4])
            st.write("Niveau :", comp[5])
            st.write(comp[6])
            show_photo(comp[7])

            if role == "famille":

                children = get_children(user["id"])

                if children:

                    options = {
                        c[1]: c[0] for c in children
                    }

                    with st.form(f"register_{comp[0]}"):

                        selected_child = st.selectbox(
                            "Inscrire un enfant",
                            list(options.keys())
                        )

                        submit = st.form_submit_button(
                            "Demander l'inscription"
                        )

                        if submit:
                            already = query("""
                                SELECT id FROM registrations
                                WHERE competition_id=? AND child_id=?
                            """, (
                                comp[0],
                                options[selected_child]
                            ))

                            if already:
                                st.warning("Cet enfant est déjà inscrit.")
                            else:
                                execute("""
                                    INSERT INTO registrations
                                    (competition_id, child_id, status)
                                    VALUES (?, ?, ?)
                                """, (
                                    comp[0],
                                    options[selected_child],
                                    "En attente"
                                ))

                                st.success("Demande envoyée !")
                                st.rerun()

    if role in ["admin", "coach"]:

        st.divider()
        st.subheader("Créer un concours")

        with st.form("new_competition"):

            name = st.text_input("Nom du concours")

            discipline = st.selectbox(
                "Discipline",
                [
                    "CSO",
                    "Dressage",
                    "Hunter",
                    "Pony Games",
                    "Équifun",
                    "Concours interne",
                    "Concours extérieur"
                ]
            )

            event_date = st.date_input("Date")
            place = st.text_input("Lieu")
            level = st.text_input("Catégories et niveaux")
            details = st.text_area("Informations complémentaires")

            photo = st.file_uploader(
                "Photo du concours",
                type=["jpg", "jpeg", "png"]
            )

            submit = st.form_submit_button("Créer le concours")

            if submit:
                if name.strip():
                    execute("""
                        INSERT INTO competitions
                        (name, discipline, event_date, place,
                         level, details, photo)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        name,
                        discipline,
                        str(event_date),
                        place,
                        level,
                        details,
                        photo.getvalue() if photo else None
                    ))

                    st.success("Concours créé !")
                    st.rerun()
                else:
                    st.error("Indique le nom du concours.")

        st.divider()
        st.subheader("Inscriptions reçues")

        registrations = query("""
            SELECT registrations.id, children.name,
            competitions.name, registrations.status
            FROM registrations
            JOIN children ON children.id=registrations.child_id
            JOIN competitions
            ON competitions.id=registrations.competition_id
            ORDER BY registrations.id DESC
        """)

        for r in registrations:

            st.write(
                f"**{r[1]}** — {r[2]} — {r[3]}"
            )

            if r[3] == "En attente":

                col1, col2 = st.columns(2)

                if col1.button(
                    "Accepter",
                    key=f"accept_{r[0]}"
                ):
                    execute(
                        "UPDATE registrations SET status=? WHERE id=?",
                        ("Acceptée", r[0])
                    )
                    st.rerun()

                if col2.button(
                    "Refuser",
                    key=f"refuse_{r[0]}"
                ):
                    execute(
                        "UPDATE registrations SET status=? WHERE id=?",
                        ("Refusée", r[0])
                    )
                    st.rerun()


# =========================================================
# ABSENCES
# =========================================================

elif page in ["Absences", "Mes absences"]:

    st.title("📋 Gestion des absences")

    if role == "famille":

        children = get_children(user["id"])

        if children:

            options = {
                c[1]: c[0] for c in children
            }

            with st.form("absence_form"):

                child_name = st.selectbox(
                    "Enfant",
                    list(options.keys())
                )

                absence_date = st.date_input("Date de l'absence")
                reason = st.text_area("Motif")

                submit = st.form_submit_button("Déclarer l'absence")

                if submit:
                    execute("""
                        INSERT INTO absences
                        (child_id, absence_date, reason, status)
                        VALUES (?, ?, ?, ?)
                    """, (
                        options[child_name],
                        str(absence_date),
                        reason,
                        "En attente"
                    ))

                    st.success("Demande envoyée !")
                    st.rerun()

        rows = query("""
            SELECT children.name, absences.absence_date,
            absences.reason, absences.status
            FROM absences
            JOIN children ON children.id=absences.child_id
            WHERE children.family_id=?
            ORDER BY absences.absence_date DESC
        """, (user["id"],))

        st.subheader("Mes demandes")

        for r in rows:
            st.write(
                f"{r[0]} — {r[1]} — {r[2]} — **{r[3]}**"
            )

    else:

        rows = query("""
            SELECT absences.id, children.name,
            absences.absence_date, absences.reason,
            absences.status
            FROM absences
            JOIN children ON children.id=absences.child_id
            ORDER BY absences.absence_date DESC
        """)

        for r in rows:

            st.write(
                f"**{r[1]}** — {r[2]} — {r[3]} — {r[4]}"
            )

            if r[4] == "En attente":

                col1, col2 = st.columns(2)

                if col1.button(
                    "Accepter",
                    key=f"absence_accept_{r[0]}"
                ):
                    execute(
                        "UPDATE absences SET status=? WHERE id=?",
                        ("Acceptée", r[0])
                    )
                    st.rerun()

                if col2.button(
                    "Refuser",
                    key=f"absence_refuse_{r[0]}"
                ):
                    execute(
                        "UPDATE absences SET status=? WHERE id=?",
                        ("Refusée", r[0])
                    )
                    st.rerun()


# =========================================================
# ACTUALITES
# =========================================================

elif page == "Actualités":

    st.title("📰 Actualités du club")

    articles = query("""
        SELECT id, title, content, publication_date, photo
        FROM articles ORDER BY id DESC
    """)

    if not articles:
        st.info("Aucun article publié pour le moment.")

    for article in articles:

        with st.container(border=True):
            st.subheader(article[1])
            st.caption(article[3])
            st.write(article[2])
            show_photo(article[4])

    if role in ["admin", "coach"]:

        st.divider()
        st.subheader("✍️ Rédiger un article")

        with st.form("new_article"):

            title = st.text_input("Titre")
            content = st.text_area(
                "Texte de l'article",
                height=180
            )

            publication_date = st.date_input(
                "Date de publication"
            )

            photo = st.file_uploader(
                "Photo de l'article",
                type=["jpg", "jpeg", "png"]
            )

            submit = st.form_submit_button("Publier")

            if submit:
                if title.strip() and content.strip():

                    execute("""
                        INSERT INTO articles
                        (title, content, publication_date, photo)
                        VALUES (?, ?, ?, ?)
                    """, (
                        title,
                        content,
                        str(publication_date),
                        photo.getvalue() if photo else None
                    ))

                    st.success("Article publié !")
                    st.rerun()

                else:
                    st.error("Ajoute un titre et un texte.")


# =========================================================
# GALERIE PHOTOS
# =========================================================

elif page == "Galerie photos":

    st.title("📸 Galerie du club")

    photos = query("""
        SELECT title, photo, photo_date
        FROM gallery ORDER BY id DESC
    """)

    if not photos:
        st.info("La galerie est encore vide.")

    for photo in photos:

        with st.container(border=True):
            st.subheader(photo[0])
            show_photo(photo[1])
            st.caption(photo[2])

    if role in ["admin", "coach"]:

        st.divider()
        st.subheader("Ajouter une photo")

        with st.form("new_gallery_photo"):

            title = st.text_input("Titre ou légende")

            photo = st.file_uploader(
                "Choisir une photo",
                type=["jpg", "jpeg", "png"]
            )

            photo_date = st.date_input("Date")

            submit = st.form_submit_button("Ajouter à la galerie")

            if submit:
                if title.strip() and photo:

                    execute("""
                        INSERT INTO gallery
                        (title, photo, photo_date)
                        VALUES (?, ?, ?)
                    """, (
                        title,
                        photo.getvalue(),
                        str(photo_date)
                    ))

                    st.success("Photo ajoutée !")
                    st.rerun()

                else:
                    st.error("Ajoute un titre et une photo.")


# =========================================================
# PIED DE PAGE
# =========================================================

st.divider()

st.markdown(
    "<p style='text-align:center;color:#71866B'>"
    "AC ÉQUITATION • La passion du cheval et du poney"
    "</p>",
    unsafe_allow_html=True
)
