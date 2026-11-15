
import streamlit as st
import sqlite3
import hashlib
import secrets
from datetime import date, time

# ==================================================
# AC EQUITATION - APPLICATION DU CLUB
# ==================================================

st.set_page_config(
    page_title="AC Équitation",
    page_icon="🐴",
    layout="wide"
)

DB = "ac_equitation.db"

# ==================================================
# DESIGN
# ==================================================

st.markdown("""
<style>
.stApp {
    background: #F7F5EF;
}
h1, h2, h3 {
    color: #526B53;
}
section[data-testid="stSidebar"] {
    background: #E6EBDD;
}
div.stButton > button {
    background: #71866B;
    color: white;
    border-radius: 10px;
    border: 0;
    min-height: 40px;
}
div.stButton > button:hover {
    background: #526B53;
    color: white;
}
div[data-testid="stForm"] {
    background: white;
    padding: 18px;
    border-radius: 12px;
}
</style>
""", unsafe_allow_html=True)

# ==================================================
# BASE DE DONNEES
# ==================================================

def connect():
    return sqlite3.connect(DB)

def init_db():
    con = connect()
    cur = con.cursor()

    cur.executescript("""
    CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        salt TEXT,
        password_hash TEXT,
        role TEXT,
        family_name TEXT
    );

    CREATE TABLE IF NOT EXISTS children (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        family_id INTEGER,
        name TEXT,
        birth TEXT,
        level TEXT
    );

    CREATE TABLE IF NOT EXISTS ponies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        age TEXT,
        description TEXT,
        photo BLOB
    );

    CREATE TABLE IF NOT EXISTS lessons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        day TEXT,
        lesson_date TEXT,
        hour TEXT,
        level TEXT,
        coach TEXT
    );

    CREATE TABLE IF NOT EXISTS competitions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        discipline TEXT,
        event_date TEXT,
        place TEXT,
        level TEXT,
        details TEXT
    );

    CREATE TABLE IF NOT EXISTS registrations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        competition_id INTEGER,
        child_id INTEGER,
        status TEXT
    );

    CREATE TABLE IF NOT EXISTS assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        child_id INTEGER,
        pony_id INTEGER,
        activity TEXT,
        activity_date TEXT
    );

    CREATE TABLE IF NOT EXISTS absences (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        child_id INTEGER,
        absence_date TEXT,
        reason TEXT,
        status TEXT
    );

    CREATE TABLE IF NOT EXISTS articles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        content TEXT,
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
    new_id = cur.lastrowid
    con.close()
    return new_id

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
    execute(
        """INSERT INTO accounts
        (username, salt, password_hash, role, family_name)
        VALUES (?, ?, ?, ?, ?)""",
        (username, salt, hashed, role, family_name)
    )

init_db()

# ==================================================
# OUTILS
# ==================================================

def get_children(family_id=None):
    if family_id is None:
        return query(
            "SELECT id, name, family_id, level FROM children"
        )
    return query(
        "SELECT id, name, family_id, level FROM children WHERE family_id=?",
        (family_id,)
    )

def get_ponies():
    return query("SELECT id, name FROM ponies ORDER BY name")

def get_families():
    return query(
        "SELECT id, username, family_name FROM accounts "
        "WHERE role='famille' ORDER BY family_name"
    )

def get_competitions():
    return query(
        "SELECT id, name, discipline, event_date, place, level "
        "FROM competitions ORDER BY event_date"
    )

def show_photo(photo):
    if photo:
        st.image(photo, use_container_width=True)

# ==================================================
# PREMIERE CONNEXION : CREATION ADMIN
# ==================================================

if not query("SELECT id FROM accounts LIMIT 1"):

    st.title("🐴 AC ÉQUITATION")
    st.subheader("Création du compte administrateur")

    st.info(
        "Commence par créer ton compte administrateur. "
        "Garde ton code secret."
    )

    with st.form("first_admin"):
        username = st.text_input("Identifiant administrateur")
        password = st.text_input("Ton code secret", type="password")
        confirm = st.text_input("Confirmer le code", type="password")
        submit = st.form_submit_button("Créer mon compte")

        if submit:
            if not username.strip() or not password:
                st.error("Remplis tous les champs.")
            elif password != confirm:
                st.error("Les deux codes ne correspondent pas.")
            elif len(password) < 8:
                st.error("Choisis un code d'au moins 8 caractères.")
            else:
                create_account(
                    username.strip(),
                    password,
                    "admin"
                )
                st.success("Compte administrateur créé !")
                st.rerun()

    st.stop()

# ==================================================
# CONNEXION
# ==================================================

if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:

    st.markdown(
        "<h1 style='text-align:center'>🐴 AC ÉQUITATION</h1>",
        unsafe_allow_html=True
    )
    st.markdown(
        "<p style='text-align:center'>"
        "Le club, les cavaliers et les poneys"
        "</p>",
        unsafe_allow_html=True
    )

    gauche, centre, droite = st.columns([1, 2, 1])

    with centre:
        st.subheader("Connexion à votre espace")

        with st.form("login"):
            username = st.text_input("Identifiant ou code famille")
            password = st.text_input("Code secret", type="password")
            submit = st.form_submit_button(
                "Se connecter",
                use_container_width=True
            )

            if submit:
                account = query(
                    """SELECT id, username, salt,
                    password_hash, role, family_name
                    FROM accounts WHERE username=?""",
                    (username.strip(),)
                )

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
                    st.error("Compte introuvable.")

    st.stop()

user = st.session_state.user
role = user["role"]

# ==================================================
# MENU
# ==================================================

st.sidebar.markdown("# 🐴 AC ÉQUITATION")
st.sidebar.caption("L'application de votre club")
st.sidebar.divider()

st.sidebar.write(
    "Connecté : **" +
    (user["family_name"] or user["username"]) + "**"
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

# ==================================================
# ACCUEIL
# ==================================================

if page == "Accueil":

    st.title("Bienvenue chez AC Équitation 🐴")
    st.write("La vie du club en un seul endroit.")

    if role in ["admin", "coach"]:
        c1, c2, c3 = st.columns(3)
        c1.metric("Cavaliers", len(get_children()))
        c2.metric("Poneys", len(get_ponies()))
        c3.metric("Concours", len(get_competitions()))

    st.divider()
    st.subheader("Les dernières actualités")

    for article in query(
        """SELECT title, content, publication_date, photo
        FROM articles ORDER BY id DESC LIMIT 3"""
    ):
        with st.container(border=True):
            st.subheader(article[0])
            st.caption(article[2])
            st.write(article[1])
            show_photo(article[3])

# ==================================================
# FAMILLES ET CAVALIERS
# ==================================================

elif page == "Familles et cavaliers":

    st.title("👨‍👩‍👧 Familles et cavaliers")

    if role == "admin":

        st.subheader("Créer une famille")

        with st.form("new_family"):
            family_name = st.text_input("Nom de la famille")
            code = st.text_input(
                "Code de connexion de la famille",
                type="password"
            )
            confirm = st.text_input(
                "Confirmer le code",
                type="password"
            )
            submit = st.form_submit_button("Créer la famille")

            if submit:
                if not family_name.strip() or not code:
                    st.error("Remplis tous les champs.")
                elif code != confirm:
                    st.error("Les codes ne correspondent pas.")
                elif len(code) < 6:
                    st.error("Utilise au moins 6 caractères.")
                else:
                    try:
                        create_account(
                            family_name.strip(),
                            code,
                            "famille",
                            family_name.strip()
                        )
                        st.success("Famille créée !")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Cet identifiant existe déjà.")

        st.divider()

        st.subheader("Ajouter un enfant")

        families = get_families()

        if families:
            family_options = {
                f"{f[2]} ({f[1]})": f[0] for f in families
            }

            with st.form("new_child"):
                selected_family = st.selectbox(
                    "Famille",
                    list(family_options.keys())
                )
                name = st.text_input("Prénom et nom")
                birth = st.date_input(
                    "Date de naissance",
                    value=date(2015, 1, 1)
                )
                level = st.selectbox(
                    "Niveau",
                    [
                        "Baby poney", "Débutant", "Galop 1",
                        "Galop 2", "Galop 3", "Galop 4",
                        "Galop 5", "Galop 6", "Galop 7"
                    ]
                )

                submit = st.form_submit_button("Ajouter l'enfant")

                if submit:
                    if name.strip():
                        execute(
                            """INSERT INTO children
                            (family_id, name, birth, level)
                            VALUES (?, ?, ?, ?)""",
                            (
                                family_options[selected_family],
                                name.strip(),
                                str(birth),
                                level
                            )
                        )
                        st.success("Enfant ajouté !")
                        st.rerun()
                    else:
                        st.error("Indique le nom de l'enfant.")

        st.divider()
        st.subheader("Toutes les familles")

        for f in families:
            with st.expander(f[2] + " — " + f[1]):
                for child in get_children(f[0]):
                    st.write(child[1] + " — " + child[3])

    else:
        st.title("Liste des cavaliers")
        st.dataframe(
            [
                {"Nom": c[1], "Niveau": c[3]}
                for c in get_children()
            ],
            use_container_width=True
        )

# ==================================================
# MONITEURS - MAXIMUM 2
# ==================================================

elif page == "Moniteurs":

    st.title("👩‍🏫 Gestion des moniteurs")

    coaches = query(
        "SELECT id, username FROM accounts WHERE role='coach'"
    )

    st.metric("Moniteurs enregistrés", f"{len(coaches)} / 2")

    st.subheader("Ajouter un moniteur")

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
            submit = st.form_submit_button("Créer le compte")

            if submit:
                if not username.strip() or not password:
                    st.error("Remplis tous les champs.")
                elif password != confirm:
                    st.error("Les codes ne correspondent pas.")
                elif len(password) < 8:
                    st.error("Minimum 8 caractères.")
                else:
                    try:
                        create_account(
                            username.strip(),
                            password,
                            "coach"
                        )
                        st.success("Moniteur ajouté !")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Identifiant déjà utilisé.")

    else:
        st.info("Les deux comptes moniteurs sont déjà utilisés.")

    st.divider()
    st.subheader("Moniteurs du club")

    for coach in coaches:
        st.write("👤 " + coach[1])

# ==================================================
# PONEYS
# ==================================================

elif page == "Poneys":

    st.title("🐴 Les poneys du club")

    ponies = query(
        "SELECT id, name, age, description, photo FROM ponies"
    )

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
                    execute(
                        """INSERT INTO ponies
                        (name, age, description, photo)
                        VALUES (?, ?, ?, ?)""",
                        (name, age, description, photo_data)
                    )
                    st.success("Poney ajouté !")
                    st.rerun()
                else:
                    st.error("Indique le nom du poney.")

# ==================================================
# PLANNING
# ==================================================

elif page == "Planning":

    st.title("📅 Planning des cours")

    lessons = query(
        """SELECT id, day, lesson_date, hour, level, coach
        FROM lessons ORDER BY lesson_date, hour"""
    )

    st.dataframe(
        [
            {
                "Jour": x[1],
                "Date": x[2],
                "Heure": x[3],
                "Niveau": x[4],
                "Moniteur": x[5]
            }
            for x in lessons
        ],
        use_container_width=True
    )

    if role in ["admin", "coach"]:

        st.divider()
        st.subheader("Créer un cours")

        with st.form("new_lesson"):
            day = st.selectbox(
                "Jour",
                [
                    "Lundi", "Mardi", "Mercredi",
                    "Jeudi", "Vendredi", "Samedi", "Dimanche"
                ]
            )
            lesson_date = st.date_input("Date du cours")
            hour = st.time_input("Heure", time(14, 0))
            level = st.selectbox(
                "Niveau",
                [
                    "Baby poney", "Débutant", "Galop 1",
                    "Galop 2", "Galop 3", "Galop 4",
                    "Galop 5", "Galop 6", "Galop 7"
                ]
            )
            coach = st.text_input("Moniteur responsable")

            submit = st.form_submit_button("Créer le cours")

            if submit:
                execute(
                    """INSERT INTO lessons
                    (day, lesson_date, hour, level, coach)
                    VALUES (?, ?, ?, ?, ?)""",
                    (
                        day, str(lesson_date),
                        hour.strftime("%H:%M"), level, coach
                    )
                )
                st.success("Cours créé !")
                st.rerun()

# ==================================================
# ATTRIBUTION DES PONEYS
# ==================================================

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
                ["Cours", "Concours", "Stage"]
            )

            activity_date = st.date_input("Date de l'activité")

            submit = st.form_submit_button("Attribuer le poney")

            if submit:
                execute(
                    """INSERT INTO assignments
                    (child_id, pony_id, activity, activity_date)
                    VALUES (?, ?, ?, ?)""",
                    (
                        child_options[child_name],
                        pony_options[pony_name],
                        activity,
                        str(activity_date)
                    )
                )
                st.success("Attribution enregistrée !")
                st.rerun()

    else:
        st.info("Ajoute d'abord des enfants et des poneys.")

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

    st.dataframe(
        [
            {
                "Cavalier": a[0],
                "Poney": a[1],
                "Activité": a[2],
                "Date": a[3]
            }
            for a in assignments
        ],
        use_container_width=True
    )

# ==================================================
# CONCOURS
# ==================================================

elif page in ["Concours", "Mes concours"]:

    st.title("🏆 Concours et compétitions")

    competitions = get_competitions()

    for comp in competitions:

        with st.container(border=True):
            st.subheader(comp[1])
            st.write("Discipline :", comp[2])
            st.write("Date :", comp[3])
            st.write("Lieu :", comp[4])
            st.write("Niveau :", comp[5])

            if role == "famille":
                my_children = get_children(user["id"])

                if my_children:
                    child_options = {
                        c[1]: c[0] for c in my_children
                    }

                    if st.button(
                        "Inscrire un enfant",
                        key=f"register_{comp[0]}"
                    ):
                        st.session_state[
                            f"registration_{comp[0]}"
                        ] = True

                    if st.session_state.get(
                        f"registration_{comp[0]}", False
                    ):
                        child_name = st.selectbox(
                            "Choisir l'enfant",
                            list(child_options.keys()),
                            key=f"child_{comp[0]}"
                        )

                        if st.button(
                            "Confirmer l'inscription",
                            key=f"confirm_{comp[0]}"
                        ):
                            execute(
                                """INSERT INTO registrations
                                (competition_id, child_id, status)
                                VALUES (?, ?, ?)""",
                                (
                                    comp[0],
                                    child_options[child_name],
                                    "En attente"
                                )
                            )
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

            event_date = st.date_input("Date du concours")
            place = st.text_input("Lieu")
            level = st.text_input("Catégories et niveaux")
            details = st.text_area("Informations complémentaires")

            submit = st.form_submit_button("Créer le concours")

            if submit:
                if name.strip():
                    execute(
                        """INSERT INTO competitions
                        (name, discipline, event_date, place, level, details)
                        VALUES (?, ?, ?, ?, ?, ?)""",
                        (
                            name, discipline, str(event_date),
                            place, level, details
                        )
                    )
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
        """)

        for r in registrations:
            st.write(f"{r[1]} — {r[2]} — {r[3]}")

            if r[3] == "En attente":
                a, b = st.columns(2)

                if a.button("Accepter", key=f"ok_{r[0]}"):
                    execute(
                        "UPDATE registrations SET status=? WHERE id=?",
                        ("Acceptée", r[0])
                    )
                    st.rerun()

                if b.button("Refuser", key=f"no_{r[0]}"):
                    execute(
                        "UPDATE registrations SET status=? WHERE id=?",
                        ("Refusée", r[0])
                    )
                    st.rerun()

# ==================================================
# ABSENCES
# ==================================================

elif page in ["Absences", "Mes absences"]:

    st.title("📋 Gestion des absences")

    if role == "famille":

        children = get_children(user["id"])

        if children:

            child_options = {c[1]: c[0] for c in children}

            with st.form("absence_form"):

                child_name = st.selectbox(
                    "Enfant",
                    list(child_options.keys())
                )
                absence_date = st.date_input("Date de l'absence")
                reason = st.text_area("Motif")

                submit = st.form_submit_button("Déclarer l'absence")

                if submit:
                    execute(
                        """INSERT INTO absences
                        (child_id, absence_date, reason, status)
                        VALUES (?, ?, ?, ?)""",
                        (
                            child_options[child_name],
                            str(absence_date),
                            reason,
                            "En attente"
                        )
                    )
                    st.success("Demande envoyée !")
                    st.rerun()

        st.subheader("Mes demandes")

        rows = query("""
            SELECT children.name, absences.absence_date,
            absences.reason, absences.status
            FROM absences
            JOIN children ON children.id=absences.child_id
            WHERE children.family_id=?
        """, (user["id"],))

        st.dataframe(
            [
                {
                    "Enfant": r[0],
                    "Date": r[1],
                    "Motif": r[2],
                    "Statut": r[3]
                }
                for r in rows
            ],
            use_container_width=True
        )

    else:

        rows = query("""
            SELECT absences.id, children.name,
            absences.absence_date, absences.reason, absences.status
            FROM absences
            JOIN children ON children.id=absences.child_id
            ORDER BY absences.absence_date
        """)

        for r in rows:
            st.write(
                f"**{r[1]}** — {r[2]} — {r[3]} — {r[4]}"
            )

            if r[4] == "En attente":

                a, b = st.columns(2)

                if a.button("Accepter", key=f"absence_ok_{r[0]}"):
                    execute(
                        "UPDATE absences SET status=? WHERE id=?",
                        ("Acceptée", r[0])
                    )
                    st.rerun()

                if b.button("Refuser", key=f"absence_no_{r[0]}"):
                    execute(
                        "UPDATE absences SET status=? WHERE id=?",
                        ("Refusée", r[0])
                    )
                    st.rerun()

# ==================================================
# ACTUALITES
# ==================================================

elif page == "Actualités":

    st.title("📰 Actualités du club")

    articles = query("""
        SELECT id, title, content, publication_date, photo
        FROM articles ORDER BY id DESC
    """)

    for article in articles:

        with st.container(border=True):
            st.subheader(article[1])
            st.caption(article[3])
            st.write(article[2])
            show_photo(article[4])

    if role in ["admin", "coach"]:

        st.divider()
        st.subheader("Rédiger un article")

        with st.form("new_article"):

            title = st.text_input("Titre de l'article")
            content = st.text_area(
                "Ton article",
                height=180
            )
            publication_date = st.date_input(
                "Date de publication"
            )
            photo = st.file_uploader(
                "Photo de l'article",
                type=["jpg", "jpeg", "png"],
                key="article_photo"
            )

            submit = st.form_submit_button("Publier l'article")

            if submit:
                if title.strip() and content.strip():

                    photo_data = photo.getvalue() if photo else None

                    execute(
                        """INSERT INTO articles
                        (title, content, publication_date, photo)
                        VALUES (?, ?, ?, ?)""",
                        (
                            title, content,
                            str(publication_date), photo_data
                        )
                    )

                    st.success("Article publié !")
                    st.rerun()

                else:
                    st.error("Ajoute un titre et un texte.")

# ==================================================
# GALERIE
# ==================================================

elif page == "Galerie photos":

    st.title("📸 Galerie du club")

    photos = query("""
        SELECT title, photo, photo_date
        FROM gallery ORDER BY id DESC
    """)

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

                    execute(
                        """INSERT INTO gallery
                        (title, photo, photo_date)
                        VALUES (?, ?, ?)""",
                        (
                            title,
                            photo.getvalue(),
                            str(photo_date)
                        )
                    )

                    st.success("Photo ajoutée !")
                    st.rerun()

                else:
                    st.error("Ajoute un titre et une photo.")

# ==================================================
# FIN
# ==================================================

st.divider()
st.caption("AC Équitation • La passion du cheval et du poney")
