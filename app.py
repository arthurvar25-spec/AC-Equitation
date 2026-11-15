
import streamlit as st
from datetime import date, time

# =====================================
# CONFIGURATION
# =====================================

st.set_page_config(
    page_title="AC Équitation",
    page_icon="🐴",
    layout="wide"
)

st.markdown("""
<style>
.stApp {
    background-color: #F7F5EE;
}
h1, h2, h3 {
    color: #526B53;
}
section[data-testid="stSidebar"] {
    background-color: #E6EBDD;
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
</style>
""", unsafe_allow_html=True)


# =====================================
# DONNEES
# =====================================

if "poneys" not in st.session_state:
    st.session_state.poneys = [
        {
            "nom": "Caramel",
            "age": "8 ans",
            "caractere": "Gentil et gourmand"
        },
        {
            "nom": "Chocolat",
            "age": "6 ans",
            "caractere": "Calme et joueur"
        }
    ]

if "enfants" not in st.session_state:
    st.session_state.enfants = [
        {
            "nom": "Léa",
            "famille": "Famille Martin",
            "niveau": "Débutant"
        },
        {
            "nom": "Noah",
            "famille": "Famille Martin",
            "niveau": "Galop 1"
        }
    ]

if "cours" not in st.session_state:
    st.session_state.cours = [
        {
            "jour": "Mercredi",
            "heure": "14:00",
            "niveau": "Débutant",
            "moniteur": "Moniteur"
        },
        {
            "jour": "Samedi",
            "heure": "10:00",
            "niveau": "Galop 1",
            "moniteur": "Moniteur"
        }
    ]

if "absences" not in st.session_state:
    st.session_state.absences = []

if "rattrapages" not in st.session_state:
    st.session_state.rattrapages = []

if "evenements" not in st.session_state:
    st.session_state.evenements = [
        {
            "nom": "Stage de printemps",
            "date": "À définir",
            "places": 10
        },
        {
            "nom": "Fête du club",
            "date": "À définir",
            "places": 30
        }
    ]

if "inscriptions" not in st.session_state:
    st.session_state.inscriptions = []


# =====================================
# MENU
# =====================================

st.sidebar.title("🐴 AC ÉQUITATION")
st.sidebar.caption("Application du club")

page = st.sidebar.radio(
    "MENU PRINCIPAL",
    [
        "Accueil",
        "Espace familles",
        "Espace moniteur",
        "Nos poneys",
        "Planning des cours",
        "Absences",
        "Stages et événements"
    ]
)

st.sidebar.divider()
st.sidebar.caption("AC Équitation")


# =====================================
# ACCUEIL
# =====================================

if page == "Accueil":

    st.title("🐴 AC ÉQUITATION")
    st.subheader("Bienvenue dans votre club !")

    st.write(
        "Retrouvez toutes les informations "
        "du club sur votre espace personnel."
    )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Poneys",
        len(st.session_state.poneys)
    )

    col2.metric(
        "Enfants",
        len(st.session_state.enfants)
    )

    col3.metric(
        "Événements",
        len(st.session_state.evenements)
    )

    st.divider()

    st.subheader("Bienvenue chez AC Équitation")

    gauche, droite = st.columns(2)

    with gauche:
        st.markdown("### 👨‍👩‍👧 Espace familles")
        st.write(
            "Consultez les cours, les poneys "
            "et les événements du club."
        )

    with droite:
        st.markdown("### 📝 Espace moniteur")
        st.write(
            "Gérez les enfants, les cours, "
            "les poneys et les demandes."
        )


# =====================================
# ESPACE FAMILLES
# =====================================

elif page == "Espace familles":

    st.title("👨‍👩‍👧 Espace familles")

    st.write("Bienvenue dans votre espace famille.")

    st.subheader("Mes enfants")

    if st.session_state.enfants:
        st.dataframe(
            st.session_state.enfants,
            use_container_width=True
        )
    else:
        st.info("Aucun enfant enregistré.")

    st.divider()

    st.subheader("Planning des cours")

    st.dataframe(
        st.session_state.cours,
        use_container_width=True
    )

    st.divider()

    st.subheader("Mes inscriptions")

    st.dataframe(
        st.session_state.inscriptions,
        use_container_width=True
    )


# =====================================
# ESPACE MONITEUR
# =====================================

elif page == "Espace moniteur":

    st.title("📝 Espace moniteur")

    st.warning(
        "Version de démonstration : "
        "cet espace n'est pas protégé par un mot de passe."
    )

    onglet1, onglet2, onglet3 = st.tabs([
        "Enfants",
        "Ajouter un enfant",
        "Créer un cours"
    ])

    with onglet1:

        st.subheader("Liste des enfants")

        st.dataframe(
            st.session_state.enfants,
            use_container_width=True
        )

    with onglet2:

        st.subheader("Ajouter un enfant")

        with st.form("ajout_enfant"):

            nom = st.text_input("Nom de l'enfant")
            famille = st.text_input("Nom de la famille")

            niveau = st.selectbox(
                "Niveau",
                [
                    "Baby poney",
                    "Débutant",
                    "Galop 1",
                    "Galop 2",
                    "Galop 3",
                    "Galop 4",
                    "Galop 5",
                    "Galop 6",
                    "Galop 7"
                ]
            )

            valider = st.form_submit_button(
                "Ajouter l'enfant"
            )

            if valider:

                if nom.strip() and famille.strip():

                    st.session_state.enfants.append({
                        "nom": nom,
                        "famille": famille,
                        "niveau": niveau
                    })

                    st.success("Enfant ajouté !")

                else:
                    st.error("Remplis tous les champs.")

    with onglet3:

        st.subheader("Créer un cours")

        with st.form("ajout_cours"):

            jour = st.selectbox(
                "Jour",
                [
                    "Lundi",
                    "Mardi",
                    "Mercredi",
                    "Jeudi",
                    "Vendredi",
                    "Samedi",
                    "Dimanche"
                ]
            )

            heure = st.time_input(
                "Heure du cours",
                time(14, 0)
            )

            niveau_cours = st.selectbox(
                "Niveau",
                [
                    "Baby poney",
                    "Débutant",
                    "Galop 1",
                    "Galop 2",
                    "Galop 3",
                    "Galop 4",
                    "Galop 5",
                    "Galop 6",
                    "Galop 7"
                ]
            )

            moniteur = st.text_input("Nom du moniteur")

            valider_cours = st.form_submit_button(
                "Créer le cours"
            )

            if valider_cours:

                st.session_state.cours.append({
                    "jour": jour,
                    "heure": heure.strftime("%H:%M"),
                    "niveau": niveau_cours,
                    "moniteur": moniteur
                })

                st.success("Cours créé !")

    st.divider()

    st.subheader("Gestion des absences")

    for i, demande in enumerate(st.session_state.absences):

        st.write(
            f"**{demande['enfant']}** | "
            f"{demande['date']} | "
            f"{demande['motif']} | "
            f"{demande['statut']}"
        )

        if demande["statut"] == "En attente":

            col1, col2 = st.columns(2)

            if col1.button("Accepter", key=f"a{i}"):

                demande["statut"] = "Acceptée"
                st.rerun()

            if col2.button("Refuser", key=f"r{i}"):

                demande["statut"] = "Refusée"
                st.rerun()

    st.divider()

    st.subheader("Demandes de rattrapage")

    for i, demande in enumerate(st.session_state.rattrapages):

        st.write(
            f"{demande['enfant']} | "
            f"{demande['date']} | "
            f"{demande['statut']}"
        )

        if demande["statut"] == "En attente":

            col1, col2 = st.columns(2)

            if col1.button("Accepter", key=f"ra{i}"):

                demande["statut"] = "Acceptée"
                st.rerun()

            if col2.button("Refuser", key=f"rr{i}"):

                demande["statut"] = "Refusée"
                st.rerun()


# =====================================
# PONEYS
# =====================================

elif page == "Nos poneys":

    st.title("🐴 Nos poneys")

    st.write("Découvrez les poneys du club.")

    for poney in st.session_state.poneys:

        with st.container(border=True):

            st.subheader("🐴 " + poney["nom"])

            st.write("Âge :", poney["age"])

            st.write(
                "Caractère :",
                poney["caractere"]
            )

    st.divider()

    st.subheader("Ajouter un poney")

    with st.form("ajout_poney"):

        nom = st.text_input("Nom du poney")

        age = st.text_input("Âge")

        caractere = st.text_area(
            "Caractère et particularités"
        )

        ajouter = st.form_submit_button(
            "Ajouter le poney"
        )

        if ajouter:

            if nom.strip():

                st.session_state.poneys.append({
                    "nom": nom,
                    "age": age,
                    "caractere": caractere
                })

                st.success("Poney ajouté !")

            else:
                st.error("Indique le nom du poney.")


# =====================================
# PLANNING
# =====================================

elif page == "Planning des cours":

    st.title("📅 Planning des cours")

    st.dataframe(
        st.session_state.cours,
        use_container_width=True
    )


# =====================================
# ABSENCES ET RATTRAPAGES
# =====================================

elif page == "Absences":

    st.title("📋 Absences")

    enfants = [
        enfant["nom"]
        for enfant in st.session_state.enfants
    ]

    if enfants:

        st.subheader("Déclarer une absence")

        with st.form("declaration_absence"):

            enfant = st.selectbox(
                "Enfant concerné",
                enfants
            )

            date_absence = st.date_input(
                "Date de l'absence"
            )

            motif = st.text_area(
                "Motif de l'absence"
            )

            envoyer = st.form_submit_button(
                "Envoyer ma demande"
            )

            if envoyer:

                st.session_state.absences.append({
                    "enfant": enfant,
                    "date": str(date_absence),
                    "motif": motif,
                    "statut": "En attente"
                })

                st.success("Demande envoyée !")

        st.divider()

        st.subheader("Demander un rattrapage")

        with st.form("demande_rattrapage"):

            enfant_r = st.selectbox(
                "Enfant concerné",
                enfants,
                key="enfant_r"
            )

            date_r = st.date_input(
                "Date souhaitée",
                key="date_r"
            )

            envoyer_r = st.form_submit_button(
                "Envoyer la demande"
            )

            if envoyer_r:

                st.session_state.rattrapages.append({
                    "enfant": enfant_r,
                    "date": str(date_r),
                    "statut": "En attente"
                })

                st.success("Demande de rattrapage envoyée !")

    else:
        st.info("Aucun enfant enregistré.")


# =====================================
# STAGES ET EVENEMENTS
# =====================================

elif page == "Stages et événements":

    st.title("🎉 Stages et événements")

    for evenement in st.session_state.evenements:

        with st.container(border=True):

            st.subheader(evenement["nom"])

            st.write("Date :", evenement["date"])

            st.write(
                "Nombre de places :",
                evenement["places"]
            )

    st.divider()

    st.subheader("Inscrire un enfant")

    enfants = [
        enfant["nom"]
        for enfant in st.session_state.enfants
    ]

    evenements = [
        evenement["nom"]
        for evenement in st.session_state.evenements
    ]

    if enfants and evenements:

        with st.form("inscription"):

            enfant = st.selectbox(
                "Choisir un enfant",
                enfants
            )

            evenement = st.selectbox(
                "Choisir un événement",
                evenements
            )

            inscrire = st.form_submit_button(
                "M'inscrire"
            )

            if inscrire:

                st.session_state.inscriptions.append({
                    "enfant": enfant,
                    "evenement": evenement
                })

                st.success("Inscription enregistrée !")

    st.divider()

    st.subheader("Ajouter un événement")

    with st.form("ajout_evenement"):

        nom = st.text_input("Nom de l'événement")

        date_event = st.date_input(
            "Date de l'événement"
        )

        places = st.number_input(
            "Nombre de places",
            min_value=1,
            value=10
        )

        ajouter = st.form_submit_button(
            "Ajouter l'événement"
        )

        if ajouter:

            if nom.strip():

                st.session_state.evenements.append({
                    "nom": nom,
                    "date": str(date_event),
                    "places": places
                })

                st.success("Événement ajouté !")

            else:
                st.error("Indique le nom de l'événement.")


# =====================================
# PIED DE PAGE
# =====================================

st.divider()

st.caption(
    "AC Équitation | Application de démonstration"
)
