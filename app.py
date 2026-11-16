
import streamlit as st
import sqlite3
import hashlib
import secrets
from datetime import date, datetime, time, timedelta
from pathlib import Path

# =====================================================
# AC EQUITATION - APPLICATION DU CLUB
# =====================================================

st.set_page_config(
    page_title="AC Équitation",
    page_icon="🐴",
    layout="wide"
)

DB = "ac_equitation.db"

# CHANGE CES DEUX CODES AVANT DE METTRE EN LIGNE
COACH_CODES = {
    "COACH-AC-2026": "Coach 1",
    "COACH2-AC-2026": "Coach 2"
}

# =====================================================
# DESIGN
# =====================================================

st.markdown("""
<style>
.stApp {
    background: #f6f5ef;
}
h1, h2, h3 {
    color: #435b4b;
}
.stButton button {
    background: #607b65;
    color: white;
    border-radius: 10px;
    border: none;
}
.stButton button:hover {
    background: #435b4b;
    color: white;
}
.card {
    background: white;
    padding: 18px;
    border-radius: 14px;
    border: 1px solid #e4e2d8;
    margin-bottom: 12px;
}
.small {
    color: #777;
    font-size: 13px;
}
</style>
""", unsafe_allow_html=True)

# =====================================================
# BASE DE DONNEES
# =====================================================

def connect():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    return db

def execute(sql, values=()):
    with connect() as db:
        db.execute(sql, values)
        db.commit()

def query(sql, values=()):
    with connect() as db:
        return db.execute(sql, values).fetchall()

def init_db():
    with connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS families (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT,
            email TEXT UNIQUE,
            telephone TEXT,
            adresse TEXT,
            password TEXT
        );

        CREATE TABLE IF NOT EXISTS children (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            family_id INTEGER,
            prenom TEXT,
            age INTEGER,
            poids REAL,
            taille REAL,
            galop TEXT,
            photo BLOB
        );

        CREATE TABLE IF NOT EXISTS coaches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT UNIQUE,
            password TEXT
        );

        CREATE TABLE IF NOT EXISTS ponies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT,
            age TEXT,
            description TEXT,
            photo BLOB
        );

        CREATE TABLE IF NOT EXISTS slots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jour TEXT,
            heure TEXT,
            niveau TEXT,
            places INTEGER,
            actif INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            child_id INTEGER,
            slot_id INTEGER,
            pony_id INTEGER
        );

        CREATE TABLE IF NOT EXISTS dp_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            child_id INTEGER,
            slot_ids TEXT,
            statut TEXT DEFAULT 'En attente'
        );

        CREATE TABLE IF NOT EXISTS absences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            child_id INTEGER,
            slot_id INTEGER,
            date_absence TEXT,
            motif TEXT,
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
            tarif REAL
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

# =====================================================
# OUTILS
# =====================================================

def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), 100000
    ).hex()
    return salt + "$" + digest

def check_password(password, stored):
    try:
        salt, digest = stored.split("$")
        test = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt.encode(), 100000
        ).hex()
        return secrets.compare_digest(test, digest)
    except Exception:
        return False

def notify(family_id, message):
    if family_id:
        execute(
            "INSERT INTO notifications (family_id,message,date_creation) VALUES (?,?,?)",
            (family_id, message, datetime.now().strftime("%d/%m/%Y %H:%M"))
        )

def photo_widget(photo):
    if photo:
        st.image(photo, use_container_width=True)

def get_children(family_id):
    return query("SELECT * FROM children WHERE family_id=?", (family_id,))

def get_child_name(child_id):
    result = query("SELECT prenom FROM children WHERE id=?", (child_id,))
    return result[0]["prenom"] if result else "Élève"

def family_of_child(child_id):
    result = query("SELECT family_id FROM children WHERE id=?", (child_id,))
    return result[0]["family_id"] if result else None

def slot_label(slot):
    return f"{slot['jour']} à {slot['heure']} - {slot['niveau']}"

# =====================================================
# SESSION
# =====================================================

if "role" not in st.session_state:
    st.session_state.role = None
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "user_name" not in st.session_state:
    st.session_state.user_name = None

# =====================================================
# ENTETE
# =====================================================

st.title("🐴 AC ÉQUITATION")
st.caption("Le club, les poneys et les cavaliers réunis au même endroit.")
st.divider()

# =====================================================
# PAGE PUBLIQUE
# =====================================================

def public_page():
    st.subheader("Bienvenue au club !")
    tabs = st.tabs([
        "Accueil", "Nos poneys", "Stages",
        "Événements", "Actualités", "Réserver une balade",
        "Connexion", "Créer un compte"
    ])

    with tabs[0]:
        st.markdown("""
        <div class="card">
        <h2>Bienvenue chez AC Équitation</h2>
        Retrouvez les informations du club, les poneys,
        les stages et les activités proposées.
        </div>
        """, unsafe_allow_html=True)

        for article in query(
            "SELECT * FROM articles ORDER BY id DESC LIMIT 3"
        ):
            st.markdown(f"### {article['titre']}")
            photo_widget(article["photo"])
            st.write(article["contenu"])
            st.caption(article["date_article"])

    with tabs[1]:
        st.subheader("Les poneys du club")
        ponies = query("SELECT * FROM ponies ORDER BY nom")
        if not ponies:
            st.info("Les fiches des poneys seront bientôt disponibles.")
        for pony in ponies:
            with st.container(border=True):
                st.subheader(pony["nom"])
                photo_widget(pony["photo"])
                st.write("Âge :", pony["age"])
                st.write(pony["description"])

    with tabs[2]:
        st.subheader("Stages à venir")
        stages = query("SELECT * FROM stages ORDER BY date_stage")
        for stage in stages:
            regs = query(
                "SELECT COUNT(*) AS n FROM stage_regs WHERE stage_id=?",
                (stage["id"],)
            )[0]["n"]
            with st.container(border=True):
                st.subheader(stage["nom"])
                st.write(
                    f"{stage['discipline']} • {stage['date_stage']} • "
                    f"{stage['horaire']}"
                )
                st.write(f"Niveau : {stage['niveau']}")
                st.write(f"Places restantes : {max(0, stage['places']-regs)}")
                st.write(f"Tarif : {stage['tarif']} €")
                with st.form(f"stage_{stage['id']}"):
                    enfant = st.text_input("Prénom de l'enfant")
                    responsable = st.text_input("Nom du responsable")
                    tel = st.text_input("Téléphone")
                    email = st.text_input("Adresse e-mail")
                    ok = st.form_submit_button("Réserver une place")
                    if ok:
                        if not all([enfant, responsable, tel, email]):
                            st.error("Merci de remplir tous les champs.")
                        elif regs >= stage["places"]:
                            st.error("Ce stage est complet.")
                        else:
                            execute("""
                            INSERT INTO stage_regs
                            (stage_id,nom_enfant,nom_responsable,telephone,email)
                            VALUES (?,?,?,?,?)
                            """, (
                                stage["id"], enfant, responsable, tel, email
                            ))
                            st.success("Demande d'inscription enregistrée.")

    with tabs[3]:
        st.subheader("Événements du club")
        for event in query("SELECT * FROM events ORDER BY date_event"):
            with st.container(border=True):
                st.subheader(event["nom"])
                st.write(event["date_event"])
                st.write(event["description"])

    with tabs[4]:
        st.subheader("Les nouvelles du club")
        for article in query("SELECT * FROM articles ORDER BY id DESC"):
            with st.container(border=True):
                st.subheader(article["titre"])
                photo_widget(article["photo"])
                st.write(article["contenu"])
                st.caption(article["date_article"])

    with tabs[5]:
        st.subheader("Réserver une balade à poney")
        st.write("Réservation sans création de compte.")
        with st.form("walk_form"):
            enfant = st.text_input("Prénom de l'enfant")
            responsable = st.text_input("Nom et prénom du responsable")
            telephone = st.text_input("Téléphone")
            email = st.text_input("Adresse e-mail")
            jour = st.date_input("Date souhaitée", min_value=date.today())
            heure = st.selectbox(
                "Horaire", ["10h00", "10h30", "11h00", "14h00", "14h30", "15h00", "15h30", "16h00"]
            )
            tarif = st.number_input("Tarif de la balade (€)", min_value=0.0, value=10.0)
            ok = st.form_submit_button("Envoyer ma réservation")
            if ok:
                if not all([enfant, responsable, telephone, email]):
                    st.error("Merci de remplir tous les champs.")
                else:
                    execute("""
                    INSERT INTO walk_bookings
                    (enfant,responsable,telephone,email,date_balade,heure,tarif)
                    VALUES (?,?,?,?,?,?,?)
                    """, (
                        enfant, responsable, telephone, email,
                        str(jour), heure, tarif
                    ))
                    st.success("Demande envoyée au club !")

    with tabs[6]:
        st.subheader("Connexion")
        role = st.radio(
            "Je suis :", ["Famille", "Coach"], horizontal=True
        )
        with st.form("login_form"):
            if role == "Famille":
                email = st.text_input("Adresse e-mail")
                password = st.text_input("Mot de passe", type="password")
            else:
                code = st.text_input("Code coach", type="password")
                password = st.text_input("Mot de passe coach", type="password")
            ok = st.form_submit_button("Se connecter")

            if ok:
                if role == "Famille":
                    users = query(
                        "SELECT * FROM families WHERE email=?", (email,)
                    )
                    if users and check_password(password, users[0]["password"]):
                        st.session_state.role = "family"
                        st.session_state.user_id = users[0]["id"]
                        st.session_state.user_name = users[0]["nom"]
                        st.rerun()
                    else:
                        st.error("Identifiants incorrects.")
                else:
                    if code not in COACH_CODES:
                        st.error("Code coach incorrect.")
                    else:
                        coaches = query(
                            "SELECT * FROM coaches WHERE nom=?",
                            (COACH_CODES[code],)
                        )
                        if coaches and check_password(
                            password, coaches[0]["password"]
                        ):
                            st.session_state.role = "coach"
                            st.session_state.user_id = coaches[0]["id"]
                            st.session_state.user_name = coaches[0]["nom"]
                            st.rerun()
                        else:
                            st.error(
                                "Compte coach non créé ou mot de passe incorrect."
                            )

    with tabs[7]:
        st.subheader("Créer un compte famille")
        st.write("Un seul compte parent peut gérer plusieurs enfants.")
        with st.form("register_form"):
            nom = st.text_input("Nom et prénom du responsable")
            email = st.text_input("Adresse e-mail")
            tel = st.text_input("Téléphone")
            adresse = st.text_input("Adresse postale")
            password = st.text_input("Créer un mot de passe", type="password")
            password2 = st.text_input("Confirmer le mot de passe", type="password")
            ok = st.form_submit_button("Créer mon compte")
            if ok:
                if not all([nom, email, tel, adresse, password, password2]):
                    st.error("Tous les champs sont obligatoires.")
                elif password != password2:
                    st.error("Les mots de passe ne correspondent pas.")
                elif len(password) < 8:
                    st.error("Choisis un mot de passe d'au moins 8 caractères.")
                elif query("SELECT id FROM families WHERE email=?", (email,)):
                    st.error("Cette adresse e-mail possède déjà un compte.")
                else:
                    execute("""
                    INSERT INTO families (nom,email,telephone,adresse,password)
                    VALUES (?,?,?,?,?)
                    """, (
                        nom, email, tel, adresse, hash_password(password)
                    ))
                    st.success("Compte créé ! Tu peux maintenant te connecter.")

# =====================================================
# ESPACE FAMILLE
# =====================================================

def family_page():
    fid = st.session_state.user_id
    family = query("SELECT * FROM families WHERE id=?", (fid,))[0]

    st.title(f"Bonjour {family['nom']} !")
    tabs = st.tabs([
        "Accueil", "Mes enfants", "Mon planning",
        "Espace DP", "Absences et rattrapages",
        "Stages et événements", "Notifications"
    ])

    with tabs[0]:
        st.subheader("Mon espace famille")
        st.write("Bienvenue dans votre espace personnel.")
        st.write("Adresse e-mail :", family["email"])
        st.write("Téléphone :", family["telephone"])
        st.write("Adresse :", family["adresse"])

    with tabs[1]:
        st.subheader("Mes enfants")
        for child in get_children(fid):
            with st.container(border=True):
                st.subheader(child["prenom"])
                photo_widget(child["photo"])
                st.write(f"Âge : {child['age']} ans")
                st.write(f"Poids : {child['poids']} kg")
                st.write(f"Taille : {child['taille']} cm")
                st.write(f"Niveau : {child['galop']}")

        st.markdown("### Ajouter un enfant")
        with st.form("add_child"):
            prenom = st.text_input("Prénom")
            age = st.number_input("Âge", min_value=2, max_value=25, value=8)
            poids = st.number_input("Poids (kg)", min_value=0.0, value=25.0)
            taille = st.number_input("Taille (cm)", min_value=0.0, value=120.0)
            galop = st.selectbox(
                "Niveau",
                ["Débutant", "Galop 1", "Galop 2", "Galop 3",
                 "Galop 4", "Galop 5", "Galop 6", "Galop 7"]
            )
            photo = st.file_uploader("Photo de l'enfant", type=["png", "jpg", "jpeg"])
            ok = st.form_submit_button("Ajouter")
            if ok and prenom:
                execute("""
                INSERT INTO children
                (family_id,prenom,age,poids,taille,galop,photo)
                VALUES (?,?,?,?,?,?,?)
                """, (
                    fid, prenom, age, poids, taille, galop,
                    photo.getvalue() if photo else None
                ))
                st.success("Enfant ajouté.")
                st.rerun()

    with tabs[2]:
        st.subheader("Mon planning")
        children = get_children(fid)
        if children:
            child = st.selectbox(
                "Choisir un enfant",
                children,
                format_func=lambda x: x["prenom"],
                key="family_planning_child"
            )
            rows = query("""
            SELECT slots.jour,slots.heure,slots.niveau,ponies.nom AS poney
            FROM assignments
            JOIN slots ON slots.id=assignments.slot_id
            LEFT JOIN ponies ON ponies.id=assignments.pony_id
            WHERE assignments.child_id=?
            ORDER BY slots.jour,slots.heure
            """, (child["id"],))
            if rows:
                for row in rows:
                    st.write(
                        f"**{row['jour']} à {row['heure']}** — "
                        f"{row['niveau']} — Poney : {row['poney'] or 'À définir'}"
                    )
            else:
                st.info("Aucun cours attribué pour le moment.")
        else:
            st.info("Ajoute d'abord un enfant à ton compte.")

    with tabs[3]:
        st.subheader("Espace demi-pension")
        st.write("""
        Les cavaliers en demi-pension peuvent demander leurs
        3 cours hebdomadaires parmi les créneaux proposés par le club.
        Le choix doit être validé par un coach.
        """)
        children = get_children(fid)
        if children:
            child = st.selectbox(
                "Pour quel enfant ?",
                children,
                format_func=lambda x: x["prenom"],
                key="dp_child"
            )
            slots = query(
                "SELECT * FROM slots WHERE actif=1 ORDER BY jour,heure"
            )
            if slots:
                st.write("Sélectionne exactement 3 cours.")
                choices = st.multiselect(
                    "Les 3 cours de la semaine",
                    options=[s["id"] for s in slots],
                    format_func=lambda sid: slot_label(
                        next(s for s in slots if s["id"] == sid)
                    ),
                    max_selections=3,
                    key="dp_choices"
                )
                if st.button("Envoyer ma demande de DP"):
                    if len(choices) != 3:
                        st.error("Tu dois choisir exactement 3 cours.")
                    else:
                        old = query("""
                        SELECT id FROM dp_requests
                        WHERE child_id=? AND statut='En attente'
                        """, (child["id"],))
                        if old:
                            st.warning("Une demande est déjà en attente.")
                        else:
                            execute("""
                            INSERT INTO dp_requests (child_id,slot_ids,statut)
                            VALUES (?,?,?)
                            """, (
                                child["id"], ",".join(map(str, choices)),
                                "En attente"
                            ))
                            st.success("Demande envoyée aux coachs.")
                requests = query(
                    "SELECT * FROM dp_requests WHERE child_id=? ORDER BY id DESC",
                    (child["id"],)
                )
                for req in requests:
                    st.write(f"Demande DP : **{req['statut']}**")
            else:
                st.info("Les coachs n'ont pas encore créé de créneaux.")
        else:
            st.info("Ajoute un enfant avant de faire une demande de DP.")

    with tabs[4]:
        st.subheader("Absences et rattrapages")
        children = get_children(fid)
        if children:
            child = st.selectbox(
                "Enfant concerné",
                children,
                format_func=lambda x: x["prenom"],
                key="absence_child"
            )
            slots = query("SELECT * FROM slots WHERE actif=1")
            with st.form("absence_form"):
                slot_id = st.selectbox(
                    "Cours concerné",
                    [s["id"] for s in slots],
                    format_func=lambda sid: slot_label(
                        next(s for s in slots if s["id"] == sid)
                    )
                ) if slots else None
                jour = st.date_input(
                    "Date du cours manqué",
                    min_value=date.today()
                )
                motif = st.text_area("Motif")
                ok = st.form_submit_button("Envoyer ma demande")
                if ok:
                    limite = datetime.combine(jour, time.min)
                    if limite < datetime.now() + timedelta(hours=24):
                        st.error("La demande doit être faite au moins 24 h à l'avance.")
                    elif slot_id is None:
                        st.error("Aucun cours disponible.")
                    else:
                        execute("""
                        INSERT INTO absences
                        (child_id,slot_id,date_absence,motif,created_at)
                        VALUES (?,?,?,?,?)
                        """, (
                            child["id"], slot_id, str(jour), motif,
                            datetime.now().isoformat()
                        ))
                        st.success("Demande envoyée.")
            for absence in query(
                "SELECT * FROM absences WHERE child_id=? ORDER BY id DESC",
                (child["id"],)
            ):
                st.write(
                    f"{absence['date_absence']} — {absence['statut']}"
                )

    with tabs[5]:
        st.subheader("Stages et événements")
        st.markdown("### Stages")
        for stage in query("SELECT * FROM stages ORDER BY date_stage"):
            st.write(
                f"**{stage['nom']}** — {stage['date_stage']} — "
                f"{stage['tarif']} €"
            )
        st.markdown("### Événements")
        for event in query("SELECT * FROM events ORDER BY date_event"):
            st.write(f"**{event['nom']}** — {event['date_event']}")
            st.write(event["description"])

    with tabs[6]:
        st.subheader("Mes notifications")
        notifications = query("""
        SELECT * FROM notifications
        WHERE family_id=? ORDER BY id DESC
        """, (fid,))
        if not notifications:
            st.info("Tu n'as pas encore de notification.")
        for n in notifications:
            st.write(f"🔔 {n['date_creation']} — {n['message']}")

# =====================================================
# ESPACE COACH
# =====================================================

def coach_page():
    st.title(f"Espace coach — {st.session_state.user_name}")
    tabs = st.tabs([
        "Tableau de bord", "Élèves", "Poneys",
        "Planning", "Demandes DP", "Absences",
        "Stages", "Événements", "Articles",
        "Balades réservées", "Inscriptions stages"
    ])

    with tabs[0]:
        st.subheader("Vue d'ensemble")
        c1, c2, c3 = st.columns(3)
        c1.metric("Familles", len(query("SELECT id FROM families")))
        c2.metric("Élèves", len(query("SELECT id FROM children")))
        c3.metric("Poneys", len(query("SELECT id FROM ponies")))
        st.write("Bienvenue dans la gestion du club.")

    with tabs[1]:
        st.subheader("Liste des élèves")
        for child in query("""
        SELECT children.*,families.nom AS famille
        FROM children LEFT JOIN families
        ON children.family_id=families.id
        ORDER BY prenom
        """):
            with st.container(border=True):
                st.write(
                    f"**{child['prenom']}** — Famille : {child['famille']}"
                )
                st.write(
                    f"{child['age']} ans • {child['poids']} kg • "
                    f"{child['taille']} cm • {child['galop']}"
                )
                photo_widget(child["photo"])
                ponies = query("SELECT * FROM ponies ORDER BY nom")
                if ponies:
                    current = query(
                        "SELECT pony_id FROM assignments WHERE child_id=? LIMIT 1",
                        (child["id"],)
                    )
                    default = current[0]["pony_id"] if current else ponies[0]["id"]
                    ids = [p["id"] for p in ponies]
                    selected = st.selectbox(
                        f"Poney de {child['prenom']}",
                        ids,
                        index=ids.index(default) if default in ids else 0,
                        format_func=lambda pid: next(
                            p["nom"] for p in ponies if p["id"] == pid
                        ),
                        key=f"pony_child_{child['id']}"
                    )
                    if st.button(
                        f"Attribuer le poney à {child['prenom']}",
                        key=f"assign_pony_{child['id']}"
                    ):
                        execute(
                            "DELETE FROM assignments WHERE child_id=?",
                            (child["id"],)
                        )
                        execute("""
                        INSERT INTO assignments (child_id,pony_id)
                        VALUES (?,?)
                        """, (child["id"], selected))
                        notify(
                            child["family_id"],
                            f"Un poney a été attribué à {child['prenom']}."
                        )
                        st.success("Poney attribué.")

    with tabs[2]:
        st.subheader("Gestion des poneys")
        with st.form("pony_form"):
            nom = st.text_input("Nom du poney")
            age = st.text_input("Âge")
            description = st.text_area("Caractère et description")
            photo = st.file_uploader(
                "Photo du poney", type=["png", "jpg", "jpeg"]
            )
            ok = st.form_submit_button("Ajouter le poney")
            if ok and nom:
                execute("""
                INSERT INTO ponies (nom,age,description,photo)
                VALUES (?,?,?,?)
                """, (
                    nom, age, description,
                    photo.getvalue() if photo else None
                ))
                st.success("Poney ajouté.")
                st.rerun()
        for pony in query("SELECT * FROM ponies ORDER BY nom"):
            with st.container(border=True):
                st.write(f"**{pony['nom']}** — {pony['age']}")
                photo_widget(pony["photo"])
                st.write(pony["description"])
                if st.button("Supprimer", key=f"delpony{pony['id']}"):
                    execute("DELETE FROM ponies WHERE id=?", (pony["id"],))
                    st.rerun()

    with tabs[3]:
        st.subheader("Planning hebdomadaire")
        st.write("Les créneaux créés ici reviennent chaque semaine.")
        jours = [
            "Lundi", "Mardi", "Mercredi", "Jeudi",
            "Vendredi", "Samedi", "Dimanche"
        ]
        with st.form("slot_form"):
            jour = st.selectbox("Jour", jours)
            heure = st.time_input("Heure du cours", value=time(14, 0))
            niveau = st.selectbox(
                "Niveau",
                ["Baby poney", "Débutant", "Galop 1-2",
                 "Galop 3-4", "Galop 5-7", "Tous niveaux"]
            )
            places = st.number_input(
                "Nombre de places", min_value=1, max_value=20, value=8
            )
            ok = st.form_submit_button("Ajouter le cours récurrent")
            if ok:
                execute("""
                INSERT INTO slots (jour,heure,niveau,places)
                VALUES (?,?,?,?)
                """, (jour, heure.strftime("%H:%M"), niveau, places))
                st.success("Créneau ajouté.")
                st.rerun()

        for slot in query("SELECT * FROM slots ORDER BY jour,heure"):
            with st.container(border=True):
                st.write(
                    f"**{slot_label(slot)}** — {slot['places']} places"
                )
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Annuler ce cours", key=f"cancel{slot['id']}"):
                        execute(
                            "UPDATE slots SET actif=0 WHERE id=?",
                            (slot["id"],)
                        )
                        st.success("Cours désactivé.")
                        st.rerun()
                with col2:
                    if st.button("Réactiver", key=f"react{slot['id']}"):
                        execute(
                            "UPDATE slots SET actif=1 WHERE id=?",
                            (slot["id"],)
                        )
                        st.rerun()

        st.markdown("### Déplacer un cours")
        active_slots = query("SELECT * FROM slots WHERE actif=1")
        if active_slots:
            selected = st.selectbox(
                "Cours à déplacer",
                [s["id"] for s in active_slots],
                format_func=lambda sid: slot_label(
                    next(s for s in active_slots if s["id"] == sid)
                )
            )
            new_day = st.selectbox("Nouveau jour", jours, key="move_day")
            new_time = st.time_input("Nouvelle heure", key="move_time")
            if st.button("Enregistrer le déplacement"):
                execute("""
                UPDATE slots SET jour=?,heure=? WHERE id=?
                """, (new_day, new_time.strftime("%H:%M"), selected))
                st.success("Créneau modifié.")
                st.rerun()

    with tabs[4]:
        st.subheader("Demandes de demi-pension")
        requests = query("""
        SELECT dp_requests.*,children.prenom,children.family_id
        FROM dp_requests JOIN children
        ON children.id=dp_requests.child_id
        ORDER BY dp_requests.id DESC
        """)
        for req in requests:
            with st.container(border=True):
                st.write(f"**{req['prenom']}** — {req['statut']}")
                ids = [int(x) for x in req["slot_ids"].split(",") if x]
                for sid in ids:
                    found = query("SELECT * FROM slots WHERE id=?", (sid,))
                    if found:
                        st.write(slot_label(found[0]))
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Valider la DP", key=f"acceptdp{req['id']}"):
                        execute(
                            "UPDATE dp_requests SET statut='Validée' WHERE id=?",
                            (req["id"],)
                        )
                        for sid in ids:
                            execute("""
                            INSERT INTO assignments (child_id,slot_id)
                            VALUES (?,?)
                            """, (req["child_id"], sid))
                        notify(
                            req["family_id"],
                            f"La demande de DP de {req['prenom']} a été validée."
                        )
                        st.rerun()
                with c2:
                    if st.button("Refuser", key=f"refusedp{req['id']}"):
                        execute(
                            "UPDATE dp_requests SET statut='Refusée' WHERE id=?",
                            (req["id"],)
                        )
                        notify(
                            req["family_id"],
                            f"La demande de DP de {req['prenom']} a été refusée."
                        )
                        st.rerun()

    with tabs[5]:
        st.subheader("Demandes d'absence")
        for absence in query("""
        SELECT absences.*,children.prenom,children.family_id
        FROM absences JOIN children ON children.id=absences.child_id
        ORDER BY absences.id DESC
        """):
            with st.container(border=True):
                st.write(
                    f"**{absence['prenom']}** — {absence['date_absence']}"
                )
                st.write(absence["motif"])
                st.write("Statut :", absence["statut"])
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Accepter", key=f"acceptabs{absence['id']}"):
                        execute(
                            "UPDATE absences SET statut='Acceptée' WHERE id=?",
                            (absence["id"],)
                        )
                        notify(
                            absence["family_id"],
                            f"Absence de {absence['prenom']} acceptée."
                        )
                        st.rerun()
                with c2:
                    if st.button("Refuser", key=f"refuseabs{absence['id']}"):
                        execute(
                            "UPDATE absences SET statut='Refusée' WHERE id=?",
                            (absence["id"],)
                        )
                        notify(
                            absence["family_id"],
                            f"Absence de {absence['prenom']} refusée."
                        )
                        st.rerun()

    with tabs[6]:
        st.subheader("Créer un stage")
        with st.form("create_stage"):
            nom = st.text_input("Nom du stage")
            discipline = st.text_input("Discipline")
            jour = st.date_input("Date du stage")
            horaire = st.text_input("Horaire", "9h-17h")
            niveau = st.text_input("Niveau minimum")
            places = st.number_input(
                "Nombre de places", min_value=1, value=8
            )
            tarif = st.number_input("Tarif (€)", min_value=0.0)
            ok = st.form_submit_button("Publier le stage")
            if ok and nom:
                execute("""
                INSERT INTO stages
                (nom,discipline,date_stage,horaire,niveau,places,tarif)
                VALUES (?,?,?,?,?,?,?)
                """, (
                    nom, discipline, str(jour), horaire,
                    niveau, places, tarif
                ))
                st.success("Stage publié.")
                st.rerun()
        for stage in query("SELECT * FROM stages ORDER BY date_stage"):
            st.write(
                f"{stage['nom']} — {stage['date_stage']} — {stage['tarif']} €"
            )

    with tabs[7]:
        st.subheader("Ajouter un événement")
        with st.form("create_event"):
            nom = st.text_input("Nom de l'événement")
            jour = st.date_input("Date", key="event_date")
            description = st.text_area("Description")
            ok = st.form_submit_button("Publier l'événement")
            if ok and nom:
                execute("""
                INSERT INTO events (nom,date_event,description)
                VALUES (?,?,?)
                """, (nom, str(jour), description))
                st.success("Événement publié.")
                st.rerun()

    with tabs[8]:
        st.subheader("Rédiger un article")
        with st.form("article_form"):
            titre = st.text_input("Titre de l'article")
            contenu = st.text_area("Texte de l'article")
            photo = st.file_uploader(
                "Ajouter une photo", type=["png", "jpg", "jpeg"]
            )
            ok = st.form_submit_button("Publier l'article")
            if ok and titre and contenu:
                execute("""
                INSERT INTO articles (titre,contenu,photo,date_article)
                VALUES (?,?,?,?)
                """, (
                    titre, contenu,
                    photo.getvalue() if photo else None,
                    date.today().strftime("%d/%m/%Y")
                ))
                st.success("Article publié.")
                st.rerun()

    with tabs[9]:
        st.subheader("Réservations de balades")
        for booking in query(
            "SELECT * FROM walk_bookings ORDER BY date_balade"
        ):
            with st.container(border=True):
                st.write(f"**{booking['enfant']}**")
                st.write(f"Responsable : {booking['responsable']}")
                st.write(f"Téléphone : {booking['telephone']}")
                st.write(f"E-mail : {booking['email']}")
                st.write(
                    f"{booking['date_balade']} à {booking['heure']}"
                )
                st.write(f"Tarif : {booking['tarif']} €")

    with tabs[10]:
        st.subheader("Inscriptions aux stages")
        for reg in query("""
        SELECT stage_regs.*,stages.nom AS stage
        FROM stage_regs JOIN stages
        ON stages.id=stage_regs.stage_id
        ORDER BY stage_regs.id DESC
        """):
            st.write(
                f"**{reg['nom_enfant']}** — {reg['stage']} — "
                f"{reg['nom_responsable']} — {reg['telephone']}"
            )

# =====================================================
# PREMIERE CREATION DES COMPTES COACHS
# =====================================================

def coach_setup():
    st.subheader("Première création des comptes coachs")
    st.write("""
    Cette étape permet de créer les deux comptes coach.
    Elle ne sera plus nécessaire une fois les comptes créés.
    """)
    for code, nom in COACH_CODES.items():
        existing = query("SELECT id FROM coaches WHERE nom=?", (nom,))
        if not existing:
            st.markdown(f"### {nom}")
            with st.form(f"setup_{nom}"):
                password = st.text_input(
                    f"Créer le mot de passe de {nom}",
                    type="password"
                )
                confirm = st.text_input(
                    "Confirmer le mot de passe",
                    type="password"
                )
                ok = st.form_submit_button(f"Créer {nom}")
                if ok:
                    if len(password) < 8:
                        st.error("8 caractères minimum.")
                    elif password != confirm:
                        st.error("Les mots de passe ne correspondent pas.")
                    else:
                        execute(
                            "INSERT INTO coaches (nom,password) VALUES (?,?)",
                            (nom, hash_password(password))
                        )
                        st.success(f"Compte {nom} créé.")
                        st.rerun()

# =====================================================
# NAVIGATION GENERALE
# =====================================================

if st.session_state.role == "family":
    col1, col2 = st.columns([5, 1])
    with col2:
        if st.button("Déconnexion"):
            st.session_state.clear()
            st.rerun()
    family_page()

elif st.session_state.role == "coach":
    col1, col2 = st.columns([5, 1])
    with col2:
        if st.button("Déconnexion"):
            st.session_state.clear()
            st.rerun()
    coach_page()

else:
    public_page()
    st.divider()
    with st.expander("Configuration initiale des comptes coachs"):
        coach_setup()
