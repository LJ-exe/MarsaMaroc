"""Authentification Supabase Auth + profils utilisateurs."""



from functools import wraps



from flask import redirect, request, session, url_for



ROLES_VALIDES = ("stagiaire", "rh", "affectation")

ROLE_INSCRIPTION = "stagiaire"



# Emails réservés — comptes créés uniquement dans Supabase Authentication

EMAILS_RESERVES_INSCRIPTION = frozenset(

    {

        "rh@marsamaroc.ma",

        "aff@marsamaroc.ma",

    }

)



REDIRECTION_PAR_ROLE = {

    "stagiaire": "/stagiaire",

    "rh": "/rh",

    "affectation": "/affectation",

}





def utilisateur_connecte():

    return bool(session.get("user_id"))





def role_utilisateur():

    return session.get("role") or ROLE_INSCRIPTION





def nom_utilisateur():

    return session.get("user_name") or session.get("user_email") or "Utilisateur"





def redirection_pour_role(role=None):

    """URL de redirection selon le rôle."""

    return REDIRECTION_PAR_ROLE.get(role or role_utilisateur(), "/stagiaire")





def inscription_autorisee(email: str, role_demande: str | None = None):

    """

    Vérifie si l'inscription publique est permise.

    Retourne (ok: bool, message_erreur: str | None).

    """

    email = (email or "").strip().lower()

    if email in EMAILS_RESERVES_INSCRIPTION:

        return (

            False,

            "Cet email est réservé au personnel Marsa Maroc. "

            "Les comptes RH et Affectation sont créés par l'administrateur — utilisez la connexion.",

        )

    if role_demande and role_demande != ROLE_INSCRIPTION:

        return False, "Seuls les stagiaires peuvent créer un compte via cette page."

    return True, None





def role_depuis_profil(profil: dict | None) -> str | None:

    """Extrait et valide le rôle depuis la table profiles."""

    if not profil:

        return None

    role = (profil.get("role") or "").strip().lower()

    if role in ROLES_VALIDES:

        return role

    return None





def enregistrer_session(auth_response, profil=None, *, inscription=False):

    """

    Enregistre la session Flask après connexion ou inscription.



    - inscription=True : rôle forcé à stagiaire

    - inscription=False (login) : rôle lu uniquement depuis profiles

    """

    utilisateur = auth_response.user

    meta = utilisateur.user_metadata or {}



    if inscription:

        role = ROLE_INSCRIPTION

        nom = (

            (profil or {}).get("name")

            or meta.get("full_name")

            or meta.get("name")

            or utilisateur.email

        )

    else:

        role = role_depuis_profil(profil)

        if not role:

            return False

        nom = profil.get("name") or utilisateur.email



    session.clear()

    session["user_id"] = utilisateur.id

    session["user_email"] = utilisateur.email

    session["user_name"] = nom

    session["role"] = role



    if auth_response.session:

        session["access_token"] = auth_response.session.access_token

        session["refresh_token"] = auth_response.session.refresh_token



    return True





def rafraichir_token_si_expire(client):
    """Tente de rafraîchir le token JWT s'il est expiré."""
    refresh = session.get("refresh_token")
    if not refresh:
        return False
    
    try:
        session_response = client.auth.refresh_session(refresh)
        if session_response.session:
            session["access_token"] = session_response.session.access_token
            session["refresh_token"] = session_response.session.refresh_token
            return True
    except Exception as exc:
        print(f"[AUTH] Erreur rafraîchissement token: {exc}")
        return False


def appliquer_session_supabase(client):
    """Réapplique le JWT Supabase sur le client pour les requêtes authentifiées."""
    token = session.get("access_token")
    refresh = session.get("refresh_token")
    
    if token and refresh:
        try:
            client.auth.set_session(token, refresh)
        except Exception as exc:
            print(f"[AUTH] Erreur set_session: {exc}")
            # Tenter de rafraîchir le token
            if rafraichir_token_si_expire(client):
                token = session.get("access_token")
                refresh = session.get("refresh_token")
                if token and refresh:
                    client.auth.set_session(token, refresh)





def charger_profil(client, user_id):

    """Charge le profil depuis la table profiles (source de vérité pour le rôle)."""

    try:

        reponse = (

            client.table("profiles")

            .select("name, role")

            .eq("id", user_id)

            .single()

            .execute()

        )

        return reponse.data

    except Exception:

        return None





def profil_depuis_auth_user(user):

    """Construit un profil minimal à partir de auth.users (secours si table profiles vide)."""

    email = getattr(user, "email", None) or (user.get("email") if isinstance(user, dict) else "")

    email = (email or "").strip().lower()

    meta = getattr(user, "user_metadata", None) or (user.get("user_metadata") if isinstance(user, dict) else {}) or {}

    role = ROLE_INSCRIPTION

    name = meta.get("full_name") or meta.get("name") or email or "Utilisateur"



    if email == "rh@marsamaroc.ma":

        role, name = "rh", "Responsable RH"

    elif email == "aff@marsamaroc.ma":

        role, name = "affectation", "Responsable Affectation"



    return {"name": name, "role": role}





def assurer_profil(client, user):

    """

    Charge le profil ou le crée/synchronise si manquant (après login réussi).

    """

    user_id = getattr(user, "id", None) or (user.get("id") if isinstance(user, dict) else None)

    user_email = getattr(user, "email", None) or (user.get("email") if isinstance(user, dict) else None)

    if not user_id:

        return None



    profil = charger_profil(client, user_id)

    if profil and role_depuis_profil(profil):

        return profil



    profil = profil_depuis_auth_user(user)

    try:

        client.table("profiles").upsert(

            {

                "id": user_id,

                "name": profil["name"],

                "email": user_email,

                "role": profil["role"],

            }

        ).execute()

    except Exception as exc:

        print(f"[AUTH] Upsert profil ignoré: {exc}")



    return profil





def cible_apres_login(role, next_url=None):

    """

    Détermine la redirection après login.

    Le paramètre next n'est honoré que s'il correspond au rôle de l'utilisateur.

    """

    cible_defaut = redirection_pour_role(role)

    if not next_url:

        return cible_defaut

    chemins_autorises = set(REDIRECTION_PAR_ROLE.values())

    if next_url in chemins_autorises and next_url == redirection_pour_role(role):

        return next_url

    return cible_defaut





def message_erreur_auth(exc):

    """Traduit les erreurs Supabase Auth en messages lisibles."""

    texte = str(exc).lower()

    if "database error saving new user" in texte:

        return (

            "Erreur base de données à la création du compte. "

            "Exécutez supabase_fix_auth_trigger.sql dans Supabase, puis réessayez."

        )

    if "rate limit" in texte or "too many requests" in texte:

        return "Trop de tentatives. Attendez 2 minutes puis réessayez."

    if "invalid login credentials" in texte or "invalid_credentials" in texte:

        return (

            "Connexion refusée : ce compte n'existe pas dans Supabase Authentication, "

            "ou le mot de passe est incorrect. "

            "Créez le compte dans Supabase (Users → Add user, cochez « Auto Confirm User ») "

            "ou lancez : python scripts/creer_comptes_admin.py"

        )

    if "user already registered" in texte or "already been registered" in texte:

        return "Cet email est déjà utilisé. Connectez-vous ou utilisez un autre email."

    if "password should be at least" in texte or "weak password" in texte:

        return "Le mot de passe doit contenir au moins 6 caractères."

    if "unable to validate email" in texte or "invalid email" in texte:

        return "Adresse email invalide."

    if "email not confirmed" in texte or "email_not_confirmed" in texte:

        return "Confirmez votre email avant de vous connecter (vérifiez votre boîte mail)."

    if "signup is disabled" in texte:

        return "Les inscriptions sont désactivées sur ce projet Supabase."

    return "Une erreur est survenue. Réessayez ou contactez l'administrateur."





def login_required(*roles_autorises):

    """Protège une route : connexion obligatoire, rôle optionnel."""



    def decorator(view):

        @wraps(view)

        def wrapper(*args, **kwargs):

            if not utilisateur_connecte():

                return redirect(url_for("login", next=request.path))

            if roles_autorises and role_utilisateur() not in roles_autorises:

                return redirect(redirection_pour_role())

            return view(*args, **kwargs)



        return wrapper



    return decorator

