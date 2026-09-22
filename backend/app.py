import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from pdfrw import PdfReader, PdfWriter

try:
    import pythoncom
    import win32com.client
except ImportError:
    pythoncom = None
    win32com = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
FRONTEND_DIR = os.path.join(PROJECT_ROOT, 'frontend')
FRONTEND_TEMPLATES_FOLDER = os.path.join(FRONTEND_DIR, 'templates')
FRONTEND_STATIC_FOLDER = os.path.join(FRONTEND_DIR, 'static')
STORAGE_DIR = os.path.join(BASE_DIR, 'storage')
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))
load_dotenv(os.path.join(PROJECT_ROOT, '.env.local'), override=True)

from flask import Flask, jsonify, redirect, render_template, request, send_file, session, url_for
from werkzeug.utils import secure_filename

from .auth_helpers import (
    ROLE_INSCRIPTION,
    appliquer_session_supabase,
    assurer_profil,
    cible_apres_login,
    enregistrer_session,
    inscription_autorisee,
    login_required,
    message_erreur_auth,
    nom_utilisateur,
    redirection_pour_role,
    role_utilisateur,
    utilisateur_connecte,
)
from .db_config import (
    STATUT_INITIAL_DB,
    TABLE_APPLICATIONS,
    appliquer_filtre_identifiant,
    colonne_manquante_dans_erreur,
    creer_client_supabase,
    donnees_pour_insertion,
    message_hint_rh,
    normaliser_candidat,
    statut_pour_db,
    statut_pour_affichage,
    supabase_executer_insert,
    supabase_executer_update_eq,
)

# App configuration
app = Flask(
    __name__,
    template_folder=FRONTEND_TEMPLATES_FOLDER,
    static_folder=FRONTEND_STATIC_FOLDER,
)
app.secret_key = os.getenv("SECRET_KEY", "marsa-maroc-dev-secret-changez-moi")

UPLOAD_FOLDER = os.path.join(STORAGE_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['GENERATED_PDFS_FOLDER'] = os.path.join(STORAGE_DIR, 'generated_pdfs')
app.config['PDF_TEMPLATES_FOLDER'] = os.path.join(BASE_DIR, 'pdf')

SUPABASE_URL = (os.getenv("SUPABASE_URL") or "").strip()
SUPABASE_KEY = (os.getenv("SUPABASE_KEY") or "").strip()
SUPABASE_SERVICE_ROLE_KEY = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()

supabase = creer_client_supabase(SUPABASE_URL, SUPABASE_KEY)
supabase_admin = creer_client_supabase(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY) if SUPABASE_SERVICE_ROLE_KEY else None


DOCUMENTS_REQUIS = ("cv", "cin", "assurance", "convention", "demande")

DOC_LABELS = {
    "cv": "CV (Curriculum Vitae)",
    "cin": "CIN (Carte d'Identité)",
    "assurance": "Attestation d'Assurance",
    "convention": "Convention de Stage",
    "demande": "Demande de Stage",
}

OUTLOOK_DOCUMENT_MESSAGES = {

    "fiche_accueil": {
        "subject": "Fiche d'accueil de stage | Marsa Maroc",
        "body": """Bonjour {name},

Veuillez trouver en pièce jointe votre fiche d'accueil de stage au sein de Marsa Maroc.

Nous vous invitons à prendre connaissance des informations relatives à votre affectation.

Cordialement,

Direction du Capital Humain
Marsa Maroc"""
    },

    "decision_stage": {
        "subject": "Décision de stage | Marsa Maroc",
        "body": """Bonjour {name},

Veuillez trouver en pièce jointe votre décision de stage officielle.

Ce document précise les informations relatives à votre stage au sein de Marsa Maroc.

Cordialement,

Direction du Capital Humain
Marsa Maroc"""
    },

    "evaluation": {
        "subject": "Fiche d'appréciation de stage | Marsa Maroc",
        "body": """Bonjour {name},

Votre fiche d'appréciation de stage a été validée.

Veuillez trouver le document en pièce jointe.

Cordialement,

Direction du Capital Humain
Marsa Maroc"""
    },

    "attestation": {
        "subject": "Attestation de stage | Marsa Maroc",
        "body": """Bonjour {name},

Nous vous transmettons votre attestation de stage.

Veuillez trouver votre attestation officielle en pièce jointe.

Cordialement,

Direction du Capital Humain
Marsa Maroc"""
    },
}



HINT_NOUVEAU_DOCUMENT = "📩 Nouveau document envoyé par le stagiaire"
HINT_PDF_RENVOYE = "📄 PDF renvoyé par le stagiaire"

 

POLES = [
    "DSI - Direction Systèmes d'Information",
    "DCH - Capital Humain",
    "DAF - Finance & Contrôle",
    "DOF - Opérations Portuaires",
]

ZONES = [
    "Siège Social - Casablanca",
    "Terminal à conteneurs TC3",
    "Port Tanger Med I",
    "Port d'Agadir",
]


def formater_date_soumission(iso):
    if not iso:
        return "Non renseignée"
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        return dt.strftime("%d %b %Y, %H:%M")
    except (ValueError, TypeError):
        return "Non renseignée"


def enrichir_candidats(candidats):
    resultat = []

    for c in candidats or []:
        ligne = normaliser_candidat(c)

        # Conserver les données d'affectation directement depuis Supabase
        ligne["mentor"] = c.get("mentor") or ""
        ligne["encadrant_id"] = c.get("encadrant_id")
        ligne["project"] = c.get("project") or ""
        ligne["fiche_accueil_pdf"] = c.get("fiche_accueil_pdf")
        # Le stagiaire est considéré comme affecté
        # lorsque la fiche d'accueil a été générée par le service Affectation
        ligne["est_affecte"] = bool(
            ligne.get("fiche_accueil_pdf")
        )

        # Rapport de stage
        ligne["intern_report_path"] = c.get("intern_report_path")
        ligne["intern_report_status"] = c.get("intern_report_status") or ""

        # Fiche d'évaluation
        ligne["evaluation_pdf"] = c.get("evaluation_pdf")
        ligne["evaluation_status"] = c.get("evaluation_status") or ""
        ligne["evaluation_submitted_at"] = c.get("evaluation_submitted_at")
        ligne["evaluation_reject_reason"] = c.get("evaluation_reject_reason")

        #decision de stage
        
        ligne["decision_pdf"] = c.get(
            "decision_pdf"
        )

        ligne["decision_numero"] = c.get(
            "decision_numero"
        )

        ligne["decision_reference"] = c.get(
            "decision_reference"
        )

        ligne["decision_status"] = (
            c.get("decision_status")
            or ""
        )

        ligne["decision_generated_at"] = c.get(
            "decision_generated_at"
        )
        
        ligne["decision_data"] = (
            c.get("decision_data")
            or {}
        )

        ligne["decision_updated_at"] = c.get(
            "decision_updated_at"
        )
        
        # True dès que la fiche a été soumise ou validée par la RH
        ligne["evaluation_deja_soumise"] = bool(
            c.get("evaluation_pdf")
            or c.get("evaluation_status") in ["En attente", "Accepté"]
        )

        date_affichage = (
            ligne.get("submitted_to_rh_at")
            or ligne.get("created_at")
        )

        ligne["submittedAtFormatted"] = formater_date_soumission(
            date_affichage
        )

        ligne["rh_status_submessage"] = message_hint_rh(ligne)
        # Documents du candidat : CV, CIN, assurance, convention, demande
        ligne["documents"] = documents_uploades(
            str(ligne["id"])
        )
        resultat.append(ligne)

    return resultat


def chemin_document(candidate_id: str, doc_type: str) -> str | None:
    """Retourne le chemin du PDF s'il existe."""
    filename = f"{candidate_id}_{doc_type}.pdf"
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    if os.path.exists(filepath):
        return filepath
    fallback = os.path.join(
        app.config["UPLOAD_FOLDER"],
        f"{secure_filename(str(candidate_id))}_{doc_type}.pdf",
)
    return fallback if os.path.exists(fallback) else None


def documents_uploades(candidate_id: str) -> dict:
    """État des 5 PDF pour un candidat."""
    resultat = {}
    for doc in DOCUMENTS_REQUIS:
        path = chemin_document(candidate_id, doc)
        resultat[doc] = {
            "uploaded": path is not None,
            "url": f"/api/documents/{candidate_id}/{doc}" if path else None,
        }
    return resultat


def tous_documents_presents(candidate_id: str) -> bool:
    return all(documents_uploades(candidate_id)[d]["uploaded"] for d in DOCUMENTS_REQUIS)


def dossier_soumis_pour_rh(ligne: dict) -> bool:
    """
    Détermine si un dossier doit être visible côté RH.

    Règle principale (si colonnes DB existent) :
    - dossier_submitted = True ou submitted_to_rh_at non nul

    Mode dégradé (si migration Supabase non exécutée) :
    - on considère soumis si les 5 PDF sont présents localement.
    """
    if not ligne:
        return False
    if ligne.get("dossier_submitted") or ligne.get("submitted_to_rh_at"):
        return True
    cid = ligne.get("id")
    if cid is None:
        return False
    try:
        return tous_documents_presents(str(cid))
    except Exception:
        return False


def _enrichir_candidat_charge(ligne: dict) -> dict:
    candidat = enrichir_candidats([ligne])[0]
    candidat["documents"] = documents_uploades(str(candidat["id"]))
    session["candidature_id"] = str(candidat["id"])
    return candidat


def charger_candidature_par_id(candidate_id: str):
    """Charge une candidature par son identifiant."""
    if not supabase or not candidate_id:
        return None
    
    # Appliquer la session Supabase pour l'authentification
    appliquer_session_supabase(supabase)
    
    try:
        reponse = (
            supabase.table(TABLE_APPLICATIONS)
            .select("*")
            .eq("id", candidate_id)
            .limit(1)
            .execute()
        )
        if reponse.data:
            return _enrichir_candidat_charge(reponse.data[0])
    except Exception as exc:
        print(f"[STAGIAIRE] Erreur chargement id={candidate_id}: {exc}")
        # Si erreur JWT, tenter de rafraîchir le token
        if "JWT expired" in str(exc) or "PGRST303" in str(exc):
            print("[STAGIAIRE] Token JWT expiré, tentative de rafraîchissement...")
            from .auth_helpers import rafraichir_token_si_expire
            if rafraichir_token_si_expire(supabase):
                appliquer_session_supabase(supabase)
                try:
                    reponse = (
                        supabase.table(TABLE_APPLICATIONS)
                        .select("*")
                        .eq("id", candidate_id)
                        .limit(1)
                        .execute()
                    )
                    if reponse.data:
                        return _enrichir_candidat_charge(reponse.data[0])
                except Exception as exc2:
                    print(f"[STAGIAIRE] Erreur après rafraîchissement: {exc2}")
    return None


def lier_candidature_au_compte(candidate_id: str):
    """Associe email / user_id à la candidature (si colonnes présentes)."""
    if not supabase or not candidate_id:
        return
    mise_a_jour = {}
    email = (session.get("user_email") or "").strip().lower()
    user_id = session.get("user_id")
    if email:
        mise_a_jour["email"] = email
    if user_id:
        mise_a_jour["user_id"] = user_id
    if not mise_a_jour:
        return
    try:
        supabase_executer_update_eq(
            supabase, TABLE_APPLICATIONS, mise_a_jour, "id", str(candidate_id)
        )
    except Exception as exc:
        print(f"[STAGIAIRE] Lien compte→candidature ({candidate_id}): {exc}")


def charger_candidature_utilisateur():
    """Charge la candidature liée au compte connecté (session, email ou user_id)."""
    if not supabase:
        return None, "Supabase non configuré (.env)"

    cid_session = session.get("candidature_id")
    if cid_session:
        candidat = charger_candidature_par_id(str(cid_session))
        if candidat:
            return candidat, None

    user_id = session.get("user_id")
    email = (session.get("user_email") or "").strip().lower()
    if not user_id and not email:
        return None, None

    try:
        if user_id:
            try:
                reponse = (
                    supabase.table(TABLE_APPLICATIONS)
                    .select("*")
                    .eq("user_id", user_id)
                    .order("created_at", desc=True)
                    .limit(1)
                    .execute()
                )
                if reponse.data:
                    return _enrichir_candidat_charge(reponse.data[0]), None
            except Exception as exc:
                print(f"[STAGIAIRE] Filtre user_id ignoré: {exc}")

        if email:
            try:
                reponse = (
                    supabase.table(TABLE_APPLICATIONS)
                    .select("*")
                    .eq("email", email)
                    .order("created_at", desc=True)
                    .limit(1)
                    .execute()
                )
                if reponse.data:
                    return _enrichir_candidat_charge(reponse.data[0]), None
            except Exception as exc:
                print(f"[STAGIAIRE] Filtre email ignoré: {exc}")

        # Dernier recours : candidature récente avec le même nom d'affichage
        nom_session = (session.get("user_name") or "").strip()
        if nom_session:
            reponse = (
                supabase.table(TABLE_APPLICATIONS)
                .select("*")
                .eq("name", nom_session)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            if reponse.data:
                candidat = _enrichir_candidat_charge(reponse.data[0])
                lier_candidature_au_compte(str(candidat["id"]))
                return candidat, None
    except Exception as exc:
        print(f"[STAGIAIRE] Erreur chargement candidature: {exc}")
        return None, str(exc)

    return None, None


def candidature_appartient_session(candidat: dict) -> bool:
    if not candidat:
        return False
    cid = str(candidat.get("id") or "")
    if cid and str(session.get("candidature_id") or "") == cid:
        return True
    if cid and str(session.get("dossier_soumis_id") or "") == cid:
        return True
    user_id = session.get("user_id")
    email = (session.get("user_email") or "").strip().lower()
    if user_id and str(candidat.get("user_id") or "") == str(user_id):
        return True
    if email and (candidat.get("email") or "").strip().lower() == email:
        return True
    nom_session = (session.get("user_name") or "").strip()
    if nom_session and (candidat.get("name") or "").strip() == nom_session:
        return True
    return False


def candidature_soumise_au_rh(candidat: dict | None) -> bool:
    """Dossier transmis au RH (colonne DB ou session de secours)."""
    if not candidat:
        return False
    if candidat.get("dossier_submitted") or candidat.get("submitted_to_rh_at"):
        return True
    cid = str(candidat.get("id") or "")
    return bool(cid and session.get("dossier_soumis_id") == cid)


def vue_stagiaire_pour(candidat: dict | None) -> str:
    """
    form — pas encore de candidature
    docs — formulaire OK, PDF ou envoi RH en attente
    dashboard — dossier transmis au RH (suivi)
    """
    if not candidat:
        return "form"
    if candidature_soumise_au_rh(candidat):
        return "dashboard"
    if candidat.get("id"):
        return "docs"
    return "form"


EMAIL_SERVICE_AFFECTATION = os.getenv("EMAIL_AFFECTATION", "aff@marsamaroc.ma")


def envoyer_email(dest: str, sujet: str, corps: str, fichier_tag: str = "general"):
    """Envoie un e-mail (fichier local + SMTP si configuré)."""
    if not dest:
        return
    os.makedirs("emails_sent", exist_ok=True)
    filename = f"emails_sent/email_{fichier_tag}_{int(datetime.now().timestamp())}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"To: {dest}\nSubject: {sujet}\n\n{corps}")
    print(f"\n{'=' * 50}")
    print(f"📧 [EMAIL] → {dest}")
    print(f"Sujet: {sujet}")
    print(f"Fichier: {filename}")
    print(f"{'=' * 50}\n")

    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = os.getenv("SMTP_PORT")
    smtp_login = os.getenv("SMTP_LOGIN")
    smtp_password = os.getenv("SMTP_PASSWORD")
    mail_from = os.getenv("MAIL_FROM")

    if smtp_server and smtp_port and smtp_login and smtp_password and mail_from:
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.header import Header

            msg = MIMEText(corps, "plain", "utf-8")
            msg["Subject"] = Header(sujet, "utf-8")
            msg["From"] = mail_from
            msg["To"] = dest

            port = int(smtp_port)
            if port == 465:
                server = smtplib.SMTP_SSL(smtp_server, port, timeout=5)
            else:
                server = smtplib.SMTP(smtp_server, port, timeout=5)
                server.starttls()

            server.login(smtp_login, smtp_password)
            server.sendmail(mail_from, [dest], msg.as_string())
            server.quit()
            print(f"[SMTP] Email envoyé avec succès à {dest}")
        except Exception as e:
            print(f"[SMTP] Échec de l'envoi de l'email : {e}")


def envoyer_email_stagiaire(candidate_id: str, email_dest: str, sujet: str, corps: str):
    envoyer_email(email_dest, sujet, corps, fichier_tag=str(candidate_id))
    
def notifier_nouveau_document_email(
    stagiaire: dict,
    nom_document: str
):
    """
    Envoie un email réel au stagiaire lorsqu'un nouveau
    document devient disponible dans son espace.
    """

    if not stagiaire:
        return

    candidate_id = str(
        stagiaire.get("id") or ""
    )

    candidate_email = (
        stagiaire.get("email")
        or ""
    ).strip().lower()

    nom_stagiaire = (
        stagiaire.get("name")
        or "Stagiaire"
    )

    if not candidate_email:
        print(
            f"[EMAIL DOCUMENT] Aucun email pour {candidate_id}"
        )
        return

    app_url = (
        os.getenv(
            "APP_URL",
            "http://127.0.0.1:5000"
        )
        .rstrip("/")
    )

    lien_espace = f"{app_url}/stagiaire"

    sujet = (
        f"[Marsa Maroc] "
        f"{nom_document} disponible"
    )

    corps = f"""Bonjour {nom_stagiaire},

Un nouveau document vient d'être ajouté à votre espace stagiaire Marsa Maroc.

Document :
{nom_document}

Vous pouvez maintenant le consulter et le télécharger depuis votre espace stagiaire :

{lien_espace}

Cordialement,
Direction du Capital Humain
Marsa Maroc
"""

    envoyer_email_stagiaire(
        candidate_id,
        candidate_email,
        sujet,
        corps
    )


def ouvrir_mail_outlook(
    email_rh,
    destinataire,
    sujet,
    corps,
    fichier_path
):
    if pythoncom is None or win32com is None:
        raise RuntimeError(
            "L'envoi Outlook nécessite Windows, Outlook installé et pywin32."
        )

    fichier_path = os.path.abspath(fichier_path)

    if not os.path.exists(fichier_path):
        raise RuntimeError(
            f"Fichier introuvable : {fichier_path}"
        )

    pythoncom.CoInitialize()

    try:
        outlook = win32com.client.Dispatch(
            "Outlook.Application"
        )

        namespace = outlook.Session

        email_rh = (
            email_rh or ""
        ).strip().lower()

        compte_rh = None

        for account in namespace.Accounts:

            try:
                smtp = (
                    account.SmtpAddress or ""
                ).strip().lower()

                if smtp == email_rh:
                    compte_rh = account
                    break

            except Exception:
                continue

        if not compte_rh:
            raise RuntimeError(
                "Le compte Outlook correspondant au RH "
                f"connecté est introuvable : {email_rh}"
            )

        mail = outlook.CreateItem(0)

        mail.SendUsingAccount = compte_rh
        mail.To = destinataire
        mail.Subject = sujet
        mail.Body = corps

        mail.Attachments.Add(
            fichier_path
        )

        # Ouvre Outlook sans envoyer automatiquement
        mail.Display()

    finally:
        pythoncom.CoUninitialize()


        
@app.post("/api/rh/documents/validate")
@login_required("rh")
def rh_validate_document():

    if not supabase:
        return jsonify(
            success=False,
            error="Supabase non configuré"
        ), 500

    data = request.get_json(silent=True) or {}

    candidate_id = str(
        data.get("candidate_id") or ""
    ).strip()

    doc_type = (
        data.get("doc_type") or ""
    ).strip().lower()

    if not candidate_id:
        return jsonify(
            success=False,
            error="Candidat manquant."
        ), 400

    if doc_type not in DOCUMENTS_REQUIS:
        return jsonify(
            success=False,
            error="Type de document invalide."
        ), 400

    # Vérifier que le PDF existe réellement
    fichier_path = chemin_document(
        candidate_id,
        doc_type
    )

    if not fichier_path:
        return jsonify(
            success=False,
            error="Document introuvable."
        ), 404

    try:

        response = (
            supabase
            .table(TABLE_APPLICATIONS)
            .select("id,validated_documents")
            .eq("id", candidate_id)
            .single()
            .execute()
        )

        candidat = response.data

        if not candidat:
            return jsonify(
                success=False,
                error="Stagiaire introuvable."
            ), 404

        validated_documents = (
            candidat.get("validated_documents")
            or {}
        )

        if not isinstance(validated_documents, dict):
            validated_documents = {}

        validated_documents[doc_type] = True

        (
            supabase
            .table(TABLE_APPLICATIONS)
            .update({
                "validated_documents":
                    validated_documents
            })
            .eq("id", candidate_id)
            .execute()
        )

        return jsonify(
            success=True,
            message=(
                f"{DOC_LABELS.get(doc_type, doc_type)} "
                "validé avec succès."
            ),
            outlook_available=True
        )

    except Exception as exc:

        print(
            f"[RH VALIDATE DOCUMENT] {exc}"
        )

        return jsonify(
            success=False,
            error=str(exc)
        ), 500
        
   
@app.post("/api/rh/outlook/<candidate_id>/<doc_type>")
@login_required("rh")
def rh_outlook_document(candidate_id, doc_type):

    TYPES_OUTLOOK = {

        "fiche_accueil": {
            "column": "fiche_accueil_pdf",
        },

        "decision_stage": {
            "column": "decision_pdf",
        },

        "evaluation": {
            "column": "evaluation_pdf",
        },

        "attestation": {
            "column": "attestation_pdf",
        },
    }

    if doc_type not in TYPES_OUTLOOK:
        return jsonify(
            success=False,
            error="Type de document Outlook invalide."
        ), 400

    try:

        # ==============================
        # STAGIAIRE
        # ==============================

        response = (
            supabase
            .table(TABLE_APPLICATIONS)
            .select(
                "id,name,email,"
                "fiche_accueil_pdf,"
                "decision_pdf,"
                "evaluation_pdf,"
                "evaluation_status,"
                "attestation_pdf"
            )
            .eq("id", candidate_id)
            .single()
            .execute()
        )

        candidat = response.data

        if not candidat:
            return jsonify(
                success=False,
                error="Stagiaire introuvable."
            ), 404


        # ==============================
        # CAS FICHE D'APPRÉCIATION
        # ==============================

        if (
            doc_type == "evaluation"
            and candidat.get("evaluation_status") != "Accepté"
        ):
            return jsonify(
                success=False,
                error=(
                    "La fiche d'appréciation doit être "
                    "validée par le RH avant l'envoi."
                )
            ), 403


        # ==============================
        # NOM DU PDF
        # ==============================

        column_name = (
            TYPES_OUTLOOK[doc_type]["column"]
        )

        filename = candidat.get(
            column_name
        )

        if not filename:
            return jsonify(
                success=False,
                error="Le document n'est pas disponible."
            ), 404


        # Sécuriser le nom du fichier
        filename = os.path.basename(
            filename
        )


        # ==============================
        # CHERCHER LE PDF
        # ==============================

        possible_paths = [

            os.path.join(
                app.config["GENERATED_PDFS_FOLDER"],
                filename
            ),

            os.path.join(
                app.config["UPLOAD_FOLDER"],
                filename
            ),

            os.path.join(
                app.config["PDF_TEMPLATES_FOLDER"],
                filename
            ),
        ]

        fichier_path = None

        for path in possible_paths:

            if os.path.exists(path):
                fichier_path = path
                break


        if not fichier_path:
            return jsonify(
                success=False,
                error=f"PDF introuvable : {filename}"
            ), 404


        # ==============================
        # EMAIL STAGIAIRE
        # ==============================

        email_stagiaire = (
            candidat.get("email")
            or ""
        ).strip()

        if not email_stagiaire:
            return jsonify(
                success=False,
                error="Le stagiaire n'a pas d'adresse email."
            ), 400


        # ==============================
        # RH CONNECTÉ
        # ==============================

        email_rh = (
            session.get("user_email")
            or ""
        ).strip()

        if not email_rh:
            return jsonify(
                success=False,
                error="Email du RH connecté introuvable."
            ), 400


        # ==============================
        # TEXTE DYNAMIQUE
        # ==============================

        template = (
            OUTLOOK_DOCUMENT_MESSAGES.get(
                doc_type
            )
        )

        nom_stagiaire = (
            candidat.get("name")
            or "Stagiaire"
        )

        sujet = template["subject"]

        corps = template["body"].format(
            name=nom_stagiaire
        )


        # ==============================
        # OUTLOOK
        # ==============================

        ouvrir_mail_outlook(
            email_rh=email_rh,
            destinataire=email_stagiaire,
            sujet=sujet,
            corps=corps,
            fichier_path=fichier_path,
        )

        return jsonify(
            success=True,
            message="Email préparé dans Outlook."
        )


    except Exception as exc:

        print(
            "[OUTLOOK]",
            exc
        )

        return jsonify(
            success=False,
            error=str(exc)
        ), 500     


def ajouter_notification(
    candidat: dict,
    texte: str,
    titre: str = "",
    url: str = "",
    type_notification: str = "",
) -> list:

    import datetime as dt

    notifications = candidat.get("notifications") or []

    if not isinstance(notifications, list):
        notifications = []

    # Évite d'avoir 10 fois la même notification
    # si le RH modifie/régénère le même document.
    if type_notification:

        notifications = [
            notif
            for notif in notifications
            if notif.get("type") != type_notification
        ]

    notifications.append({
        "id": f"notif_{int(dt.datetime.now().timestamp())}",
        "title": titre,
        "text": texte,
        "date": dt.datetime.now().isoformat(),
        "read": False,
        "url": url,
        "type": type_notification,
    })

    return notifications


def notifier_document_officiel(
    candidate_id: str,
    document_type: str
):

    if not supabase:
        return False

    documents = {

        "fiche_accueil": {
            "column": "fiche_accueil_pdf",
            "title": "Fiche d'accueil disponible",
            "text": (
                "Votre fiche d'accueil de stage "
                "est désormais disponible."
            ),
        },

        "decision_stage": {
            "column": "decision_pdf",
            "title": "Décision de stage disponible",
            "text": (
                "Votre décision de stage officielle "
                "est désormais disponible."
            ),
        },

        "evaluation": {
            "column": "evaluation_pdf",
            "title": "Fiche d'appréciation validée",
            "text": (
                "Votre fiche d'appréciation de stage "
                "a été validée par le service RH."
            ),
        },

        "attestation": {
            "column": "attestation_pdf",
            "title": "Attestation de stage disponible",
            "text": (
                "Votre attestation de stage officielle "
                "est désormais disponible."
            ),
        },
    }


    config = documents.get(
        document_type
    )

    if not config:
        return False


    try:

        response = (
            supabase
            .table(TABLE_APPLICATIONS)
            .select(
                "id,"
                "notifications,"
                "fiche_accueil_pdf,"
                "decision_pdf,"
                "evaluation_pdf,"
                "attestation_pdf"
            )
            .eq(
                "id",
                candidate_id
            )
            .single()
            .execute()
        )


        candidat = response.data

        if not candidat:
            return False


        filename = (
            candidat.get(
                config["column"]
            )
            or ""
        ).strip()


        if not filename:

            print(
                "[NOTIFICATION DOCUMENT] "
                f"{document_type} sans PDF"
            )

            return False


        filename = os.path.basename(
            filename
        )


        # URL générique déjà disponible
        pdf_url = (
            f"/pdf/{filename}"
        )


        notifications = ajouter_notification(

            candidat,

            texte=config["text"],

            titre=config["title"],

            url=pdf_url,

            type_notification=document_type,
        )


        (
            supabase
            .table(TABLE_APPLICATIONS)
            .update({
                "notifications":
                    notifications
            })
            .eq(
                "id",
                candidate_id
            )
            .execute()
        )


        print(
            "[NOTIFICATION DOCUMENT] "
            f"{document_type} -> "
            f"{candidate_id}"
        )

        return True


    except Exception as exc:

        print(
            "[NOTIFICATION DOCUMENT ERROR]",
            exc
        )

        return False



def charger_candidats():
    """Charge toutes les candidatures pour le tableau RH."""
    candidats, _ = charger_candidats_avec_erreur()
    return candidats


def charger_candidats_avec_erreur():
    if not supabase:
        return [], "Supabase non configuré (.env)"

    # Appliquer la session Supabase pour l'authentification
    appliquer_session_supabase(supabase)

    try:
        reponse = (
            supabase.table(TABLE_APPLICATIONS)
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
        if reponse.data is not None:
            return enrichir_candidats(reponse.data), None
    except Exception as exc:
        print(f"[RH] Erreur chargement (created_at): {exc}")
        # Si erreur JWT, tenter de rafraîchir le token
        if "JWT expired" in str(exc) or "PGRST303" in str(exc):
            print("[RH] Token JWT expiré, tentative de rafraîchissement...")
            from .auth_helpers import rafraichir_token_si_expire
            if rafraichir_token_si_expire(supabase):
                appliquer_session_supabase(supabase)
                try:
                    reponse = (
                        supabase.table(TABLE_APPLICATIONS)
                        .select("*")
                        .order("created_at", desc=True)
                        .execute()
                    )
                    if reponse.data is not None:
                        return enrichir_candidats(reponse.data), None
                except Exception as exc2:
                    print(f"[RH] Erreur après rafraîchissement: {exc2}")

    try:
        reponse = (
            supabase.table(TABLE_APPLICATIONS)
            .select("*")
            .order("id", desc=True)
            .execute()
        )
        return enrichir_candidats(reponse.data or []), None
    except Exception as exc:
        print(f"[RH] Erreur chargement: {exc}")
        try:
            reponse = (
                supabase.table(TABLE_APPLICATIONS)
                .select("*")
                .order("id", desc=True)
                .execute()
            )
            return enrichir_candidats(reponse.data or []), None
        except Exception as exc2:
            print(f"[RH] Erreur chargement (fallback): {exc2}")
            return [], str(exc2)


def inserer_candidature(corps: dict):
    """Insère une candidature dans la table applications."""
    donnees = donnees_pour_insertion(corps)
    donnees["created_at"] = datetime.now(timezone.utc).isoformat()
    return supabase_executer_insert(supabase, TABLE_APPLICATIONS, donnees)


def message_erreur_supabase(exc: Exception) -> str:
    """Message utilisateur en français pour les erreurs Supabase courantes."""
    col = colonne_manquante_dans_erreur(exc)
    if col:
        return (
            f"Colonne « {col} » absente dans Supabase. "
            "Exécutez le fichier supabase/migrations/supabase_stagiaire_dashboard.sql dans le SQL Editor, "
            "puis réessayez."
        )
    return str(exc)




# New function: generate PDF by overlaying text onto the original template using pdfrw.
def generer_fiche_accueil_pdf_filled(stagiaire: dict, affectation: dict) -> str:
    """
    Generates a filled PDF based on the original template, preserving exact layout.
    Uses reportlab to build a transparent text layer and pdfrw to merge it with the template.
    Returns the filename of the generated PDF.
    """
    import os
    import re
    from datetime import datetime
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import HexColor
    from pdfrw import PdfReader, PdfWriter, PageMerge

    try:
        # Ensure output directory exists
        output_dir = app.config['GENERATED_PDFS_FOLDER']
        os.makedirs(output_dir, exist_ok=True)

        # Path to the original PDF template (absolute for safety)
        base_dir = BASE_DIR
        template_path = os.path.join(base_dir, 'pdf', 'FICHE ACCUEIL DES STAGIAIRES DE PASSAGE.pdf')
        if not os.path.exists(template_path):
            print(f"[PDF] Template not found: {template_path}")
            return None

        # 1. Normalize data
        candidat = normaliser_candidat(stagiaire)

        # Name splitting
        full_name = candidat.get('name', '').strip()
        parts = full_name.split(None, 1)
        prenom = parts[0] if len(parts) > 0 else ''
        nom = parts[1] if len(parts) > 1 else ''
        if not nom:
            nom = (stagiaire.get('last_name') or stagiaire.get('nom') or '').strip()
            prenom = (stagiaire.get('first_name') or stagiaire.get('prenom') or '').strip()
        
        phone = candidat.get('phone', '') or ''
        school = candidat.get('school', '') or ''
        specialty = candidat.get('specialty', '') or ''
        level = candidat.get('level', '') or ''
        type_stage = candidat.get('type', '') or ''
        
        # Extract department, mentor and project
        department = candidat.get('department', '') or affectation.get('department', '') or ''
        mentor = affectation.get('mentor', '') or candidat.get('mentor', '') or ''
        project = affectation.get('project', '') or candidat.get('project', '') or ''
        
        # Extract dates from period
        period = candidat.get('period', '') or ''
        start_date = ''
        end_date = ''
        if ' - ' in period:
            p_parts = period.split(' - ')
            start_date = p_parts[0].strip()
            end_date = p_parts[1].strip()
        elif '-' in period:
            p_parts = period.split('-')
            start_date = p_parts[0].strip()
            end_date = p_parts[1].strip()
        else:
            start_date = period

        # 2. Generate the transparent overlay PDF using reportlab
        temp_overlay_filename = f"temp_overlay_{candidat.get('id', 'temp')}.pdf"
        temp_overlay_path = os.path.join(output_dir, temp_overlay_filename)
        
        # Dimensions of the template page are 595.32 x 841.92
        c = canvas.Canvas(temp_overlay_path, pagesize=(595.32, 841.92))
        
        # Set premium brand color matching Marsa Maroc
        brand_color = HexColor('#001a4d')
        c.setFillColor(brand_color)
        
        # Helper to draw grid characters (Nom, Prenom, Telephone)
        def draw_grid_text(c, txt, start_x, pitch, y, font_size=10, max_chars=17):
            txt = ''.join(ch for ch in str(txt).strip().upper() if ch.isalnum() or ch == ' ')
            txt = txt[:max_chars]
            c.setFont('Courier-Bold', font_size)
            c.setFillColor(brand_color)
            for idx, char in enumerate(txt):
                x_center = start_x + (idx * pitch) + (pitch / 2.0)
                # Center character inside the box
                c.drawCentredString(x_center, y, char)

        # Helper to normalize and parse dates into 8-digits (DDMMYYYY)
        def get_date_digits(date_str):
            clean_digits = ''.join(ch for ch in str(date_str) if ch.isdigit())
            if len(clean_digits) == 8:
                # Check if it was parsed as YYYY-MM-DD
                if '-' in str(date_str) and str(date_str).strip().startswith('20'):
                    return clean_digits[6:8] + clean_digits[4:6] + clean_digits[0:4]
                return clean_digits
            # Try splitting standard separators
            parts = re.split(r'[-/.]', str(date_str))
            if len(parts) == 3:
                d = parts[0].strip().zfill(2)
                m = parts[1].strip().zfill(2)
                y = parts[2].strip()
                if len(y) == 2:
                    y = "20" + y
                return f"{d}{m}{y}"
            return clean_digits[:8].ljust(8, ' ')

        # Helper to draw date digits into specific box centers
        def draw_date_digits(c, date_str, xs, y, font_size=10):
            digits = get_date_digits(date_str)
            digits = digits.ljust(8, ' ')[:8]
            c.setFont('Courier-Bold', font_size)
            c.setFillColor(brand_color)
            for idx, char in enumerate(digits):
                x_center = xs[idx]
                c.drawCentredString(x_center, y, char)

        # Helper to draw standard text centered vertically with auto-shrink
        def draw_bounded_string(c, txt, x, y, max_width, initial_size=10, font_name='Helvetica-Bold'):
            txt = str(txt).strip()
            size = initial_size
            c.setFont(font_name, size)
            c.setFillColor(brand_color)
            # Loop to decrease size if text is too wide
            while size > 5.5 and c.stringWidth(txt, font_name, size) > max_width:
                size -= 0.5
            c.setFont(font_name, size)
            c.drawString(x, y, txt)

        # Helper to draw a cross (X) in a checkbox
        def draw_checkbox_cross(c, x, y, size=10):
            c.setFillColor(brand_color)
            c.setStrokeColor(brand_color)
            c.setLineWidth(2.0)
            # Draw X centered at the position
            offset = size / 2
            c.line(x - offset, y - offset, x + offset, y + offset)
            c.line(x + offset, y - offset, x - offset, y + offset)
            print(f"[CHECKBOX] Drew cross at X={x}, Y={y}, size={size}")

        # Draw grid text fields
        # Nom Y-baseline: 660.39, Prenom Y-baseline: 628.04, Telephone Y-baseline: 595.94
        # Grid start X: 174.50, Pitch: 23.04
        draw_grid_text(c, nom, start_x=174.50, pitch=23.04, y=660.39, font_size=10, max_chars=17)
        draw_grid_text(c, prenom, start_x=174.50, pitch=23.04, y=628.04, font_size=10, max_chars=17)
        draw_grid_text(c, phone, start_x=174.50, pitch=23.04, y=595.94, font_size=10, max_chars=17)

        # Draw date digits
        start_date_xs = [209.09, 220.91, 251.09, 265.43, 294.17, 308.64, 323.11, 337.51]
        end_date_xs = [380.71, 395.11, 423.97, 438.39, 467.14, 481.54, 496.00, 510.46]
        draw_date_digits(c, start_date, start_date_xs, y=345.33, font_size=10)
        draw_date_digits(c, end_date, end_date_xs, y=345.33, font_size=10)

        # Draw regular text fields (with auto-shrinkage and vertical centering)
        # Etablissement: baseline 565.57, using 567.0, X starts after label at 135
        draw_bounded_string(c, school.upper(), x=135, y=567.0, max_width=390, initial_size=11.0)
        
        # Specialty & Level: baseline 541.57, using 543.0, X starts after label at 140
        draw_bounded_string(c, f"{specialty} - {level}".upper(), x=140, y=543.0, max_width=380, initial_size=11.0)
        
                # =====================================================
        # TYPE DE STAGE
        # Coche automatiquement la case choisie par le stagiaire
        # =====================================================

        type_lower = (type_stage or "").strip().lower()

        print(
            f"[CHECKBOX] Type stage reçu : '{type_stage}', "
            f"normalisé : '{type_lower}'"
        )

        # Centres exacts des trois cases du PDF
        PASSAGE_BOX = (242.33, 511.27)
        ALTERNE_BOX = (344.41, 511.27)
        PFE_BOX = (505.84, 511.27)

        target_center = None


        # ----------------------------
        # PASSAGE
        # ----------------------------
        if type_lower == "passage":
            target_center = PASSAGE_BOX


        # ----------------------------
        # ALTERNE / ALTERNÉ
        # ----------------------------
        elif type_lower == "alterne" or "altern" in type_lower:
            target_center = ALTERNE_BOX


        # ----------------------------
        # PROJET FIN ETUDE
        # ----------------------------
        elif (
            type_lower == "projet fin etude"
            or "projet fin" in type_lower
            or "fin etude" in type_lower
            or "pfe" in type_lower
        ):
            target_center = PFE_BOX


        # ----------------------------
        # Dessiner la croix
        # ----------------------------
        if target_center:

            target_center_x, target_center_y = target_center

            print(
                f"[CHECKBOX] Case cochée : "
                f"X={target_center_x}, Y={target_center_y}"
            )

            draw_checkbox_cross(
                c,
                target_center_x,
                target_center_y,
                size=8
            )

        else:

            print(
                f"[CHECKBOX] Type de stage non reconnu : "
                f"'{type_stage}'"
            )
        
        # Division d'affectation: baseline 399.47, using 401.0, X starts after label at 172
        draw_bounded_string(c, department.upper(), x=172, y=401.0, max_width=350, initial_size=11.0)
        
        # Encadrant: baseline 379.19, using 380.7, X starts after label at 113
        draw_bounded_string(c, mentor.upper(), x=113, y=380.7, max_width=410, initial_size=11.0)
        
        # Thème de stage: baseline 358.79, using 360.3, X starts after label at 142
        draw_bounded_string(c, project.upper(), x=142, y=360.3, max_width=380, initial_size=11.0)

        # Save overlay
        c.save()

        # 3. Use pdfrw to merge the overlay onto the template page
        template_pdf = PdfReader(template_path)
        overlay_pdf = PdfReader(temp_overlay_path)
        
        PageMerge(template_pdf.pages[0]).add(overlay_pdf.pages[0]).render()
        
        # 4. Write final output PDF
        pdf_filename = f"fiche_accueil_{candidat.get('name', 'stagiaire').replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        pdf_path = os.path.join(output_dir, pdf_filename)
        
        PdfWriter(pdf_path, trailer=template_pdf).write()
        
        # Clean up temporary overlay file
        try:
            os.remove(temp_overlay_path)
        except Exception:
            pass
            
        print(f"[PDF] Generated successfully: {pdf_filename}")
        return pdf_filename
        
    except Exception as e:
        print(f"[PDF] Generation error: {e}")
        import traceback
        traceback.print_exc()
        return None
    
# Point important : si on régénère la décision du même stagiaire, on réutilisera son ancien numéro. On ne demandera un nouveau numéro que pour une nouvelle décision.

def get_next_decision_stage_number():
    if not supabase:
        raise RuntimeError("Supabase non configuré")

    result = (
        supabase
        .rpc("next_decision_stage_number")
        .execute()
    )

    value = result.data

    if isinstance(value, list):
        if not value:
            raise RuntimeError(
                "Impossible de récupérer le numéro de décision"
            )

        value = value[0]

        if isinstance(value, dict):
            value = next(iter(value.values()))

    return int(value)

def generer_decision_stage_pdf(
    stagiaire: dict,
    affectation: dict,
    decision_info: dict
) -> str:

    import os
    import re
    import base64

    from io import BytesIO
    from datetime import datetime,timezone

    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import black, white
    from reportlab.lib.utils import ImageReader

    from pdfrw import (
        PdfReader,
        PdfWriter,
        PageMerge
    )

    try:

        # =====================================================
        # DOSSIERS
        # =====================================================

        output_dir = app.config["GENERATED_PDFS_FOLDER"]

        os.makedirs(
            output_dir,
            exist_ok=True
        )

        base_dir = os.path.dirname(
            os.path.abspath(__file__)
        )

        template_path = os.path.join(
            app.config["PDF_TEMPLATES_FOLDER"],
            "Decision de stage.pdf"
        )

        if not os.path.exists(template_path):
            print(
                f"[DECISION] Modèle introuvable : "
                f"{template_path}"
            )
            return None


        # =====================================================
        # STAGIAIRE
        # =====================================================

        candidat = normaliser_candidat(
            stagiaire
        )

        prenom = (
            stagiaire.get("first_name")
            or stagiaire.get("prenom")
            or ""
        ).strip()

        nom = (
            stagiaire.get("last_name")
            or stagiaire.get("nom")
            or ""
        ).strip()


        # Fallback si first_name / last_name absents
        if not prenom or not nom:

            full_name = (
                candidat.get("name")
                or ""
            ).strip()

            parties = full_name.split(
                None,
                1
            )

            if not prenom and parties:
                prenom = parties[0]

            if not nom and len(parties) > 1:
                nom = parties[1]


        # Exemple :
        # Monsieur LARAQUI Jad

        nom_decision = (
            f"Monsieur {nom.upper()} "
            f"{prenom.capitalize()}"
        ).strip()
        nom_decision = (
            decision_info.get("nom_stagiaire")
            or nom_decision
        ).strip()


        # =====================================================
        # PÉRIODE
        # =====================================================

        period = (
            candidat.get("period")
            or ""
        ).strip()

        start_date = ""
        end_date = ""

        if " - " in period:

            parts = period.split(
                " - ",
                1
            )

            start_date = parts[0].strip()
            end_date = parts[1].strip()


        def date_fr(value):

            if not value:
                return ""

            value = str(value).strip()

            try:

                dt = datetime.strptime(
                    value,
                    "%Y-%m-%d"
                )

                return dt.strftime(
                    "%d/%m/%Y"
                )

            except Exception:
                return value


        date_debut = date_fr(
            start_date
        )
        
        date_debut = (
            decision_info.get("date_debut")
            or date_debut
        ).strip()


        # =====================================================
        # DURÉE DU STAGE
        # =====================================================

        # Tu as déjà cette fonction dans ton projet.
        # Elle donne par exemple :
        # d'un mois
        # de deux mois
        # de trois mois

        duree_stage = duree_stage_en_mois(period).strip()

        # =====================================================
        # AFFECTATION
        # =====================================================

        department = (
            affectation.get("department")
            or candidat.get("department")
            or ""
        ).strip()


        # Pour ton exemple DSI
        division_mapping = {
            "DSI - Direction Systèmes d'Information":
                "Division Systèmes d'Information"
        }

        division = division_mapping.get(
            department,
            department
        )
        
        division = (
            decision_info.get("division")
            or division
        ).strip()


        responsable = (
            affectation.get("mentor_function")
            or candidat.get("mentor_function")
            or ""
        ).strip()
        
        responsable = (
            decision_info.get("responsable")
            or responsable
        ).strip()


        # =====================================================
        # INFORMATIONS DÉCISION
        # =====================================================

        numero = str(
            decision_info.get("numero")
            or ""
        )

        reference = (
            decision_info.get("reference")
            or ""
        )

        date_decision = (
            decision_info.get("date_decision")
            or ""
        )

        direction = (
            decision_info.get("direction")
            or ""
        )

        pole = (
            decision_info.get("pole")
            or ""
        )

        entite_header = (
            decision_info.get("entite_header")
            or ""
        )


        # =====================================================
        # OVERLAY
        # =====================================================

        candidate_id = (
            candidat.get("id")
            or stagiaire.get("id")
            or "temp"
        )

        temp_filename = (
            f"temp_decision_"
            f"{candidate_id}.pdf"
        )

        temp_path = os.path.join(
            output_dir,
            temp_filename
        )


        PAGE_W = 612
        PAGE_H = 792

        c = canvas.Canvas(
            temp_path,
            pagesize=(
                PAGE_W,
                PAGE_H
            )
        )


        # =====================================================
        # HELPER POUR LE TEXTE
        # =====================================================

        def draw_fit(
            text,
            x,
            y,
            max_width,
            size=9,
            font="Times-Bold"
        ):

            text = str(
                text or ""
            ).strip()

            font_size = size

            while (
                font_size > 5
                and
                c.stringWidth(
                    text,
                    font,
                    font_size
                ) > max_width
            ):
                font_size -= 0.25

            # Texte dynamique légèrement plus gras
            c.setFillColor(black)
            c.setStrokeColor(black)
            c.setLineWidth(0.13)

            txt = c.beginText()
            txt.setTextOrigin(x, y)
            txt.setFont(font, font_size)

            

            txt.textOut(text)
            c.drawText(txt)

             # =====================================================
        # EN-TÊTE SUPÉRIEUR
        # =====================================================

        # Complète :
        # "Direction de l'Exploitation ..."
        draw_fit(
            entite_header,
            411,
            747.5,
            150,
            6.3,
            "Helvetica"
        )


        # =====================================================
        # LIGNE DECISION
        # DECISION N° [173] /DAF/DRH/DEPC-[TCR/2026].
        # =====================================================
        # Numéro et référence : même ligne et même taille que le texte du modèle
        draw_fit(
            numero,
            140,
            669.5,
            20,
            10,
            "Times-Bold"
        )

        draw_fit(
            reference,
            250,
            669.5,
            50,
            10,
            "Times-Bold"
        )


        # =====================================================
        # DATE EN HAUT A DROITE
        # Casablanca - Maroc     09/09/2026
        # =====================================================

       # Date de décision : juste après "Casablanca", sur la même ligne
        draw_fit(
            date_decision,
            490,
            681,
            55,
            10,
            "Times-Bold"
        )


        # =====================================================
        # LE DIRECTEUR DES RESSOURCES HUMAINES AU ...
        # =====================================================

        # Blanc entre "au" et "-"
        draw_fit(
            direction,
            308,
            628.5,
            120,
            10.5,
            "Times-Bold"
        )

        # Blanc entre "-" et ":"
        draw_fit(
            pole,
            415,
            628.5,
            150,
            10.5,
            "Times-Bold"
        )


        # =====================================================
        # VU LA DEMANDE DE STAGE DE ...
        # =====================================================

        draw_fit(
            nom_decision,
            214,
            601,
            145,
            10,
            "Times-Bold"
        )


        # =====================================================
        # VU L'ACCORD PREALABLE DE STAGE DU ...
        # =====================================================

        draw_fit(
            responsable,
            256,
            572.5,
            200,
            10,
            "Times-Bold"
        )


        # =====================================================
        # ARTICLE 1 - NOM DU STAGIAIRE
        #
        # [Monsieur ...] est autorisé à effectuer...
        # =====================================================

        draw_fit(
            nom_decision,
            72,
            470.5,
            138,
            10,
            "Times-Bold"
        )


        # =====================================================
        # ARTICLE 1 - DUREE
        #
        # stage [de six mois] à la...
        # =====================================================

        # Effacer le "d'" déjà présent dans le modèle.
        c.setFillColor(white)

        c.rect(
            363,
            466,
            55,
            15,
            fill=1,
            stroke=0
        )

        draw_fit(
            duree_stage,
            367.5,
            471,
            66,
            10,
            "Times-Bold"
        )


        # =====================================================
        # ARTICLE 1 - DIVISION
        # =====================================================

        mots = division.split()

        ligne1 = ""
        ligne2 = ""

        for mot in mots:

            tentative = (
                f"{ligne1} {mot}"
            ).strip()

            largeur = c.stringWidth(
                tentative,
                "Times-Bold",
                8
            )

            if largeur <= 98:
                ligne1 = tentative

            else:
                ligne2 = (
                    f"{ligne2} {mot}"
                ).strip()


        # Première partie après "à la"
            draw_fit(
                ligne1,
                443.5,
                471.5,
                110,
                9.25,
                "Times-Bold"
            )

        # Suite éventuelle au début de la deuxième ligne
        if ligne2:
            draw_fit(
                ligne2,
                74,
                456.5,
                85,
                9.25,
                "Times-Bold"
            )


        # =====================================================
        # DATE DEBUT
        #
        # et ce à compter du [01/09/2026].
        # =====================================================

        # Une seule date de début, alignée après "et ce à compter du"
        draw_fit(
            date_debut,
            247,
            457.5,
            65,
            9.5,
            "Times-Bold"
        )


       


        # =====================================================
        # SIGNATURE RH
        # =====================================================

        signature = (
            decision_info.get("signature")
            or ""
        )

        if signature:

            try:

                if "," in signature:
                    signature = signature.split(
                        ",",
                        1
                    )[1]

                image_bytes = base64.b64decode(
                    signature
                )

                image = ImageReader(
                    BytesIO(
                        image_bytes
                    )
                )

                c.drawImage(
                    image,
                    333,
                    158,
                    width=79,
                    height=45,
                    preserveAspectRatio=True,
                    mask="auto"
                )

            except Exception as exc:

                print(
                    "[DECISION] Signature error:",
                    exc
                )


        # =====================================================
        # SAUVEGARDE OVERLAY
        # =====================================================

        c.save()


        # =====================================================
        # FUSION AVEC LE MODÈLE
        # =====================================================

        template_pdf = PdfReader(
            template_path
        )

        overlay_pdf = PdfReader(
            temp_path
        )

        PageMerge(
            template_pdf.pages[0]
        ).add(
            overlay_pdf.pages[0]
        ).render()


        # =====================================================
        # NOM PDF FINAL
        # =====================================================

        safe_name = re.sub(
            r"[^A-Za-z0-9_-]",
            "_",
            f"{nom}_{prenom}"
        )

        pdf_filename = (
            f"decision_stage_"
            f"{safe_name}_"
            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            f".pdf"
        )

        pdf_path = os.path.join(
            output_dir,
            pdf_filename
        )

        PdfWriter(
            pdf_path,
            trailer=template_pdf
        ).write()


        # Nettoyer overlay temporaire
        try:
            os.remove(
                temp_path
            )
        except Exception:
            pass


        print(
            f"[DECISION] Générée : "
            f"{pdf_filename}"
        )

        return pdf_filename


    except Exception as exc:

        print(
            "[DECISION] Erreur :",
            exc
        )

        import traceback
        traceback.print_exc()

        return None
    
 
DECISION_AFFECTATION_MAP = {

    "DSI - Direction Systèmes d'Information": {
        "direction": "Port de Casablanca",
        "pole": "Trafics Conteneur et Roulier",
        "entite_header": (
            "au Port de Casablanca "
            "Trafic Conteneur & Roulier"
        ),
        "division": "Division Systèmes d'Information",
    },

    "DCH - Capital Humain": {
        "direction": "Port de Casablanca",
        "pole": "Capital Humain",
        "entite_header": (
            "au Port de Casablanca "
            "Capital Humain"
        ),
        "division": "Division Capital Humain",
    },

    "DAF - Finance & Contrôle": {
        "direction": "Port de Casablanca",
        "pole": "Finance & Contrôle",
        "entite_header": (
            "au Port de Casablanca "
            "Finance & Contrôle"
        ),
        "division": "Division Finance & Contrôle",
    },

    "DOF - Opérations Portuaires": {
        "direction": "Port de Casablanca",
        "pole": "Opérations Portuaires",
        "entite_header": (
            "au Port de Casablanca "
            "Opérations Portuaires"
        ),
        "division": "Division Opérations Portuaires",
    },
}   
    
def construire_decision_auto(stagiaire: dict) -> dict:
    """
    Construit automatiquement les champs de la décision
    à partir :
    - du formulaire stagiaire
    - de la direction choisie par RH
    - de l'affectation
    """

    import re
    

    candidat = normaliser_candidat(stagiaire)

    # =====================================================
    # 1. NOM / PRENOM - FORMULAIRE STAGIAIRE
    # =====================================================

    prenom = (
        stagiaire.get("first_name")
        or stagiaire.get("prenom")
        or ""
    ).strip()

    nom = (
        stagiaire.get("last_name")
        or stagiaire.get("nom")
        or ""
    ).strip()

    # Fallback sur name
    if not prenom or not nom:

        full_name = (
            candidat.get("name")
            or ""
        ).strip()

        parties = full_name.split(None, 1)

        if not prenom and parties:
            prenom = parties[0]

        if not nom and len(parties) > 1:
            nom = parties[1]

    nom_stagiaire = (
        f"Monsieur {nom.upper()} {prenom.capitalize()}"
    ).strip()


    # =====================================================
    # 2. PERIODE - FORMULAIRE STAGIAIRE
    # =====================================================

    period = (
        stagiaire.get("period")
        or candidat.get("period")
        or ""
    ).strip()

    dates = re.findall(
        r"\d{4}-\d{2}-\d{2}",
        period
    )

    date_debut = ""

    if dates:

        try:

            date_debut = datetime.strptime(
                dates[0],
                "%Y-%m-%d"
            ).strftime(
                "%d/%m/%Y"
            )

        except ValueError:
            pass


    duree = duree_stage_en_mois(
        period
    )


    # =====================================================
    # 3. ZONE - FORMULAIRE STAGIAIRE
    # =====================================================

    zone = (
        stagiaire.get("zone")
        or candidat.get("zone")
        or ""
    ).strip()


    # =====================================================
    # 4. DIRECTION / POLE - AFFECTATION RH
    # =====================================================

    department = (
        stagiaire.get("department")
        or candidat.get("department")
        or ""
    ).strip()


    # Exemple :
    # DSI - Direction Systèmes d'Information
    #
    # code_department = DSI
    # libelle_department = Direction Systèmes d'Information

    # =====================================================
    # 4. AFFECTATION
    # =====================================================

    department = (
        stagiaire.get("department")
        or candidat.get("department")
        or ""
    ).strip()


    affectation_config = (
        DECISION_AFFECTATION_MAP.get(
            department,
            {}
        )
    )


    # Direction officielle de la décision
   # =====================================================
# DIRECTION / POLE / DIVISION / ZONE
# =====================================================

    department = (
        stagiaire.get("department")
        or candidat.get("department")
        or ""
    ).strip()

    affectation_config = (
        DECISION_AFFECTATION_MAP.get(
            department,
            {}
        )
    )

    # Zone choisie par le stagiaire dans son formulaire
    zone_decision = (
        stagiaire.get("zone")
        or candidat.get("zone")
        or ""
    ).strip()

    if not zone_decision:
        zone_decision = "Port de Casablanca"


    # La zone est dynamique
    direction = zone_decision


    # Le pôle vient de l'affectation RH
    pole = (
        affectation_config.get("pole")
        or department
        or ""
    )


    # La division vient de l'affectation
    division = (
        affectation_config.get("division")
        or department
        or ""
    )


    # En-tête dynamique
    entite_header = (
        f"au {zone_decision}"
    )


    

       # =====================================================
    # 5. RESPONSABLE / ENCADRANT
    # =====================================================

    mentor = (
        stagiaire.get("mentor")
        or candidat.get("mentor")
        or ""
    ).strip()


    mentor_function = (
        stagiaire.get("mentor_function")
        or candidat.get("mentor_function")
        or ""
    ).strip()


    if mentor_function:
        responsable = mentor_function

    elif mentor:
        responsable = mentor

    else:
        responsable = ""

    # =====================================================
    # 7. THEME DE STAGE - AFFECTATION
    # =====================================================

    project = (
        stagiaire.get("project")
        or candidat.get("project")
        or ""
    ).strip()


    # =====================================================
    # 8. DATE DECISION
    # =====================================================

    now_ma = datetime.now()


    # =====================================================
    # 9. EN-TETE
    # =====================================================

    # if zone:

    #     if zone.lower().startswith("port "):
    #         entite_header = f"au {zone}"

    #     elif "casablanca" in zone.lower():
    #         entite_header = (
    #             f"à {zone}"
    #         )

    #     else:
    #         entite_header = zone

    # else:

    #     entite_header = (
    #         libelle_department
    #     )


    # =====================================================
    # 10. RESULTAT
    # =====================================================

    resultat = {

    "reference":
        f"TCR/{now_ma.year}",

    "date_decision":
        now_ma.strftime("%d/%m/%Y"),

    "direction":
        direction,

    "pole":
        pole,

    "entite_header":
        entite_header,

    "nom_stagiaire":
        nom_stagiaire,

    "responsable":
        responsable,

    "division":
        division,

    "duree":
        duree,

    "date_debut":
        date_debut,

    "zone":
        zone_decision,

    "project":
        project,

    "mentor":
        mentor,

    "mentor_function":
        mentor_function,
}


    print(
        "[DECISION AUTO]",
        {
            "nom": nom_stagiaire,
            "period": period,
            "department": department,
            "zone": zone,
            "mentor": mentor,
            "project": project,
            "resultat": resultat,
        }
    )


    return resultat
    
@app.get("/api/candidates/decision/<candidate_id>")
@login_required("rh")
def api_get_decision_stage(candidate_id):

    if not supabase:
        return jsonify(
            success=False,
            error="Supabase non configuré"
        ), 500

    try:

        result = (
            supabase
            .table(TABLE_APPLICATIONS)
            .select("*")
            .eq("id", candidate_id)
            .limit(1)
            .execute()
        )

        if not result.data:
            return jsonify(
                success=False,
                error="Stagiaire introuvable"
            ), 404


        stagiaire = result.data[0]

        candidat = normaliser_candidat(
            stagiaire
        )


        # ==========================================
        # NOM
        # ==========================================

        prenom = (
            stagiaire.get("first_name")
            or stagiaire.get("prenom")
            or ""
        ).strip()

        nom = (
            stagiaire.get("last_name")
            or stagiaire.get("nom")
            or ""
        ).strip()

        if not prenom or not nom:

            full_name = (
                candidat.get("name")
                or ""
            ).strip()

            parts = full_name.split(None, 1)

            if not prenom and parts:
                prenom = parts[0]

            if not nom and len(parts) > 1:
                nom = parts[1]


        nom_decision = (
            f"Monsieur {nom.upper()} "
            f"{prenom.capitalize()}"
        ).strip()


        # ==========================================
        # PÉRIODE
        # ==========================================

        period = (
            candidat.get("period")
            or ""
        )

        date_debut = ""

        import re

        dates = re.findall(
            r"\d{4}-\d{2}-\d{2}",
            period
        )

        if dates:
            try:

                date_debut = datetime.strptime(
                    dates[0],
                    "%Y-%m-%d"
                ).strftime(
                    "%d/%m/%Y"
                )

            except Exception:
                pass


        duree = duree_stage_en_mois(
            period
        )


        # ==========================================
        # AFFECTATION
        # ==========================================

        department = (
            stagiaire.get("department")
            or candidat.get("department")
            or ""
        ).strip()

        division_mapping = {

            "DSI - Direction Systèmes d'Information":
                "Division Systèmes d'Information",

        }

        division = division_mapping.get(
            department,
            department
        )


        responsable = (
            stagiaire.get("mentor_function")
            or candidat.get("mentor_function")
            or ""
        ).strip()

        if (
            not responsable
            and department.startswith("DSI")
        ):
            responsable = (
                "Responsable Systèmes d'Information"
            )


        # ==========================================
        # VALEURS PAR DÉFAUT
        # ==========================================

        now = datetime.now()

        defaults = {

            "reference":
                f"TCR/{now.year}",

            "date_decision":
                now.strftime("%d/%m/%Y"),

            "direction":
                "Port de Casablanca",

            "pole":
                "Trafics Conteneur et Roulier",

            "entite_header":
                "au Port de Casablanca "
                "Trafic Conteneur & Roulier",

            "nom_stagiaire":
                nom_decision,

            "responsable":
                responsable,

            "division":
                division,

            "duree":
                duree,

            "date_debut":
                date_debut,
        }


            # ==========================================
        # VALEURS DÉJÀ CORRIGÉES PAR LE RH
        # ==========================================

        saved_data = (
            stagiaire.get("decision_data")
            or {}
        )

        # Ne pas laisser une ancienne valeur vide
        # remplacer une valeur automatique correcte
        saved_data = {
            key: value
            for key, value in saved_data.items()
            if value not in (None, "")
        }

        data = {
            **defaults,
            **saved_data
        }

        return jsonify(
            success=True,
            numero=stagiaire.get(
                "decision_numero"
            ),
            decision_pdf=stagiaire.get(
                "decision_pdf"
            ),
            data=data
        )

    except Exception as exc:

        import traceback
        traceback.print_exc()

        return jsonify(
            success=False,
            error=str(exc)
        ), 500
        
    except Exception as exc:

        import traceback
        traceback.print_exc()

        return jsonify(
            success=False,
            error=str(exc)
        ), 500    
    
@app.post("/api/candidates/decision/generer")
@app.route("/download/decision/<path:filename>")
@login_required("rh")
def api_generer_decision_stage():

    if not supabase:
        return jsonify(
            success=False,
            error="Supabase non configuré"
        ), 500


    corps = request.get_json(
        silent=True
    ) or {}

    candidate_id = corps.get("id")
    signature = corps.get("signature")


    if not candidate_id:
        return jsonify(
            success=False,
            error="ID du stagiaire manquant"
        ), 400


    if not signature:
        return jsonify(
            success=False,
            error="La signature RH est obligatoire"
        ), 400


    try:

        result = (
            supabase
            .table(TABLE_APPLICATIONS)
            .select("*")
            .eq("id", candidate_id)
            .limit(1)
            .execute()
        )

        if not result.data:

            return jsonify(
                success=False,
                error="Stagiaire introuvable"
            ), 404


        stagiaire = result.data[0]

        candidat = normaliser_candidat(
            stagiaire
        )


        # ==============================================
        # Vérifier que l'affectation existe
        # ==============================================

        deja_affecte = bool(
        stagiaire.get("fiche_accueil_pdf")
        or stagiaire.get("mentor")
        or stagiaire.get("encadrant_id")
        or stagiaire.get("project")
        )

        if not deja_affecte:

            return jsonify(
                success=False,
                error=(
                    "Le stagiaire doit d'abord "
                    "être affecté."
                )
            ), 403


        # ==============================================
        # NUMÉRO AUTOMATIQUE
        # ==============================================

        # Important :
        # si la décision existe déjà,
        # on garde son numéro.

        # ==============================================
        # NUMÉRO : AUTOMATIQUE OU MANUEL
        # ==============================================

        numero_mode = (
            corps.get("numero_mode")
            or "auto"
        ).strip().lower()


        if numero_mode == "manuel":

            numero_manuel = str(
                corps.get("numero_manuel")
                or ""
            ).strip()


            if not numero_manuel:

                return jsonify(
                    success=False,
                    error="Le numéro manuel est obligatoire."
                ), 400


            try:

                numero = int(
                    numero_manuel
                )

            except ValueError:

                return jsonify(
                    success=False,
                    error=(
                        "Le numéro de décision doit "
                        "être un nombre valide."
                    )
                ), 400


            if numero <= 0:

                return jsonify(
                    success=False,
                    error=(
                        "Le numéro de décision doit "
                        "être supérieur à zéro."
                    )
                ), 400


            # Vérifier qu'un autre stagiaire
            # n'utilise pas déjà ce numéro

            existing = (
                supabase
                .table(TABLE_APPLICATIONS)
                .select("id")
                .eq("decision_numero", numero)
                .neq("id", candidate_id)
                .limit(1)
                .execute()
            )


            if existing.data:

                return jsonify(
                    success=False,
                    error=(
                        f"La décision N°{numero} "
                        "existe déjà."
                    )
                ), 409


        else:

            numero_mode = "auto"

            # Si une décision existe déjà,
            # conserver son numéro.
            numero = stagiaire.get(
                "decision_numero"
            )

            if not numero:

                numero = (
                    get_next_decision_stage_number()
                )


               # ==============================================
        # DONNÉES AUTOMATIQUES
        # ==============================================

        auto_data = (
            construire_decision_auto(
                stagiaire
            )
        )


        # ==============================================
        # DONNÉES FINALES
        # ==============================================

        decision_info = {

            "numero":
                numero,

            "reference":
                corps.get("reference")
                or auto_data["reference"],

            "date_decision":
                corps.get("date_decision")
                or auto_data["date_decision"],

            "direction":
                corps.get("direction")
                or auto_data["direction"],

            "pole":
                corps.get("pole")
                or auto_data["pole"],

            "entite_header":
                corps.get("entite_header")
                or auto_data["entite_header"],

            "nom_stagiaire":
                corps.get("nom_stagiaire")
                or auto_data["nom_stagiaire"],

            "responsable":
                corps.get("responsable")
                or auto_data["responsable"],

            "division":
                corps.get("division")
                or auto_data["division"],

            "duree":
                auto_data["duree"],

            "date_debut":
                corps.get("date_debut")
                or auto_data["date_debut"],

            "signature":
                signature,
        }


        affectation = {

            "department":
                stagiaire.get("department")
                or candidat.get("department")
                or "",

            "mentor":
                stagiaire.get("mentor")
                or candidat.get("mentor")
                or "",

            "mentor_function":
                stagiaire.get("mentor_function")
                or candidat.get("mentor_function")
                or "",

            "project":
                stagiaire.get("project")
                or candidat.get("project")
                or "",
        }


        # ==============================================
        # GÉNÉRER
        # ==============================================

        pdf_filename = (
            generer_decision_stage_pdf(
                stagiaire,
                affectation,
                decision_info
            )
        )


        if not pdf_filename:

            return jsonify(
                success=False,
                error=(
                    "Erreur lors de la "
                    "génération de la décision"
                )
            ), 500


        # ==============================================
        # SAUVEGARDE SUPABASE
        # ==============================================

        decision_data = {
        "numero_mode": numero_mode,
        "reference": decision_info["reference"],
        "date_decision": decision_info["date_decision"],
        "direction": decision_info["direction"],
        "pole": decision_info["pole"],
        "entite_header": decision_info["entite_header"],
        "nom_stagiaire": decision_info["nom_stagiaire"],
        "responsable": decision_info["responsable"],
        "division": decision_info["division"],
        "duree": decision_info["duree"],
        "date_debut": decision_info["date_debut"],
        }

        decision_data = {
            key: value
            for key, value in decision_data.items()
            if value not in (None, "")
        }

        update_payload = {

            "decision_pdf":
                pdf_filename,

            "decision_numero":
                numero,

            "decision_reference":
                decision_info["reference"],

            "decision_status":
                "Généré",

            "decision_data":
                decision_data,

            "decision_generated_at":
                stagiaire.get("decision_generated_at")
                or datetime.now(timezone.utc).isoformat(),

            "decision_updated_at":
                datetime.now(timezone.utc).isoformat(),
        }


        supabase_executer_update_eq(
            supabase,
            TABLE_APPLICATIONS,
            update_payload,
            "id",
            candidate_id
        )


        # ==============================================
        # NOTIFICATION STAGIAIRE
        # ==============================================

        notifications = ajouter_notification(
            stagiaire,
            (
                "Votre décision de stage "
                "officielle est maintenant disponible."
            )
        )

        supabase_executer_update_eq(
            supabase,
            TABLE_APPLICATIONS,
            {
                "notifications":
                    notifications
            },
            "id",
            candidate_id
        )
        # ==============================================
        # EMAIL AU STAGIAIRE
        # ==============================================

        notifier_nouveau_document_email(
            stagiaire,
            "Décision de stage"
        )
        # ==============================================
        # EMAIL - DÉCISION DISPONIBLE
        # ==============================================

        notifier_nouveau_document_email(
            stagiaire,
            "Décision de stage"
        )


        return jsonify(

            success=True,

            decision_pdf=
                pdf_filename,

            decision_numero=
                numero,

            decision_reference=
            decision_info["reference"],

            message=(
                "Décision de stage "
                "générée avec succès."
            )
        )


    except Exception as exc:

        import traceback
        traceback.print_exc()

        return jsonify(
            success=False,
            error=str(exc)
        ), 500


@app.route(
    "/download/decision/<path:filename>"
)
def download_decision(filename):

    try:

        base_filename = os.path.basename(
            filename
        )

        return send_file(
            os.path.join(
                app.config["GENERATED_PDFS_FOLDER"],
                base_filename
            ),
            as_attachment=True,
            mimetype="application/pdf"
        )

    except Exception as exc:

        return (
            f"Erreur lors du téléchargement: "
            f"{str(exc)}"
        ), 404
        


def generer_evaluation_pdf(stagiaire: dict, evaluation: dict, signatures: dict) -> str:
    """
    Generates a filled Evaluation PDF based on the original template.
    The template is landscape: 841.92 x 595.32
    """
    import os
    import base64
    from io import BytesIO
    from datetime import datetime
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import HexColor
    from pdfrw import PdfReader, PdfWriter, PageMerge

    try:
        output_dir = app.config['GENERATED_PDFS_FOLDER']
        os.makedirs(output_dir, exist_ok=True)

        base_dir = BASE_DIR
        template_path = os.path.join(base_dir, 'pdf', 'Evaluation stage.pdf')
        if not os.path.exists(template_path):
            print(f"[EVAL-PDF] Template not found: {template_path}")
            return None

        candidat = normaliser_candidat(stagiaire)
        full_name = candidat.get('name', '').strip()
        specialty = candidat.get('specialty', '') or ''
        school = candidat.get('school', '') or ''
        mentor = candidat.get('mentor', '') or evaluation.get('mentor', '') or ''
        mentor_function = evaluation.get('mentor_function', '') or candidat.get('mentor_function', '') or ''
        department = candidat.get('department', '') or ''
        period = candidat.get('period', '') or ''

        # Create overlay
        temp_overlay = os.path.join(output_dir, f"temp_eval_{candidat.get('id', 'temp')}.pdf")
        c = canvas.Canvas(temp_overlay, pagesize=(841.92, 595.32))

        brand_color = HexColor('#001a4d')
        c.setFillColor(brand_color)

        def draw_text(c, txt, x, y, max_width=400, font_size=11.5, font_name='Helvetica-Bold'):
            txt = str(txt).strip()
            size = font_size
            c.setFont(font_name, size)
            c.setFillColor(brand_color)
            while size > 6 and c.stringWidth(txt, font_name, size) > max_width:
                size -= 0.5
            c.setFont(font_name, size)
            c.drawString(x, y, txt)

        # Fill header fields (coordinates aligned with dotted lines baselines)
        # NOM & PRENOM: baseline 433.42, using 434.5
        draw_text(c, full_name.upper(), 245, 434.5, max_width=530, font_size=12)

        # SPECIALITE: baseline 406.51, using 407.5
        draw_text(c, specialty.upper(), 138, 407.5, max_width=250, font_size=12)
        # ECOLE OU INSTITUT: baseline 406.51, using 407.5, starts after label at 568
        draw_text(c, school.upper(), 568, 407.5, max_width=210, font_size=12)

        # NOM ENCADRANT: baseline 379.63, using 380.5, starts after label at 273
        draw_text(c, mentor.upper(), 273, 380.5, max_width=230, font_size=12)
        # FONCTION: baseline 379.63, using 380.5, starts after label at 565
        draw_text(c, mentor_function.upper(), 565, 380.5, max_width=215, font_size=12)

        # ENTITE D'ACCUEIL: baseline 352.75, using 353.5, starts after label at 168
        draw_text(c, department.upper(), 168, 353.5, max_width=245, font_size=12)
        # PERIODE: baseline 352.75, using 353.5, starts after label at 603
        draw_text(c, period.upper(), 603, 353.5, max_width=180, font_size=12)

        # Criteria checkmarks
        # Column centers: Faible=~328, Moyen=~458, Bon=~581, Excellent=~713
        # Row Y coords: Assiduite=309, Valeur Prof=295, Adaptation=278, Relations=255
        col_centers = {'faible': 328, 'moyen': 458, 'bon': 581, 'excellent': 713}
        row_ys = {
            'assiduite': 309,
            'valeur_professionnelle': 295,
            'capacite_adaptation': 278,
            'relations_humaines': 255,
        }

        criteria = evaluation.get('criteria', {})
        for criterion, y_pos in row_ys.items():
            value = criteria.get(criterion, '')
            x_pos = col_centers.get(value)
            if x_pos:
                c.setFillColor(brand_color)
                c.setFont('Helvetica-Bold', 14)
                c.drawCentredString(x_pos, y_pos - 2, '✓')

        # Appreciation globale: baseline 196.97, using 198.0
        appreciation = evaluation.get('appreciation_globale', '')
        if appreciation:
            draw_text(c, appreciation, 268, 198.0, max_width=535, font_size=11)

        # Observations: baseline 162.89, using 164.0
        observations = evaluation.get('observations', '')
        if observations:
            draw_text(c, observations, 268, 164.0, max_width=533, font_size=11)

        # Signatures
        def place_signature(c, sig_data, x, y, max_w=150, max_h=60):
            if not sig_data:
                return
            try:
                if sig_data.startswith('data:image'):
                    sig_data = sig_data.split(',', 1)[1]
                img_data = base64.b64decode(sig_data)
                img_buf = BytesIO(img_data)
                from reportlab.lib.utils import ImageReader
                img = ImageReader(img_buf)
                iw, ih = img.getSize()
                ratio = min(max_w / iw, max_h / ih)
                c.drawImage(img, x, y, width=iw * ratio, height=ih * ratio, mask='auto')
            except Exception as e:
                print(f"[EVAL-PDF] Signature error: {e}")

        # Signature encadrant: centered around X=230, Y=90-130
        place_signature(c, signatures.get('encadrant'), 160, 70, 150, 55)
        # Signature chef dept: centered around X=550, Y=90-130
        place_signature(c, signatures.get('chef_dept'), 470, 70, 150, 55)

        c.save()

        # Merge
        template_pdf = PdfReader(template_path)
        overlay_pdf = PdfReader(temp_overlay)
        PageMerge(template_pdf.pages[0]).add(overlay_pdf.pages[0]).render()

        pdf_filename = f"evaluation_{candidat.get('name', 'stagiaire').replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        pdf_path = os.path.join(output_dir, pdf_filename)
        PdfWriter(pdf_path, trailer=template_pdf).write()

        try:
            os.remove(temp_overlay)
        except Exception:
            pass

        print(f"[EVAL-PDF] Generated successfully: {pdf_filename}")
        return pdf_filename

    except Exception as e:
        print(f"[EVAL-PDF] Generation error: {e}")
        import traceback
        traceback.print_exc()
        return None


def duree_stage_en_mois(period: str) -> str:
    """
    Retourne la durée du stage écrite en lettres.
    Exemples :
    1 mois  -> d'un mois
    2 mois -> de deux mois
    3 mois -> de trois mois
    """
    from datetime import datetime
    import re

    dates = re.findall(r"\d{4}-\d{2}-\d{2}", str(period))

    if len(dates) < 2:
        return ""

    try:
        start = datetime.strptime(dates[0], "%Y-%m-%d").date()
        end = datetime.strptime(dates[1], "%Y-%m-%d").date()

        if end < start:
            return ""

        # Nombre de mois couverts par le stage
        months = (
            (end.year - start.year) * 12
            + (end.month - start.month)
            + 1
        )

        # nombres = {
        #     1: "un",
        #     2: "deux",
        #     3: "trois",
        #     4: "quatre",
        #     5: "cinq",
        #     6: "six",
        #     7: "sept",
        #     8: "huit",
        #     9: "neuf",
        #     10: "dix",
        #     11: "onze",
        #     12: "douze",
        # }

        if months == 1:
            return "d'un mois"

        return f"de {months} mois"

    except ValueError:
        return ""
    

def formater_periode_stage(period: str) -> str:
    """
    Convertit :
    2026-07-01 - 2026-07-31

    en :
    01/07/2026 au 31/07/2026
    """
    from datetime import datetime
    import re

    dates = re.findall(r"\d{4}-\d{2}-\d{2}", str(period))

    if len(dates) < 2:
        return ""

    try:
        start = datetime.strptime(dates[0], "%Y-%m-%d")
        end = datetime.strptime(dates[1], "%Y-%m-%d")

        return (
            f"{start.strftime('%d/%m/%Y')} "
            f"au "
            f"{end.strftime('%d/%m/%Y')}"
        )

    except ValueError:
        return ""



def generer_attestation_pdf(stagiaire: dict, rh_data: dict) -> str:
    """
    Generates a filled Attestation de Stage PDF.
    Only fills 2 blank spaces in the template:
    1. Directeur des Ressources Humaines (RH enters name)
    2. Nom du stagiaire (automatic from database)
    """
    import os
    from datetime import datetime
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import HexColor
    from pdfrw import PdfReader, PdfWriter, PageMerge

    try:
        output_dir = app.config['GENERATED_PDFS_FOLDER']
        os.makedirs(output_dir, exist_ok=True)

        base_dir = BASE_DIR
        template_path = os.path.join(base_dir, 'pdf', 'Attestation de stage .pdf')
        if not os.path.exists(template_path):
            print(f"[ATT-PDF] Template not found: {template_path}")
            return None

        candidat = normaliser_candidat(stagiaire)
        full_name = candidat.get('name', '').strip()

        temp_overlay = os.path.join(output_dir, f"temp_att_{candidat.get('id', 'temp')}.pdf")
        c = canvas.Canvas(temp_overlay, pagesize=(595.32, 841.92))

        brand_color = HexColor('#001a4d')
        c.setFillColor(brand_color)

        # Helper to draw text with auto-shrinkage to fit the blank spaces exactly
        def draw_text(c, txt, x, y, max_width=120, font_size=9.0, font_name='Helvetica-Bold'):
            txt = str(txt).strip()
            size = font_size
            c.setFont(font_name, size)
            c.setFillColor(brand_color)
            while size > 6.0 and c.stringWidth(txt, font_name, size) > max_width:
                size -= 0.5
            c.setFont(font_name, size)
            c.drawString(x, y, txt)

        # 1. Directeur des Ressources Humaines - blank space after "Je soussigné,"
        # Baseline Y = 626, starting at X = 195 (right after "Je soussigné," which ends at ~190)
        # Max width set to 68 to prevent overlap with "Directeur" which starts around X = 265
        
        directeur_rh = rh_data.get('directeur_rh', '')
        if directeur_rh:
            draw_text(c, directeur_rh, 195, 626, max_width=68, font_size=9.0)

        # 2. Nom du stagiaire - blank space before "a effectué" on Line 6
        # Baseline Y = 556, starts at left margin X = 135
        # Max width set to 72 to prevent overlap with "a effectué" which starts around X = 210
        if full_name:
            draw_text(c, full_name.upper(), 135, 556, max_width=72, font_size=9.0)

        # 3. Durée du stage - blank line after the trainee name.
        # Calculate calendar months from the stored "start - end" period.
        period = candidat.get('period', '') or ''
        
        # =====================================================
        # 3. DURÉE DU STAGE - 3ème espace blanc
        # =====================================================

        period = candidat.get('period', '') or ''

        if period:
            duration_text = duree_stage_en_mois(period)

            if duration_text:
                draw_text(
                    c,
                    duration_text,
                    281,        # X : après "un stage"
                    553.5,        # même ligne que le nom du stagiaire
                    max_width=55,
                    font_size=8.2 #plus petite police
                )


    # =====================================================
    # 4. PÉRIODE DU STAGE - 4ème espace blanc
    # =====================================================

            if period:
                periode_formatee = formater_periode_stage(period)

                if periode_formatee:
                    draw_text(
                        c,
                        periode_formatee,
                        245,        # X : après "à compter du"
                        539.5,        # ligne suivante
                        max_width=200,
                        font_size=9.0
                    )

        c.save()

        # Merge overlay with template
        template_pdf = PdfReader(template_path)
        overlay_pdf = PdfReader(temp_overlay)
        PageMerge(template_pdf.pages[0]).add(overlay_pdf.pages[0]).render()

        pdf_filename = f"attestation_{candidat.get('name', 'stagiaire').replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        pdf_path = os.path.join(output_dir, pdf_filename)
        PdfWriter(pdf_path, trailer=template_pdf).write()

        try:
            os.remove(temp_overlay)
        except Exception:
            pass

        print(f"[ATT-PDF] Generated successfully: {pdf_filename}")
        return pdf_filename

    except Exception as e:
        print(f"[ATT-PDF] Generation error: {e}")
        import traceback
        traceback.print_exc()
        return None


@app.route("/")
def home():
    return render_template("index.html")



@app.route("/stagiaire")
@login_required("stagiaire")
def stagiaire():
    candidat, erreur = charger_candidature_utilisateur()
    if candidat:
        lier_candidature_au_compte(str(candidat["id"]))
    mode_vue = vue_stagiaire_pour(candidat)
    return render_template(
        "dashboard.html",
        user=nom_utilisateur(),
        user_email=session.get("user_email") or "",
        zones=ZONES,
        candidat=candidat,
        mode_vue=mode_vue,
        doc_labels=DOC_LABELS,
        documents_requis=DOCUMENTS_REQUIS,
        db_error=erreur,
    )


@app.route("/rh")
@login_required("rh")
def rh():

    candidates, db_error = charger_candidats_avec_erreur()

    rh_name = nom_utilisateur()

    try:

        appliquer_session_supabase(supabase)

        user_id = session.get("user_id")

        if user_id:

            result = (
                supabase
                .table("profiles")
                .select("name")
                .eq("id", user_id)
                .limit(1)
                .execute()
            )

            if result.data:

                db_name = (
                    result.data[0].get("name")
                    or ""
                ).strip()

                if db_name:

                    rh_name = db_name

                    # Garder la session synchronisée
                    session["user_name"] = db_name

    except Exception as exc:

        print(
            "[RH] Erreur chargement profil :",
            exc
        )


    return render_template(
        "dashboard_rh.html",
        user=rh_name,
        user_email=session.get("user_email") or "",
        candidates=candidates,
        poles=POLES,
        db_error=db_error,
    )


@app.route("/affectation")
@login_required("affectation")
def affectation():

    if not supabase:
        return render_template(
            "dashboard_affectation.html",
            user=nom_utilisateur(),
            candidates=[],
        )

    try:
        appliquer_session_supabase(supabase)

        user_id = session.get("user_id")

        profile_result = (
            supabase
            .table("profiles")
            .select("id, name, role, encadrant_id")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )

        if not profile_result.data:
            print("[AFFECTATION] Profil introuvable")

            return render_template(
                "dashboard_affectation.html",
                user=nom_utilisateur(),
                candidates=[],
            )

        profil = profile_result.data[0]

        encadrant_id = profil.get("encadrant_id")

        print(
            "[AFFECTATION] profil connecté :",
            profil
        )

        if not encadrant_id:
            print(
                "[AFFECTATION] encadrant_id manquant"
            )

            return render_template(
                "dashboard_affectation.html",
                user=profil.get("name") or nom_utilisateur(),
                candidates=[],
            )

        candidats = [
            c
            for c in charger_candidats()
            if (
                c.get("status") == "Accepté"
                and str(c.get("encadrant_id"))
                == str(encadrant_id)
            )
        ]

        print(
            "[AFFECTATION] stagiaires trouvés :",
            len(candidats)
        )

        return render_template(
            "dashboard_affectation.html",
            user=profil.get("name") or nom_utilisateur(),
            candidates=candidats,
        )

    except Exception as exc:
        print(
            "[AFFECTATION] erreur :",
            exc
        )

        return render_template(
            "dashboard_affectation.html",
            user=nom_utilisateur(),
            candidates=[],
        )


@app.route("/login", methods=["GET", "POST"])
def login():
    if utilisateur_connecte():
        return redirect(redirection_pour_role())

    erreur = None
    succes = request.args.get("registered")

    if request.method == "POST":
        if not supabase:
            erreur = "Supabase non configuré (.env)"
        else:
            email = (request.form.get("email") or "").strip().lower()
            password = (request.form.get("password") or "").strip()

            if not email or not password:
                erreur = "Email et mot de passe obligatoires."
            else:
                try:
                    auth_response = supabase.auth.sign_in_with_password(
                        {"email": email, "password": password}
                    )
                    appliquer_session_supabase(supabase)
                    profil = assurer_profil(supabase, auth_response.user)

                    if not enregistrer_session(auth_response, profil, inscription=False):
                        erreur = (
                            "Profil introuvable ou rôle non défini. "
                            "Exécutez supabase/migrations/supabase_auth.sql et mettez à jour la table profiles."
                        )
                    else:
                        cible = cible_apres_login(
                            role_utilisateur(),
                            request.args.get("next"),
                        )
                        return redirect(cible)
                except Exception as exc:
                    print(f"[AUTH] Erreur login ({email}): {exc}")
                    erreur = message_erreur_auth(exc)

    return render_template("login.html", error=erreur, success=succes)


@app.route("/register", methods=["GET", "POST"])
def register():
    """Inscription publique réservée aux stagiaires uniquement."""
    if utilisateur_connecte():
        return redirect(redirection_pour_role())

    erreur = None

    if request.method == "POST":
        if not supabase:
            erreur = "Supabase non configuré (.env)"
        else:
            name = (request.form.get("name") or "").strip()
            email = (request.form.get("email") or "").strip().lower()
            password = (request.form.get("password") or "").strip()
            role_demande = (request.form.get("role") or ROLE_INSCRIPTION).strip().lower()

            ok, msg = inscription_autorisee(email, role_demande)
            if not ok:
                erreur = msg
            elif not name or not email or not password:
                erreur = "Tous les champs sont obligatoires."
            elif len(password) < 6:
                erreur = "Le mot de passe doit contenir au moins 6 caractères."
            else:
                try:
                    if supabase_admin:
                        auth_response = supabase_admin.auth.admin.create_user(
                            {
                                "email": email,
                                "password": password,
                                "email_confirm": True,
                                "user_metadata": {
                                    "full_name": name,
                                    "role": ROLE_INSCRIPTION,
                                }
                            }
                        )
                        user = None
                        if hasattr(auth_response, "user"):
                            user = auth_response.user
                        elif isinstance(auth_response, dict) and "user" in auth_response:
                            user = auth_response["user"]
                        else:
                            user = auth_response

                        if user:
                            assurer_profil(supabase, user)
                            return redirect(url_for("login", registered=1))

                    auth_response = supabase.auth.sign_up(
                        {
                            "email": email,
                            "password": password,
                            "options": {
                                "data": {
                                    "full_name": name,
                                    "role": ROLE_INSCRIPTION,
                                }
                            },
                        }
                    )

                    if auth_response.session:
                        appliquer_session_supabase(supabase)
                        profil = assurer_profil(supabase, auth_response.user)
                        enregistrer_session(auth_response, profil, inscription=True)
                        return redirect(redirection_pour_role(ROLE_INSCRIPTION))

                    return redirect(url_for("login", registered=1))
                except Exception as exc:
                    print(f"[AUTH] Erreur inscription: {exc}")
                    erreur = message_erreur_auth(exc)

    return render_template("register.html", error=erreur)


@app.route("/logout")
def logout():
    if supabase and session.get("access_token"):
        try:
            appliquer_session_supabase(supabase)
            supabase.auth.sign_out()
        except Exception as exc:
            print(f"[AUTH] Erreur logout: {exc}")
    session.clear()
    return redirect(url_for("login"))


# ============================================================
# GESTION DU PROFIL RH
# ============================================================

ROLES_MEMBRES_INTERNES = {"rh", "affectation"}


def _extraire_user_auth(response):
    if response is None:
        return None

    user = getattr(response, "user", None)
    if user:
        return user

    if isinstance(response, dict):
        return response.get("user")

    return response


def _valeur_user(user, cle, default=None):
    if user is None:
        return default

    if isinstance(user, dict):
        return user.get(cle, default)

    return getattr(user, cle, default)


def synchroniser_profil_interne(user_obj, full_name, role):
    """
    Synchronise le compte Auth avec la table profiles.
    """
    client = supabase_admin or supabase

    if not client or not user_obj:
        return

    user_id = str(_valeur_user(user_obj, "id") or "")
    if not user_id:
        return

    # Laisser d'abord le helper existant créer le profil s'il n'existe pas.
    try:
        assurer_profil(client, user_obj)
    except Exception as exc:
        print(f"[RH PROFILE] assurer_profil: {exc}")

    payload = {
        "full_name": full_name,
        "role": role,
    }

    # Schéma standard Supabase : profiles.id = auth.users.id
    try:
        result = (
            client.table("profiles")
            .update(payload)
            .eq("id", user_id)
            .execute()
        )

        if result.data:
            return
    except Exception as exc:
        print(f"[RH PROFILE] update profiles.id: {exc}")

    # Fallback si ta table utilise user_id
    try:
        result = (
            client.table("profiles")
            .update(payload)
            .eq("user_id", user_id)
            .execute()
        )

        if result.data:
            return
    except Exception as exc:
        print(f"[RH PROFILE] update profiles.user_id: {exc}")

@app.get("/api/rh/profile")
@login_required("rh")
def api_get_rh_profile():

    user_id = session.get("user_id")

    if not user_id:
        return jsonify(
            success=False,
            error="Utilisateur introuvable."
        ), 401

    try:

        profile_result = (
            supabase
            .table("profiles")
            .select("name")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )

        name = ""

        if profile_result.data:
            name = (
                profile_result.data[0].get("name")
                or ""
            ).strip()


        parts = name.split(None, 1)

        first_name = (
            parts[0]
            if parts
            else ""
        )

        last_name = (
            parts[1]
            if len(parts) > 1
            else ""
        )


        # Email depuis Supabase Auth
        user_response = (
            supabase_admin
            .auth
            .admin
            .get_user_by_id(user_id)
        )

        user = user_response.user

        email = user.email or ""


        return jsonify(
            success=True,
            first_name=first_name,
            last_name=last_name,
            email=email
        )


    except Exception as exc:

        print(
            "[RH PROFILE GET]",
            exc
        )

        return jsonify(
            success=False,
            error=str(exc)
        ), 500



@app.post("/api/rh/profile")
@login_required("rh")
def api_update_rh_profile():

    if not supabase_admin:
        return jsonify(
            success=False,
            error="SUPABASE_SERVICE_ROLE_KEY non configurée."
        ), 500

    corps = request.get_json() or {}

    first_name = (
        corps.get("first_name")
        or ""
    ).strip()

    last_name = (
        corps.get("last_name")
        or ""
    ).strip()

    email = (
        corps.get("email")
        or ""
    ).strip().lower()

    password = (
        corps.get("password")
        or ""
    )

    password_confirm = (
        corps.get("password_confirm")
        or ""
    )

    if not first_name or not last_name or not email:
        return jsonify(
            success=False,
            error="Prénom, nom et email obligatoires."
        ), 400

    if password and len(password) < 6:
        return jsonify(
            success=False,
            error="Le mot de passe doit contenir au moins 6 caractères."
        ), 400

    if password != password_confirm:
        return jsonify(
            success=False,
            error="Les mots de passe ne correspondent pas."
        ), 400

    user_id = session.get("user_id")

    if not user_id:
        return jsonify(
            success=False,
            error="Utilisateur introuvable."
        ), 401

    name = f"{first_name} {last_name}".strip()

    try:

        # =============================================
        # 1. MODIFIER EMAIL / PASSWORD DANS AUTH
        # =============================================

        auth_update = {
            "email": email
        }

        if password:
            auth_update["password"] = password

        supabase_admin.auth.admin.update_user_by_id(
            user_id,
            auth_update
        )


        # =============================================
        # 2. MODIFIER LE NOM DANS PROFILES
        # =============================================

        (
            supabase_admin
            .table("profiles")
            .update({
                "name": name
            })
            .eq("id", user_id)
            .execute()
        )


        # =============================================
        # 3. METTRE À JOUR LA SESSION ACTUELLE
        # =============================================

        session["user_name"] = name
        session["user_email"] = email


        return jsonify(
            success=True,
            name=name,
            email=email
        )


    except Exception as exc:

        print(
            "[RH PROFILE UPDATE]",
            exc
        )

        return jsonify(
            success=False,
            error=str(exc)
        ), 500


@app.post("/api/rh/members")
@login_required("rh")
def api_create_rh_member():

    if not supabase_admin:
        return jsonify(
            success=False,
            error="SUPABASE_SERVICE_ROLE_KEY non configurée."
        ), 500

    corps = request.get_json() or {}

    first_name = (corps.get("first_name") or "").strip()
    last_name = (corps.get("last_name") or "").strip()
    email = (corps.get("email") or "").strip().lower()
    password = corps.get("password") or ""
    password_confirm = corps.get("password_confirm") or ""

    # RH par défaut
    role = (corps.get("role") or "rh").strip().lower()

    # Sécurité : uniquement comptes internes
    if role not in {"rh", "affectation"}:
        return jsonify(
            success=False,
            error="Rôle invalide."
        ), 400

    if not first_name or not last_name or not email or not password:
        return jsonify(
            success=False,
            error="Tous les champs sont obligatoires."
        ), 400

    if len(password) < 6:
        return jsonify(
            success=False,
            error="Le mot de passe doit contenir au moins 6 caractères."
        ), 400

    if password != password_confirm:
        return jsonify(
            success=False,
            error="Les mots de passe ne correspondent pas."
        ), 400

    name = f"{first_name} {last_name}".strip()

    try:

        # ==================================================
        # 1. CRÉER LE COMPTE DANS SUPABASE AUTH
        # ==================================================

        auth_response = (
            supabase_admin
            .auth
            .admin
            .create_user({
                "email": email,
                "password": password,
                "email_confirm": True,

                # IMPORTANT :
                # le rôle est aussi enregistré dans Auth
                "user_metadata": {
                    "name": name,
                    "role": role
                }
            })
        )

        user = auth_response.user

        if not user:
            return jsonify(
                success=False,
                error="Impossible de créer l'utilisateur."
            ), 500

        user_id = str(user.id)

        print(
            "[RH MEMBER] utilisateur Auth créé :",
            user_id,
            email,
            role
        )


        # ==================================================
        # 2. CRÉER / CORRIGER LE PROFIL
        # ==================================================
        #
        # NE PAS laisser assurer_profil décider du rôle.
        # On force explicitement profiles.role.
        # ==================================================

        (
            supabase_admin
            .table("profiles")
            .upsert(
                {
                    "id": user_id,
                    "name": name,
                    "role": role
                },
                on_conflict="id"
            )
            .execute()
        )


        # ==================================================
        # 3. VÉRIFICATION
        # ==================================================

        verification = (
            supabase_admin
            .table("profiles")
            .select("id, name, role")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )

        if not verification.data:
            raise Exception(
                "Le compte Auth a été créé mais le profil n'a pas été créé."
            )

        profil_cree = verification.data[0]

        print(
            "[RH MEMBER] profil créé :",
            profil_cree
        )


        # Vérification supplémentaire du rôle
        if profil_cree.get("role") != role:

            raise Exception(
                f"Le rôle enregistré est incorrect : "
                f"{profil_cree.get('role')}"
            )


        return jsonify(
            success=True,
            member={
                "id": user_id,
                "name": name,
                "email": email,
                "role": role
            }
        ), 201


    except Exception as exc:

        print(
            "[RH MEMBER CREATE]",
            exc
        )

        return jsonify(
            success=False,
            error=str(exc)
        ), 500



@app.get("/api/mon-dossier")
@login_required("stagiaire")
def api_mon_dossier():
    candidat, erreur = charger_candidature_utilisateur()
    if erreur:
        return jsonify(success=False, error=erreur), 500
    if not candidat:
        return jsonify(success=True, candidat=None, mode_vue="form")
    return jsonify(
        success=True,
        candidat=candidat,
        mode_vue=vue_stagiaire_pour(candidat),
        documents=candidat.get("documents") or documents_uploades(str(candidat["id"])),
    )


@app.post("/api/apply")
@login_required("stagiaire")
def api_apply():
    if not supabase:
        return jsonify(success=False, error="Supabase non configuré"), 500

    existant, _ = charger_candidature_utilisateur()
    if existant:
        return jsonify(
            success=False,
            error="Vous avez déjà une candidature en cours. Complétez votre dossier existant.",
        ), 400

    corps = request.get_json() or {}
    if not (corps.get("first_name") and corps.get("last_name")) and not corps.get("name"):
        return jsonify(success=False, error="Nom et prénom obligatoires."), 400

    requis = ["phone", "school", "specialty", "zone", "start", "end"]
    manquants = [c for c in requis if not corps.get(c)]
    if manquants:
        return jsonify(
            success=False,
            error=f"Champs obligatoires manquants : {', '.join(manquants)}",
        ), 400

    corps["email"] = (session.get("user_email") or "").strip().lower()
    corps["user_id"] = session.get("user_id")

    try:
        reponse = inserer_candidature(corps)
        ligne = (reponse.data or [{}])[0]
        cid = ligne.get("id")
        if cid:
            session["candidature_id"] = str(cid)
            lier_candidature_au_compte(str(cid))
        return jsonify(success=True, id=cid, name=ligne.get("name") or corps.get("name"))
    except Exception as exc:
        print(f"[APPLY] Erreur insertion: {exc}")
        msg = message_erreur_supabase(exc)
        if "first_name" in str(exc):
            msg = "Le prénom est obligatoire (first_name)."
        elif "last_name" in str(exc):
            msg = "Le nom est obligatoire (last_name)."
        elif "applications_status_check" in str(exc) or "23514" in str(exc):
            msg = (
                "Statut non accepté par la base. Valeur utilisée : "
                f"'{STATUT_INITIAL_DB}'. Vérifiez supabase/migrations/supabase_fix_status.sql ou SUPABASE_STATUS_INITIAL dans .env"
            )
        return jsonify(success=False, error=msg), 500


@app.post("/api/candidates/status")
@login_required("rh")
def api_status():

    if not supabase:
        return jsonify(
            success=False,
            error="Supabase non configuré"
        ), 500

    corps = request.get_json() or {}

    statut_recu = corps.get("status")
    nouveau_statut = statut_pour_db(statut_recu)

    mise_a_jour = {
        "status": nouveau_statut,
        "rh_status_hint": "",
    }

    if corps.get("department"):
        mise_a_jour["department"] = corps.get("department")

    # =====================================================
    # SI LE RH ACCEPTE :
    # LE CHOIX DU MENTOR EST OBLIGATOIRE
    # =====================================================

    if statut_recu == "Accepté":

        mentor_id = corps.get("mentor_id")

        if not mentor_id:
            return jsonify(
                success=False,
                error="Veuillez choisir un mentor."
            ), 400

        try:
            mentor_result = (
                supabase
                .table("encadrants")
                .select("*")
                .eq("id", mentor_id)
                .limit(1)
                .execute()
            )

            if not mentor_result.data:
                return jsonify(
                    success=False,
                    error="Mentor introuvable."
                ), 404

            mentor_data = mentor_result.data[0]

            mise_a_jour["mentor"] = (
                mentor_data.get("nom") or ""
            ).strip()

            mise_a_jour["mentor_function"] = (
                mentor_data.get("fonction") or ""
            ).strip()

            mise_a_jour["encadrant_id"] = mentor_id

        except Exception as exc:
            return jsonify(
                success=False,
                error=f"Erreur mentor : {exc}"
            ), 500

    if nouveau_statut != "action_required":
        mise_a_jour["requested_doc_type"] = None

    try:

        query = (
            supabase
            .table(TABLE_APPLICATIONS)
            .update(mise_a_jour)
        )

        appliquer_filtre_identifiant(
            query,
            corps
        ).execute()

        return jsonify(success=True)

    except Exception as exc:

        return jsonify(
            success=False,
            error=str(exc)
        ), 500


@app.post("/api/candidates/department")
def api_department():
    """RH : attribue la Direction / Pôle à un stagiaire."""
    if not supabase:
        return jsonify(success=False, error="Supabase non configuré"), 500

    corps = request.get_json() or {}
    try:
        query = supabase.table(TABLE_APPLICATIONS).update({"department": corps.get("department")})
        appliquer_filtre_identifiant(query, corps).execute()
        return jsonify(success=True)
    except Exception as exc:
        return jsonify(success=False, error=str(exc)), 500
    
@app.post("/api/candidates/mentor")
@login_required("rh")
def api_assign_mentor():

    if not supabase:
        return jsonify(
            success=False,
            error="Supabase non configuré"
        ), 500

    corps = request.get_json() or {}

    candidate_id = corps.get("id")
    mentor_id = corps.get("mentor_id")

    if not candidate_id or not mentor_id:
        return jsonify(
            success=False,
            error="Stagiaire ou mentor manquant"
        ), 400

    try:

        # Récupérer le mentor sélectionné par le RH
        mentor_result = (
            supabase
            .table("encadrants")
            .select("*")
            .eq("id", mentor_id)
            .limit(1)
            .execute()
        )

        if not mentor_result.data:
            return jsonify(
                success=False,
                error="Mentor introuvable"
            ), 404

        mentor_data = mentor_result.data[0]

        mentor_nom = (
            mentor_data.get("nom")
            or ""
        ).strip()

        mentor_fonction = (
            mentor_data.get("fonction")
            or ""
        ).strip()

        # Affecter ce mentor au stagiaire
        update_data = {
            "mentor": mentor_nom,
            "mentor_function": mentor_fonction,
            "encadrant_id": mentor_id
        }

        supabase_executer_update_eq(
            supabase,
            TABLE_APPLICATIONS,
            update_data,
            "id",
            candidate_id
        )

        return jsonify(
            success=True,
            mentor=mentor_nom,
            mentor_function=mentor_fonction,
            mentor_id=mentor_id
        )

    except Exception as exc:

        import traceback
        traceback.print_exc()

        return jsonify(
            success=False,
            error=str(exc)
        ), 500
        
    
    # ============================================================
# PROFIL ENCADRANT / AFFECTATION
# ============================================================


@app.get("/api/encadrant/profile")
@login_required("affectation")
def api_get_encadrant_profile():

    if not supabase_admin:
        return jsonify(
            success=False,
            error="SUPABASE_SERVICE_ROLE_KEY non configurée."
        ), 500

    user_id = session.get("user_id")

    if not user_id:
        return jsonify(
            success=False,
            error="Session utilisateur introuvable."
        ), 401

    try:

        # ==================================================
        # PROFIL
        # ==================================================

        profile_result = (
            supabase_admin
            .table("profiles")
            .select("id, name, role, encadrant_id")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )

        if not profile_result.data:
            return jsonify(
                success=False,
                error="Profil encadrant introuvable."
            ), 404

        profile = profile_result.data[0]

        name = (
            profile.get("name")
            or ""
        ).strip()

        encadrant_id = profile.get("encadrant_id")


        # ==================================================
        # PRÉNOM / NOM
        # ==================================================

        parts = name.split(None, 1)

        first_name = (
            parts[0]
            if parts
            else ""
        )

        last_name = (
            parts[1]
            if len(parts) > 1
            else ""
        )


        # ==================================================
        # EMAIL SUPABASE AUTH
        # ==================================================

        auth_response = (
            supabase_admin
            .auth
            .admin
            .get_user_by_id(user_id)
        )

        auth_user = auth_response.user

        email = (
            auth_user.email
            if auth_user
            else ""
        )


        # ==================================================
        # INFORMATIONS ENCADRANT
        # ==================================================

        fonction = ""

        if encadrant_id:

            encadrant_result = (
                supabase_admin
                .table("encadrants")
                .select("*")
                .eq("id", encadrant_id)
                .limit(1)
                .execute()
            )

            if encadrant_result.data:

                fonction = (
                    encadrant_result.data[0]
                    .get("fonction")
                    or ""
                ).strip()


        return jsonify(
            success=True,

            first_name=first_name,
            last_name=last_name,

            email=email,

            fonction=fonction,

            encadrant_id=encadrant_id
        )


    except Exception as exc:

        print(
            "[ENCADRANT PROFILE GET]",
            exc
        )

        return jsonify(
            success=False,
            error=str(exc)
        ), 500



# ============================================================
# MODIFIER SON PROFIL ENCADRANT
# ============================================================

@app.post("/api/encadrant/profile")
@login_required("affectation")
def api_update_encadrant_profile():

    if not supabase_admin:
        return jsonify(
            success=False,
            error="SUPABASE_SERVICE_ROLE_KEY non configurée."
        ), 500

    corps = request.get_json() or {}

    first_name = (
        corps.get("first_name")
        or ""
    ).strip()

    last_name = (
        corps.get("last_name")
        or ""
    ).strip()

    email = (
        corps.get("email")
        or ""
    ).strip().lower()

    fonction = (
        corps.get("fonction")
        or ""
    ).strip()

    password = (
        corps.get("password")
        or ""
    )

    password_confirm = (
        corps.get("password_confirm")
        or ""
    )


    if not first_name or not last_name or not email:

        return jsonify(
            success=False,
            error="Prénom, nom et email obligatoires."
        ), 400


    if password and len(password) < 6:

        return jsonify(
            success=False,
            error="Le mot de passe doit contenir au moins 6 caractères."
        ), 400


    if password != password_confirm:

        return jsonify(
            success=False,
            error="Les mots de passe ne correspondent pas."
        ), 400


    user_id = session.get("user_id")

    if not user_id:

        return jsonify(
            success=False,
            error="Session utilisateur introuvable."
        ), 401


    name = f"{first_name} {last_name}".strip()


    try:

        # ==================================================
        # 1. EMAIL / PASSWORD AUTH
        # ==================================================

        auth_update = {
            "email": email
        }

        if password:
            auth_update["password"] = password


        supabase_admin.auth.admin.update_user_by_id(
            user_id,
            auth_update
        )


        # ==================================================
        # 2. RÉCUPÉRER LE PROFIL
        # ==================================================

        profile_result = (
            supabase_admin
            .table("profiles")
            .select("encadrant_id")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )

        if not profile_result.data:

            return jsonify(
                success=False,
                error="Profil encadrant introuvable."
            ), 404


        encadrant_id = (
            profile_result.data[0]
            .get("encadrant_id")
        )


        # ==================================================
        # 3. MODIFIER PROFILES
        # ==================================================

        (
            supabase_admin
            .table("profiles")
            .update({
                "name": name,

                # IMPORTANT
                "role": "affectation"
            })
            .eq("id", user_id)
            .execute()
        )


        # ==================================================
        # 4. MODIFIER TABLE ENCADRANTS
        # ==================================================

        if encadrant_id:

            (
                supabase_admin
                .table("encadrants")
                .update({
                    "nom": name,
                    "fonction": fonction
                })
                .eq("id", encadrant_id)
                .execute()
            )


        # ==================================================
        # 5. SESSION
        # ==================================================

        session["user_name"] = name
        session["user_email"] = email


        return jsonify(
            success=True,
            name=name,
            email=email,
            fonction=fonction
        )


    except Exception as exc:

        print(
            "[ENCADRANT PROFILE UPDATE]",
            exc
        )

        return jsonify(
            success=False,
            error=str(exc)
        ), 500



# ============================================================
# CRÉER UN NOUVEL ENCADRANT
# ============================================================

@app.post("/api/encadrant/members")
@login_required("affectation")
def api_create_encadrant_member():

    if not supabase_admin:

        return jsonify(
            success=False,
            error="SUPABASE_SERVICE_ROLE_KEY non configurée."
        ), 500


    corps = request.get_json() or {}

    first_name = (
        corps.get("first_name")
        or ""
    ).strip()

    last_name = (
        corps.get("last_name")
        or ""
    ).strip()

    email = (
        corps.get("email")
        or ""
    ).strip().lower()

    fonction = (
        corps.get("fonction")
        or ""
    ).strip()

    password = (
        corps.get("password")
        or ""
    )

    password_confirm = (
        corps.get("password_confirm")
        or ""
    )


    if not first_name or not last_name or not email or not password:

        return jsonify(
            success=False,
            error="Tous les champs obligatoires doivent être remplis."
        ), 400


    if len(password) < 6:

        return jsonify(
            success=False,
            error="Le mot de passe doit contenir au moins 6 caractères."
        ), 400


    if password != password_confirm:

        return jsonify(
            success=False,
            error="Les mots de passe ne correspondent pas."
        ), 400


    name = f"{first_name} {last_name}".strip()


    try:

        # ==================================================
        # 1. CRÉER LE COMPTE AUTH
        # ==================================================

        auth_response = (
            supabase_admin
            .auth
            .admin
            .create_user({

                "email": email,

                "password": password,

                "email_confirm": True,

                "user_metadata": {

                    "name": name,

                    # Le rôle TECHNIQUE reste affectation
                    "role": "affectation"
                }
            })
        )


        user = auth_response.user

        if not user:

            return jsonify(
                success=False,
                error="Impossible de créer le compte utilisateur."
            ), 500


        user_id = str(user.id)


        # ==================================================
        # 2. CHERCHER SI L'ENCADRANT EXISTE DÉJÀ
        # ==================================================

        existing = (
            supabase_admin
            .table("encadrants")
            .select("*")
            .eq("nom", name)
            .limit(1)
            .execute()
        )


        if existing.data:

            encadrant = existing.data[0]

            encadrant_id = encadrant.get("id")

            # Mettre à jour sa fonction
            if fonction:

                (
                    supabase_admin
                    .table("encadrants")
                    .update({
                        "fonction": fonction
                    })
                    .eq("id", encadrant_id)
                    .execute()
                )


        else:

            # ==================================================
            # 3. CRÉER L'ENCADRANT
            # ==================================================

            encadrant_result = (
                supabase_admin
                .table("encadrants")
                .insert({
                    "nom": name,
                    "fonction": fonction
                })
                .execute()
            )


            if not encadrant_result.data:

                # Nettoyer le compte Auth si création encadrant échoue
                try:
                    supabase_admin.auth.admin.delete_user(
                        user_id
                    )
                except Exception:
                    pass

                return jsonify(
                    success=False,
                    error="Impossible de créer l'encadrant."
                ), 500


            encadrant = encadrant_result.data[0]

            encadrant_id = encadrant.get("id")


        # ==================================================
        # 4. CRÉER / METTRE À JOUR PROFILES
        # ==================================================

        (
            supabase_admin
            .table("profiles")
            .upsert(
                {
                    "id": user_id,

                    "name": name,

                    # IMPORTANT :
                    # c'est ce rôle que ton login reconnaît
                    "role": "affectation",

                    # Liaison avec la table encadrants
                    "encadrant_id": encadrant_id
                },

                on_conflict="id"
            )
            .execute()
        )


        # ==================================================
        # 5. VÉRIFICATION
        # ==================================================

        verification = (
            supabase_admin
            .table("profiles")
            .select(
                "id, name, role, encadrant_id"
            )
            .eq("id", user_id)
            .limit(1)
            .execute()
        )


        if not verification.data:

            raise Exception(
                "Le profil encadrant n'a pas pu être créé."
            )


        profil = verification.data[0]


        if profil.get("role") != "affectation":

            raise Exception(
                "Le rôle du profil encadrant est incorrect."
            )


        if not profil.get("encadrant_id"):

            raise Exception(
                "L'encadrant_id n'a pas été enregistré."
            )


        print(
            "[ENCADRANT CREATE]",
            profil
        )


        return jsonify(

            success=True,

            member={
                "id": user_id,
                "name": name,
                "email": email,
                "fonction": fonction,
                "role": "affectation",
                "encadrant_id": encadrant_id
            }

        ), 201


    except Exception as exc:

        print(
            "[ENCADRANT CREATE ERROR]",
            exc
        )

        return jsonify(
            success=False,
            error=str(exc)
        ), 500







@app.post("/api/candidates/affect")
@login_required("affectation")
def api_affect():
    """
    Affectation:
    - saves project and mentor
    - generates the Fiche d'Accueil
    - stores the generated PDF filename in Supabase
    - notifies the trainee
    """

    if not supabase:
        return jsonify(
            success=False,
            error="Supabase non configuré"
        ), 500

    corps = request.get_json() or {}

    candidate_id = corps.get("id")

    if not candidate_id:
        return jsonify(
            success=False,
            error="ID du stagiaire manquant"
        ), 400

    try:

        print("\n" + "=" * 70)
        print("[AFFECTATION] Début affectation")
        print("[AFFECTATION] Candidate ID :", candidate_id)
        print("[AFFECTATION] Project :", corps.get("project"))
        print("[AFFECTATION] Mentor :", corps.get("mentor"))
        print("=" * 70)

        # =====================================================
        # 1. LOAD TRAINEE
        # =====================================================

        stagiaire_result = (
            supabase
            .table(TABLE_APPLICATIONS)
            .select("*")
            .eq("id", candidate_id)
            .limit(1)
            .execute()
        )

        if not stagiaire_result.data:
            print("[AFFECTATION] ERROR: trainee not found")

            return jsonify(
                success=False,
                error="Stagiaire non trouvé"
            ), 404

        stagiaire = stagiaire_result.data[0]
        
        # =====================================================
        # LE MENTOR A DÉJÀ ÉTÉ CHOISI PAR LE RH
        # =====================================================

        mentor = (
            stagiaire.get("mentor")
            or ""
        ).strip()

        mentor_function = (
            stagiaire.get("mentor_function")
            or ""
        ).strip()

        if not mentor:

            return jsonify(
                success=False,
                error=(
                    "Aucun mentor n'a été attribué "
                    "à ce stagiaire par le RH."
                )
            ), 403


        # Le profil Affectation connecté EST ce mentor
        # =====================================================
        # VÉRIFIER QUE LE STAGIAIRE APPARTIENT À
        # L'ENCADRANT ACTUELLEMENT CONNECTÉ
        # =====================================================

        user_id = session.get("user_id")

        if not user_id:
            return jsonify(
                success=False,
                error="Session utilisateur introuvable."
            ), 401

        profile_result = (
            supabase
            .table("profiles")
            .select("encadrant_id")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )

        if not profile_result.data:
            return jsonify(
                success=False,
                error="Profil encadrant introuvable."
            ), 403

        encadrant_connecte_id = (
            profile_result.data[0]
            .get("encadrant_id")
        )

        stagiaire_encadrant_id = (
            stagiaire.get("encadrant_id")
        )

        if (
            not encadrant_connecte_id
            or
            str(encadrant_connecte_id)
            !=
            str(stagiaire_encadrant_id)
        ):
            return jsonify(
                success=False,
                error=(
                    "Ce stagiaire ne vous est pas affecté."
                )
            ), 403

        print(
            "[AFFECTATION] Stagiaire trouvé :",
            stagiaire.get("name")
        )

        print(
            "[AFFECTATION] Period :",
            stagiaire.get("period")
        )

        print(
            "[AFFECTATION] Department :",
            stagiaire.get("department")
        )

        # =====================================================
        # 2. UPDATE PROJECT + MENTOR
        # =====================================================

        update_data = {
            "project":
                corps.get("project") or ""
        }

        supabase_executer_update_eq(
            supabase,
            TABLE_APPLICATIONS,
            update_data,
            "id",
            candidate_id
        )

        print(
            "[AFFECTATION] Project/mentor enregistrés"
        )
        query = supabase.table(TABLE_APPLICATIONS).update(update_data)

        update_result = appliquer_filtre_identifiant(
            query,
            corps
        ).execute()

        print("[AFFECTATION] UPDATE RESULT:", update_result.data)

        if not update_result.data:
            return jsonify(
                success=False,
                error="L'affectation n'a pas été enregistrée dans Supabase."
            ), 500

        # =====================================================
        # 3. IMPORTANT:
        # UPDATE LOCAL TRAINEE DATA TOO
        # =====================================================

        stagiaire["project"] = (
            update_data["project"]
        )

        # mentor et fonction restent ceux choisis par RH
        stagiaire["mentor"] = mentor
        stagiaire["mentor_function"] = mentor_function

        # =====================================================
        # 4. GENERATE FICHE ACCUEIL
        # =====================================================

        affectation_data = {

            "project":
                update_data["project"],

            "mentor":
                mentor,

            "mentor_function":
                mentor_function,

            "department":
                stagiaire.get("department") or "",
        }

        print(
            "[AFFECTATION] Génération fiche d'accueil..."
        )

        pdf_filename = generer_fiche_accueil_pdf_filled(
            stagiaire,
            affectation_data
        )

        print(
            "[AFFECTATION] PDF returned :",
            pdf_filename
        )

        # =====================================================
        # 5. CHECK PDF GENERATION
        # =====================================================

        if not pdf_filename:

            print(
                "[AFFECTATION] ERROR: "
                "generer_fiche_accueil_pdf_filled returned None"
            )

            return jsonify(
                success=False,
                error=(
                    "La fiche d'accueil n'a pas pu être générée. "
                    "Vérifiez le terminal Flask."
                )
            ), 500

        # =====================================================
        # 6. CHECK FILE EXISTS
        # =====================================================

        generated_file = os.path.join(
            app.config["GENERATED_PDFS_FOLDER"],
            os.path.basename(pdf_filename)
        )

        print(
            "[AFFECTATION] Expected file :",
            generated_file
        )

        print(
            "[AFFECTATION] File exists :",
            os.path.exists(generated_file)
        )

        if not os.path.exists(generated_file):

            return jsonify(
                success=False,
                error=(
                    "Le PDF a été généré mais le fichier "
                    "est introuvable dans generated_pdfs."
                )
            ), 500

        # =====================================================
        # 7. NOTIFICATION
        # =====================================================

        current_notifications = (
            stagiaire.get("notifications") or []
        )

        if not isinstance(
            current_notifications,
            list
        ):
            current_notifications = []

        new_notification = {
            "id": (
                f"notif_"
                f"{int(datetime.now().timestamp())}"
            ),
            "text": (
                "Votre fiche d'accueil de stage "
                "est désormais disponible."
            ),
            "date": datetime.now().isoformat(),
            "read": False
        }

        current_notifications.append(
            new_notification
        )

        # =====================================================
        # 8. SAVE PDF NAME IN SUPABASE
        # =====================================================

        update_payload = {
            "fiche_accueil_pdf":
                os.path.basename(pdf_filename),

            "notifications":
                current_notifications
        }

        print(
            "[AFFECTATION] Supabase update :",
            update_payload["fiche_accueil_pdf"]
        )

        supabase_executer_update_eq(
            supabase,
            TABLE_APPLICATIONS,
            update_payload,
            "id",
            candidate_id
        )

        # =====================================================
        # 9. VERIFY DATABASE
        # =====================================================

        verification = (
            supabase
            .table(TABLE_APPLICATIONS)
            .select(
                "id,fiche_accueil_pdf,project,mentor,mentor_function"
            )
            .eq("id", candidate_id)
            .limit(1)
            .execute()
        )

        if verification.data:

            print(
                "[AFFECTATION] Vérification Supabase :",
                verification.data[0]
            )

        # =====================================================
        # 10. EMAIL
        # =====================================================

        candidate_email = stagiaire.get(
            "email"
        )

        if candidate_email:

            subject = (
                "[Marsa Maroc] "
                "Fiche d'accueil disponible"
            )

            body = f"""Bonjour {stagiaire.get('name') or 'Stagiaire'},

Votre fiche d'accueil pour votre stage chez Marsa Maroc a été générée.

Vous pouvez la consulter et la télécharger depuis votre espace stagiaire.

Cordialement,
L'équipe RH Marsa Maroc
"""

            envoyer_email_stagiaire(
                candidate_id,
                candidate_email,
                subject,
                body
            )

        print(
            "[AFFECTATION] Fiche d'accueil terminée avec succès"
        )

        print("=" * 70 + "\n")

        # =====================================================
        # SUCCESS
        # =====================================================

        return jsonify(
            success=True,
            pdf_path=os.path.basename(
                pdf_filename
            )
        )

    except Exception as exc:

        import traceback

        print("\n[AFFECTATION] ERREUR !!!")
        traceback.print_exc()

        return jsonify(
            success=False,
            error=str(exc)
        ), 500
        
@app.get("/api/encadrants")
@login_required("rh")
def get_encadrants():
    """Récupère la liste des encadrants."""
    if not supabase:
        return jsonify(
            success=False,
            error="Supabase non configuré"
        ), 500

    try:
        appliquer_session_supabase(supabase)

        response = (
            supabase
            .table("encadrants")
            .select("*")
            .order("nom")
            .execute()
        )

        return jsonify(
            success=True,
            encadrants=response.data or []
        )

    except Exception as exc:
        print(f"[ENCADRANTS] Erreur chargement: {exc}")

        return jsonify(
            success=False,
            error=str(exc)
        ), 500


@app.post("/api/encadrants")
@login_required("rh")
def add_encadrant():
    """Ajoute un nouvel encadrant."""

    if not supabase:
        return jsonify(
            success=False,
            error="Supabase non configuré"
        ), 500

    appliquer_session_supabase(supabase)

    corps = request.get_json() or {}

    nom = (
        corps.get("nom") or ""
    ).strip()
    
    fonction = (
        corps.get("fonction") or ""
    ).strip()

    if not nom:
        return jsonify(
            success=False,
            error="Nom de l'encadrant manquant"
        ), 400

    try:
        existing = (
            supabase
            .table("encadrants")
            .select("*")
            .eq("nom", nom)
            .execute()
        )

        if existing.data:
            return jsonify(
                success=True,
                encadrant=existing.data[0],
                message="Encadrant déjà existant"
            )

        response = (
            supabase
            .table("encadrants")
            .insert({
                "nom": nom,
                "fonction": fonction
            })
            .execute()
        )

        if not response.data:
            return jsonify(
                success=False,
                error="L'encadrant n'a pas pu être créé."
            ), 500

        return jsonify(
            success=True,
            encadrant=response.data[0]
        )

    except Exception as exc:
        print(
            f"[ENCADRANTS] Erreur ajout de '{nom}': {exc}"
        )

        return jsonify(
            success=False,
            error=str(exc)
        ), 500

@app.post("/api/candidates/evaluation")
@login_required("affectation")
def api_candidates_evaluation():
    """Affectation : soumet la fiche d'évaluation (après validation du rapport) → envoi RH."""
    if not supabase:
        return jsonify(success=False, error="Supabase non configuré"), 500

    corps = request.get_json() or {}
    candidate_id = corps.get("id")
    if not candidate_id:
        return jsonify(success=False, error="ID du candidat manquant"), 400

    try:
        stagiaire_result = (
            supabase.table(TABLE_APPLICATIONS).select("*").eq("id", candidate_id).execute()
        )
        if not stagiaire_result.data:
            return jsonify(success=False, error="Stagiaire non trouvé"), 404

        stagiaire = stagiaire_result.data[0]
        candidat = normaliser_candidat(stagiaire)

        if candidat.get("intern_report_status") != "Validé":
            return jsonify(
                success=False,
                error="Le rapport de stage doit être validé avant de créer la fiche d'évaluation.",
            ), 403

        eval_status = candidat.get("evaluation_status") or ""
        if eval_status == "En attente":
            return jsonify(
                success=False,
                error="Une fiche d'évaluation est déjà en attente de validation RH.",
            ), 400

        evaluation_data = {
            "mentor_function": candidat.get("mentor_function") or stagiaire.get("mentor_function") or "",
            "criteria": corps.get("criteria", {}),
            "appreciation_globale": corps.get("appreciation_globale", ""),
            "observations": corps.get("observations", ""),
        }
        signatures = corps.get("signatures", {})

        pdf_path = generer_evaluation_pdf(stagiaire, evaluation_data, signatures)
        if not pdf_path:
            return jsonify(success=False, error="Erreur lors de la génération du PDF d'évaluation"), 500

        import datetime

        now_str = datetime.datetime.now().isoformat()
        update_payload = {
            "evaluation_pdf": pdf_path,
            "evaluation_status": "En attente",
            "evaluation_submitted_at": now_str,
            "evaluation_data": evaluation_data,
            "evaluation_reject_reason": None,
        }
        supabase_executer_update_eq(supabase, TABLE_APPLICATIONS, update_payload, "id", candidate_id)

        nom_stagiaire = candidat.get("name") or "Stagiaire"
        envoyer_email(
            os.getenv("EMAIL_RH", "rh@marsamaroc.ma"),
            "[Marsa Maroc] Fiche d'évaluation à valider",
            f"""Bonjour,

Une fiche d'évaluation de stage a été soumise par le service d'affectation pour le stagiaire : {nom_stagiaire}.

Connectez-vous au tableau de bord RH pour la consulter, l'accepter ou la refuser.

Cordialement,
Système Marsa Maroc Stagiaires
""",
            fichier_tag=f"rh_eval_{candidate_id}",
        )

        return jsonify(success=True, pdf_path=pdf_path)

    except Exception as exc:
        import traceback

        traceback.print_exc()
        return jsonify(success=False, error=str(exc)), 500
    
    

# ============================================================
# SUPERADMIN - GESTION DES UTILISATEURS
# ============================================================

SUPERADMIN_ROLES = (
    "stagiaire",
    "rh",
    "affectation",
   
)


def _admin_value(obj, key, default=None):
    """Lit une valeur depuis un objet Supabase ou un dict."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _admin_users_from_response(response):
    """
    Compatible avec plusieurs versions de supabase-py :
    - liste directe
    - objet avec .users
    - dict avec users
    """
    if isinstance(response, list):
        return response

    users = getattr(response, "users", None)
    if users is not None:
        return list(users)

    if isinstance(response, dict):
        if isinstance(response.get("users"), list):
            return response["users"]

        data = response.get("data")
        if isinstance(data, dict) and isinstance(data.get("users"), list):
            return data["users"]

    return []


def _admin_iso(value):
    if not value:
        return ""

    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass

    return str(value)


def _admin_user_banned(banned_until):
    """Retourne True uniquement si le bannissement est encore actif."""
    if not banned_until:
        return False

    try:
        if isinstance(banned_until, datetime):
            dt = banned_until
        else:
            dt = datetime.fromisoformat(
                str(banned_until).replace("Z", "+00:00")
            )

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt > datetime.now(timezone.utc)

    except Exception:
        return bool(banned_until)


def charger_utilisateurs_superadmin():
    if not supabase_admin:
        raise RuntimeError(
            "SUPABASE_SERVICE_ROLE_KEY n'est pas configurée."
        )

    # --------------------------------------------------------
    # 1. Charger les profils
    # --------------------------------------------------------
    profiles_response = (
        supabase_admin
        .table("profiles")
        .select("id,name,email,role")
        .execute()
    )

    profiles = profiles_response.data or []

    profiles_by_id = {
        str(profile.get("id")): profile
        for profile in profiles
        if profile.get("id")
    }

    # --------------------------------------------------------
    # 2. Charger tous les utilisateurs Supabase Auth
    # --------------------------------------------------------
    auth_users = []

    page = 1
    per_page = 1000

    while True:
        response = supabase_admin.auth.admin.list_users(
            page=page,
            per_page=per_page,
        )

        batch = _admin_users_from_response(response)

        auth_users.extend(batch)

        if len(batch) < per_page:
            break

        page += 1

        # Sécurité contre une boucle accidentelle
        if page > 50:
            break

    # --------------------------------------------------------
    # 3. Fusionner auth.users + profiles
    # --------------------------------------------------------
    resultat = []

    for auth_user in auth_users:

        user_id = str(_admin_value(auth_user, "id", ""))

        if not user_id:
            continue

        profile = profiles_by_id.get(user_id, {})

        metadata = (
            _admin_value(auth_user, "user_metadata", {})
            or {}
        )

        name = (
            profile.get("name")
            or metadata.get("full_name")
            or metadata.get("name")
            or ""
        )

        first_name = (
            metadata.get("first_name")
            or metadata.get("prenom")
            or ""
        )

        last_name = (
            metadata.get("last_name")
            or metadata.get("nom")
            or ""
        )

        # Anciens comptes : récupérer prénom/nom depuis profiles.name
        if not first_name and not last_name and name:
            morceaux = name.split(None, 1)

            first_name = morceaux[0]

            if len(morceaux) > 1:
                last_name = morceaux[1]

        role = (
            profile.get("role")
            or "stagiaire"
        ).strip().lower()

        email = (
            _admin_value(auth_user, "email", "")
            or profile.get("email")
            or ""
        )

        banned_until = _admin_value(
            auth_user,
            "banned_until",
            None
        )

        active = not _admin_user_banned(banned_until)

        resultat.append({
            "id": user_id,
            "name": name,
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "role": role,
            "active": active,
            "banned_until": _admin_iso(banned_until),
            "created_at": _admin_iso(
                _admin_value(auth_user, "created_at", None)
            ),
            "last_sign_in_at": _admin_iso(
                _admin_value(auth_user, "last_sign_in_at", None)
            ),
            "email_confirmed": bool(
                _admin_value(
                    auth_user,
                    "email_confirmed_at",
                    None
                )
            ),
        })

    resultat.sort(
        key=lambda u: u.get("created_at") or "",
        reverse=True,
    )

    return resultat


# ============================================================
# PAGE SUPERADMIN
# ============================================================

@app.route("/superadmin")
@login_required("superadmin")
def superadmin():

    try:
        users = charger_utilisateurs_superadmin()
        error = None

    except Exception as exc:
        print(f"[SUPERADMIN] Chargement utilisateurs : {exc}")

        users = []
        error = str(exc)

    stats = {
        "total": len(users),

        "stagiaire": sum(
            u["role"] == "stagiaire"
            for u in users
        ),

        "rh": sum(
            u["role"] == "rh"
            for u in users
        ),

        "affectation": sum(
            u["role"] == "affectation"
            for u in users
        ),

        "superadmin": sum(
            u["role"] == "superadmin"
            for u in users
        ),

        "inactive": sum(
            not u["active"]
            for u in users
        ),
    }

    return render_template(
        "dashboard_superadmin.html",
        user=nom_utilisateur(),
        users=users,
        stats=stats,
        error=error,
        current_user_id=str(session.get("user_id") or ""),
    )


# ============================================================
# CREATE USER
# ============================================================

@app.post("/api/superadmin/users")
@login_required("superadmin")
def superadmin_create_user():

    if not supabase_admin:
        return jsonify(
            success=False,
            error="Supabase Admin non configuré."
        ), 500

    data = request.get_json(silent=True) or {}

    first_name = (
        data.get("first_name") or ""
    ).strip()

    last_name = (
        data.get("last_name") or ""
    ).strip()

    email = (
        data.get("email") or ""
    ).strip().lower()

    role = (
        data.get("role") or ""
    ).strip().lower()
    if role == "superadmin":
        return jsonify(
            success=False,
            error="La création d'un autre Superadmin est interdite."
        ), 403

    password = data.get("password") or ""
    confirm_password = data.get("confirm_password") or ""

    if not first_name:
        return jsonify(
            success=False,
            error="Le prénom est obligatoire."
        ), 400

    if not last_name:
        return jsonify(
            success=False,
            error="Le nom est obligatoire."
        ), 400

    if not email:
        return jsonify(
            success=False,
            error="L'adresse email est obligatoire."
        ), 400

    if role not in SUPERADMIN_ROLES:
        return jsonify(
            success=False,
            error="Rôle invalide."
        ), 400

    if len(password) < 6:
        return jsonify(
            success=False,
            error="Le mot de passe doit contenir au moins 6 caractères."
        ), 400

    if password != confirm_password:
        return jsonify(
            success=False,
            error="Les mots de passe ne correspondent pas."
        ), 400

    full_name = f"{first_name} {last_name}".strip()

    created_user_id = None

    try:
        # Création dans Supabase Authentication
        auth_response = (
            supabase_admin
            .auth
            .admin
            .create_user({
                "email": email,
                "password": password,
                "email_confirm": True,
                "user_metadata": {
                    "first_name": first_name,
                    "last_name": last_name,
                    "full_name": full_name,
                },
            })
        )

        new_user = (
            getattr(auth_response, "user", None)
            or auth_response
        )

        created_user_id = str(
            _admin_value(new_user, "id", "")
        )

        if not created_user_id:
            raise RuntimeError(
                "Impossible de récupérer l'identifiant du nouvel utilisateur."
            )

        # profiles = source de vérité pour le rôle
        (
            supabase_admin
            .table("profiles")
            .upsert({
                "id": created_user_id,
                "name": full_name,
                "email": email,
                "role": role,
            })
            .execute()
        )

        return jsonify(
            success=True,
            message="Utilisateur créé avec succès."
        )

    except Exception as exc:

        print(f"[SUPERADMIN CREATE] {exc}")

        # Éviter un compte Auth orphelin si profiles échoue
        if created_user_id:
            try:
                supabase_admin.auth.admin.delete_user(
                    created_user_id
                )
            except Exception:
                pass

        return jsonify(
            success=False,
            error=str(exc)
        ), 500


# ============================================================
# UPDATE USER
# ============================================================
@app.put("/api/superadmin/users/<user_id>")
@login_required("superadmin")
def superadmin_update_user(user_id):

    if not supabase_admin:
        return jsonify(
            success=False,
            error="Supabase Admin non configuré."
        ), 500

    data = request.get_json(silent=True) or {}

    first_name = (
        data.get("first_name") or ""
    ).strip()

    last_name = (
        data.get("last_name") or ""
    ).strip()

    email = (
        data.get("email") or ""
    ).strip().lower()

    role = (
        data.get("role") or ""
    ).strip().lower()

    password = data.get("password") or ""
    confirm_password = data.get("confirm_password") or ""

    if not first_name or not last_name or not email:
        return jsonify(
            success=False,
            error="Prénom, nom et email sont obligatoires."
        ), 400

    current_user_id = str(
        session.get("user_id") or ""
    )

    # Lui-même = reste Superadmin
    if user_id == current_user_id:
        role = "superadmin"

    # Quelqu'un d'autre = jamais Superadmin
    elif role == "superadmin":
        return jsonify(
            success=False,
            error="Un utilisateur ne peut pas être promu Superadmin."
        ), 403

    elif role not in SUPERADMIN_ROLES:
        return jsonify(
            success=False,
            error="Rôle invalide."
        ), 400
    current_user_id = str(
        session.get("user_id") or ""
    )

    # Le Superadmin connecté ne peut pas retirer son propre rôle.
    

    if password:
        if len(password) < 6:
            return jsonify(
                success=False,
                error="Le mot de passe doit contenir au moins 6 caractères."
            ), 400

        if password != confirm_password:
            return jsonify(
                success=False,
                error="Les mots de passe ne correspondent pas."
            ), 400

    full_name = f"{first_name} {last_name}".strip()

    try:

        # Récupérer les métadonnées existantes
        response = (
            supabase_admin
            .auth
            .admin
            .get_user_by_id(user_id)
        )

        auth_user = (
            getattr(response, "user", None)
            or response
        )

        metadata = dict(
            _admin_value(
                auth_user,
                "user_metadata",
                {}
            ) or {}
        )

        metadata.update({
            "first_name": first_name,
            "last_name": last_name,
            "full_name": full_name,
        })

        auth_update = {
            "email": email,
            "user_metadata": metadata,
        }

        if password:
            auth_update["password"] = password

        # Modifier Authentication
        supabase_admin.auth.admin.update_user_by_id(
            user_id,
            auth_update,
        )

        # Modifier profiles
        (
            supabase_admin
            .table("profiles")
            .upsert({
                "id": user_id,
                "name": full_name,
                "email": email,
                "role": role,
            })
            .execute()
        )

        # Si le Superadmin modifie son propre nom/email,
        # mettre également sa session Flask à jour.
        if user_id == current_user_id:
            session["user_name"] = full_name
            session["user_email"] = email

        return jsonify(
            success=True,
            message="Utilisateur modifié avec succès."
        )

    except Exception as exc:

        print(f"[SUPERADMIN UPDATE] {exc}")

        return jsonify(
            success=False,
            error=str(exc)
        ), 500


# ============================================================
# ENABLE / DISABLE USER
# ============================================================

@app.post("/api/superadmin/users/<user_id>/status")
@login_required("superadmin")
def superadmin_user_status(user_id):

    if not supabase_admin:
        return jsonify(
            success=False,
            error="Supabase Admin non configuré."
        ), 500

    data = request.get_json(silent=True) or {}

    enabled = bool(
        data.get("enabled")
    )

    current_user_id = str(
        session.get("user_id") or ""
    )

    if user_id == current_user_id and not enabled:
        return jsonify(
            success=False,
            error="Vous ne pouvez pas désactiver votre propre compte."
        ), 400

    try:

        supabase_admin.auth.admin.update_user_by_id(
            user_id,
            {
                "ban_duration": (
                    "none"
                    if enabled
                    else "876000h"
                )
            },
        )

        return jsonify(
            success=True,
            active=enabled,
            message=(
                "Compte réactivé."
                if enabled
                else "Compte désactivé."
            )
        )

    except Exception as exc:

        print(f"[SUPERADMIN STATUS] {exc}")

        return jsonify(
            success=False,
            error=str(exc)
        ), 500


# ============================================================
# DELETE USER
# ============================================================

@app.delete("/api/superadmin/users/<user_id>")
@login_required("superadmin")
def superadmin_delete_user(user_id):

    if not supabase_admin:
        return jsonify(
            success=False,
            error="Supabase Admin non configuré."
        ), 500

    current_user_id = str(
        session.get("user_id") or ""
    )

    if user_id == current_user_id:
        return jsonify(
            success=False,
            error="Vous ne pouvez pas supprimer votre propre compte."
        ), 400

    try:

        # Supprimer d'abord Authentication.
        # Si une FK bloque la suppression, aucune donnée profile
        # n'est supprimée par erreur.
        supabase_admin.auth.admin.delete_user(
            user_id
        )

        # Si profiles possède ON DELETE CASCADE ceci ne fera rien.
        # Sinon cela nettoie le profil restant.
        try:
            (
                supabase_admin
                .table("profiles")
                .delete()
                .eq("id", user_id)
                .execute()
            )
        except Exception:
            pass

        return jsonify(
            success=True,
            message="Utilisateur supprimé."
        )

    except Exception as exc:

        print(f"[SUPERADMIN DELETE] {exc}")

        return jsonify(
            success=False,
            error=str(exc)
        ), 500




@app.post("/api/candidates/evaluation/valider")
@login_required("rh")
def api_candidates_evaluation_valider():
    """RH : accepte ou refuse la fiche d'évaluation. Si acceptée, génère l'attestation."""
    if not supabase:
        return jsonify(success=False, error="Supabase non configuré"), 500

    corps = request.get_json() or {}
    candidate_id = corps.get("id")
    decision = corps.get("decision")
    if not candidate_id or not decision:
        return jsonify(success=False, error="Paramètres manquants (id, decision)"), 400

    try:
        stagiaire_result = (
            supabase.table(TABLE_APPLICATIONS).select("*").eq("id", candidate_id).execute()
        )
        if not stagiaire_result.data:
            return jsonify(success=False, error="Stagiaire non trouvé"), 404

        stagiaire = stagiaire_result.data[0]
        candidat = normaliser_candidat(stagiaire)
        nom_stagiaire = candidat.get("name") or "Stagiaire"

        import datetime

        now_str = datetime.datetime.now().isoformat()
        update_data = {"evaluation_status": decision}


        if decision == "Accepté":

            notifier_nouveau_document_email(
                stagiaire,
                "Fiche d'évaluation de stage"
            )
            # =====================================================
            # La fiche d'évaluation est acceptée
            # MAIS aucune attestation n'est générée automatiquement.
            # Le RH devra uploader l'attestation manuellement.
            # =====================================================

            update_data.update(
                {
                    "attestation_pdf": None,
                    "attestation_generated_at": None,
                }
            )

            notif_text = (
                "Votre fiche d'évaluation a été acceptée par la RH. "
                "Votre attestation de stage sera mise à disposition prochainement."
            )

            email_sujet = "[Marsa Maroc] Fiche d'évaluation acceptée"

            email_corps = f"""Bonjour {nom_stagiaire},

            Votre fiche d'évaluation a été acceptée par la Direction des Ressources Humaines.

            Votre attestation de stage sera mise à disposition dans votre espace stagiaire
            après son dépôt par le service RH.

            Cordialement,
            La Direction des Ressources Humaines — Marsa Maroc
            """
            
        else:
            motif = (corps.get("reject_reason") or "").strip()
            if not motif:
                return jsonify(success=False, error="Le motif de refus est obligatoire"), 400

            update_data.update(
                {
                    "evaluation_pdf": None,
                    "evaluation_reject_reason": motif,
                }
            )
            notif_text = f"Votre fiche d'évaluation a été refusée par la RH. Motif : {motif}"
            email_sujet = "[Marsa Maroc] Fiche d'évaluation refusée"
            email_corps = f"""Bonjour {nom_stagiaire},

Votre fiche d'évaluation a été refusée par la Direction des Ressources Humaines.

Motif : {motif}

Votre encadrant pourra soumettre une nouvelle fiche après correction.

Cordialement,
La Direction des Ressources Humaines — Marsa Maroc
"""
            envoyer_email(
                EMAIL_SERVICE_AFFECTATION,
                "[Marsa Maroc] Fiche d'évaluation refusée — action requise",
                f"""Bonjour,

La fiche d'évaluation du stagiaire {nom_stagiaire} a été refusée par la RH.

Motif du refus :
{motif}

Veuillez corriger et soumettre une nouvelle fiche d'évaluation depuis le tableau de bord Affectation.

Cordialement,
Système Marsa Maroc Stagiaires
""",
                fichier_tag=f"aff_eval_refus_{candidate_id}",
            )

        update_data["notifications"] = ajouter_notification(stagiaire, notif_text)
        supabase_executer_update_eq(supabase, TABLE_APPLICATIONS, update_data, "id", candidate_id)

        candidate_email = stagiaire.get("email")
        if candidate_email:
            envoyer_email_stagiaire(candidate_id, candidate_email, email_sujet, email_corps)

        return jsonify(success=True, attestation_pdf=update_data.get("attestation_pdf"))

    except Exception as exc:
        import traceback

        traceback.print_exc()
        return jsonify(success=False, error=str(exc)), 500

@app.post("/api/candidates/attestation/upload")
@login_required("rh")
def api_upload_attestation():
    """
    RH :
    Upload manuel de l'attestation de stage après
    validation de la fiche d'évaluation.
    """

    if not supabase:
        return jsonify(
            success=False,
            error="Supabase non configuré"
        ), 500

    # =====================================================
    # 1. Vérifier le fichier
    # =====================================================

    if "file" not in request.files:
        return jsonify(
            success=False,
            error="Aucun fichier fourni"
        ), 400

    file = request.files["file"]

    candidate_id = (
        request.form.get("candidate_id")
        or request.form.get("id")
    )

    if not candidate_id:
        return jsonify(
            success=False,
            error="ID du stagiaire manquant"
        ), 400

    if not file or file.filename == "":
        return jsonify(
            success=False,
            error="Aucun fichier sélectionné"
        ), 400

    if not file.filename.lower().endswith(".pdf"):
        return jsonify(
            success=False,
            error="L'attestation doit être un fichier PDF"
        ), 400

    try:

        # =====================================================
        # 2. Charger le stagiaire
        # =====================================================

        result = (
            supabase
            .table(TABLE_APPLICATIONS)
            .select("*")
            .eq("id", candidate_id)
            .limit(1)
            .execute()
        )

        if not result.data:
            return jsonify(
                success=False,
                error="Stagiaire non trouvé"
            ), 404

        stagiaire = result.data[0]
        candidat = normaliser_candidat(stagiaire)

        # =====================================================
        # 3. Vérifier que la fiche d'évaluation est acceptée
        # =====================================================

        if candidat.get("evaluation_status") != "Accepté":
            return jsonify(
                success=False,
                error=(
                    "La fiche d'évaluation doit être acceptée "
                    "avant de déposer l'attestation."
                )
            ), 403

        # =====================================================
        # 4. Dossier de destination
        # =====================================================

        output_dir = app.config["GENERATED_PDFS_FOLDER"]

        os.makedirs(
            output_dir,
            exist_ok=True
        )

        # =====================================================
        # 5. Nom du fichier
        # =====================================================

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        pdf_filename = (
            f"attestation_{candidate_id}_{timestamp}.pdf"
        )

        pdf_path = os.path.join(
            output_dir,
            pdf_filename
        )

        # =====================================================
        # 6. Sauvegarder le PDF envoyé par le RH
        # =====================================================

        file.save(pdf_path)

        if not os.path.exists(pdf_path):
            return jsonify(
                success=False,
                error="Erreur lors de l'enregistrement du PDF"
            ), 500

        # =====================================================
        # 7. Notification stagiaire
        # =====================================================

        notifications = ajouter_notification(
            stagiaire,
            (
                "Votre attestation de stage officielle "
                "est maintenant disponible."
            )
        )

        # =====================================================
        # 8. Sauvegarder dans Supabase
        # =====================================================

        update_payload = {
            "attestation_pdf": pdf_filename,
            "attestation_status": "Généré",
            "attestation_generated_at":
                datetime.now(timezone.utc).isoformat(),
            "notifications": notifications,
        }

        supabase_executer_update_eq(
            supabase,
            TABLE_APPLICATIONS,
            update_payload,
            "id",
            candidate_id
        )

        # =====================================================
        # 9. Envoyer un email au stagiaire
        # =====================================================

        candidate_email = stagiaire.get("email")

        nom_stagiaire = (
            candidat.get("name")
            or "Stagiaire"
        )

        if candidate_email:

            envoyer_email_stagiaire(
                candidate_id,
                candidate_email,
                "[Marsa Maroc] Attestation de stage disponible",
                f"""Bonjour {nom_stagiaire},

Votre attestation de stage officielle est maintenant disponible.

Vous pouvez la consulter et la télécharger depuis votre espace stagiaire.

Cordialement,
La Direction des Ressources Humaines — Marsa Maroc
"""
            )

        print(
            f"[ATTESTATION] PDF uploadé par RH : {pdf_filename}"
        )

        return jsonify(
            success=True,
            attestation_pdf=pdf_filename,
            message="Attestation déposée avec succès."
        )

    except Exception as exc:

        import traceback
        traceback.print_exc()

        return jsonify(
            success=False,
            error=str(exc)
        ), 500

@app.route("/download/fiche_accueil/<path:filename>")
def download_fiche_accueil(filename):
    filepath = trouver_pdf_genere(filename)

    if not filepath:
        return "Fiche d'accueil introuvable.", 404

    return send_file(
        filepath,
        mimetype="application/pdf",
        as_attachment=True
    )


@app.route("/preview/fiche_accueil/<path:filename>")
def preview_fiche_accueil(filename):
    filepath = trouver_pdf_genere(filename)

    if not filepath:
        return "Fiche d'accueil introuvable.", 404

    return send_file(
        filepath,
        mimetype="application/pdf",
        as_attachment=False
    )


@app.route("/preview/evaluation/<path:filename>")
def preview_evaluation(filename):
    return _servir_evaluation_pdf(filename, as_attachment=False)


@app.route("/download/evaluation/<path:filename>")
def download_evaluation(filename):
    return _servir_evaluation_pdf(filename, as_attachment=True)


def trouver_pdf_genere(filename):
    """Cherche un PDF généré dans les emplacements possibles."""
    safe_filename = secure_filename(os.path.basename(filename))

    chemins = [
        # Nouveau dossier recommandé
        os.path.join(STORAGE_DIR, "generated_pdfs", safe_filename),

        # Ancien dossier à la racine du projet
        os.path.join(os.getcwd(), "generated_pdfs", safe_filename),

        # Ancien dossier backend/generated_pdfs
        os.path.join(app.root_path, "generated_pdfs", safe_filename),
    ]

    for filepath in chemins:
        if os.path.isfile(filepath):
            return filepath

    print("[PDF] Introuvable :", safe_filename)
    print("[PDF] Chemins testés :")
    for filepath in chemins:
        print("   -", filepath)

    return None



@app.route("/download/attestation/<path:filename>")
def download_attestation(filename):
    """Télécharger l'attestation de stage PDF from generated_pdfs directory."""
    try:
        base_filename = os.path.basename(filename)
        return send_file(
            os.path.join(app.config['GENERATED_PDFS_FOLDER'], base_filename),
            as_attachment=True,
            mimetype="application/pdf"
        )
    except Exception as exc:
        return f"Erreur lors du téléchargement: {str(exc)}", 404


@app.route("/pdf/<path:filename>")
def serve_pdf(filename):
    """View/Download any PDF from pdf/ or generated_pdfs/."""
    try:
        # Prevent path traversal
        base_filename = os.path.basename(filename)
        # Check pdf directory first
        path_pdf = os.path.join(app.config['PDF_TEMPLATES_FOLDER'], base_filename)
        if os.path.exists(path_pdf):
            return send_file(path_pdf, mimetype="application/pdf")
        # Check generated_pdfs directory
        path_gen = os.path.join(app.config['GENERATED_PDFS_FOLDER'], base_filename)
        if os.path.exists(path_gen):
            return send_file(path_gen, mimetype="application/pdf")
        
        # Check with space fallback (like "Evaluation stage .pdf")
        path_pdf_space = os.path.join(app.config['PDF_TEMPLATES_FOLDER'], base_filename + " ")
        if os.path.exists(path_pdf_space):
            return send_file(path_pdf_space, mimetype="application/pdf")
            
        return "Fichier non trouvé", 404
    except Exception as exc:
        return f"Erreur lors du chargement: {str(exc)}", 500



@app.post("/api/submit-dossier")
@login_required("stagiaire")
def api_submit_dossier():
    """Transmet le dossier complet au RH (après 5 PDF)."""
    if not supabase:
        return jsonify(success=False, error="Supabase non configuré"), 500

    candidat, _ = charger_candidature_utilisateur()
    if not candidat:
        return jsonify(success=False, error="Aucune candidature trouvée."), 404

    cid = str(candidat["id"])
    if not tous_documents_presents(cid):
        return jsonify(
            success=False,
            error="Tous les documents PDF sont requis avant l'envoi au RH.",
        ), 400

    try:
        supabase_executer_update_eq(
            supabase,
            TABLE_APPLICATIONS,
            {
                "dossier_submitted": True,
                "submitted_to_rh_at": datetime.now(timezone.utc).isoformat(),
                "status": STATUT_INITIAL_DB,
                "rh_status_hint": "",
            },
            "id",
            cid,
        )
        session["dossier_soumis_id"] = cid
        return jsonify(success=True, message="Dossier transmis au RH.")
    except Exception as exc:
        print(f"[SUBMIT-DOSSIER] Erreur: {exc}")
        return jsonify(success=False, error=message_erreur_supabase(exc)), 500


@app.post("/api/notifications/read")
@login_required("stagiaire")
def api_notifications_read():
    """Marque toutes les notifications du stagiaire connecté comme lues."""
    if not supabase:
        return jsonify(success=False, error="Supabase non configuré"), 500

    candidat, _ = charger_candidature_utilisateur()
    if not candidat:
        return jsonify(success=False, error="Aucune candidature trouvée."), 404

    try:
        notifications = candidat.get("notifications") or []
        for n in notifications:
            n["read"] = True

        supabase.table(TABLE_APPLICATIONS).update({
            "notifications": notifications
        }).eq("id", candidat["id"]).execute()

        return jsonify(success=True)
    except Exception as exc:
        print(f"[NOTIF-READ] Erreur: {exc}")
        return jsonify(success=False, error=str(exc)), 500



@app.post("/api/upload")
@login_required("stagiaire")
def api_upload():
    if "file" not in request.files:
        return jsonify(success=False, error="Aucun fichier fourni"), 400

    file = request.files["file"]
    doc_type = request.form.get("type")
    candidate_id = request.form.get("candidate_id")

    if doc_type not in DOCUMENTS_REQUIS:
        return jsonify(success=False, error="Type de document invalide"), 400

    candidat, _ = charger_candidature_utilisateur()
    if not candidat and candidate_id:
        candidat = charger_candidature_par_id(str(candidate_id))

    if not candidat:
        return jsonify(
            success=False,
            error="Candidature introuvable. Validez d'abord le formulaire, puis réessayez.",
        ), 404

    if not candidature_appartient_session(candidat):
        return jsonify(success=False, error="Accès non autorisé à cette candidature."), 403

    candidate_id = str(candidat["id"])
    session["candidature_id"] = candidate_id

    if file.filename == "":
        return jsonify(success=False, error="Fichier vide"), 400

    if candidature_soumise_au_rh(candidat):
        statut = candidat.get("status_db") or ""
        demande = (candidat.get("requested_doc_type") or "").strip()
        if statut != "action_required" or not demande:
            return jsonify(
                success=False,
                error="Aucune demande de document en cours. Contactez le RH.",
            ), 400
        if doc_type != demande:
            return jsonify(
                success=False,
                error=f"Le RH a demandé uniquement : {DOC_LABELS.get(demande, demande)}",
            ), 400
        return _reupload_document_interne(file, doc_type, candidate_id, candidat)

    if file.filename.lower().endswith(".pdf"):
        filename = f"{candidate_id}_{doc_type}.pdf"
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)
        docs = documents_uploades(candidate_id)

        # Envoi automatique au RH dès que les 5 PDF sont présents (sans attendre le bouton)
        auto_submitted = False
        if all(docs[d]["uploaded"] for d in DOCUMENTS_REQUIS):
            try:
                supabase_executer_update_eq(
                    supabase,
                    TABLE_APPLICATIONS,
                    {
                        "dossier_submitted": True,
                        "submitted_to_rh_at": datetime.now(timezone.utc).isoformat(),
                        "status": STATUT_INITIAL_DB,
                        "rh_status_hint": "",
                    },
                    "id",
                    candidate_id,
                )
                session["dossier_soumis_id"] = candidate_id
                auto_submitted = True
            except Exception as exc:
                # Si colonnes absentes, on reste en mode dégradé (RH verra quand même via PDFs)
                print(f"[UPLOAD] Auto-submit RH impossible: {exc}")

        return jsonify(success=True, documents=docs, auto_submitted=auto_submitted)

    return jsonify(success=False, error="Seuls les fichiers PDF sont autorisés"), 400


def _reupload_document_interne(file, doc_type: str, candidate_id: str, candidat: dict):
    """Re-téléversement depuis le dashboard (action RH)."""
    if not file.filename.lower().endswith(".pdf"):
        return jsonify(success=False, error="Seuls les fichiers PDF sont autorisés"), 400

    statut_avant = candidat.get("status_db") or "pending"
    filename = f"{candidate_id}_{doc_type}.pdf"
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    # Sous-message RH : En attente + 📩 ou (si encore action_required) + 📄
    if statut_avant == "action_required":
        hint = HINT_NOUVEAU_DOCUMENT
    else:
        hint = HINT_PDF_RENVOYE

    try:
        supabase_executer_update_eq(
            supabase,
            TABLE_APPLICATIONS,
            {
                "remark": "",
                "requested_doc_type": None,
                "status": STATUT_INITIAL_DB,
                "rh_status_hint": hint,
            },
            "id",
            candidate_id,
        )
        return jsonify(
            success=True,
            status=statut_pour_affichage(STATUT_INITIAL_DB),
            message="Document envoyé. Votre dossier est de nouveau en attente de validation RH.",
        )
    except Exception as exc:
        return jsonify(success=False, error=str(exc)), 500


@app.route("/api/candidates/<candidate_id>/documents")
@login_required("rh")
def get_candidate_documents(candidate_id):

    docs = [
        "cv",
        "cin",
        "assurance",
        "convention",
        "demande",
    ]

    result = {}

    # Récupérer les validations RH
    validated_documents = {}

    try:
        response = (
            supabase
            .table(TABLE_APPLICATIONS)
            .select("validated_documents")
            .eq("id", candidate_id)
            .single()
            .execute()
        )

        if response.data:
            validated_documents = (
                response.data.get("validated_documents")
                or {}
            )

    except Exception as exc:
        print("[DOCUMENTS VALIDATION]", exc)

    # Vérifier les PDF
    for doc in docs:

        filename = f"{candidate_id}_{doc}.pdf"

        filepath = os.path.join(
            app.config["UPLOAD_FOLDER"],
            filename
        )

        exists = os.path.exists(filepath)

        if not exists:

            fallback_filename = (
                f"{secure_filename(candidate_id)}_{doc}.pdf"
            )

            filepath = os.path.join(
                app.config["UPLOAD_FOLDER"],
                fallback_filename
            )

            exists = os.path.exists(filepath)

        result[doc] = {

            "uploaded": exists,

            "validated": bool(
                validated_documents.get(doc)
            ),

            "url": (
                f"/api/documents/{candidate_id}/{doc}"
                if exists
                else None
            ),

            "download_url": (
                f"/api/documents/{candidate_id}/{doc}/download"
                if exists
                else None
            ),
        }

    return jsonify(
        success=True,
        documents=result
    )



@app.route("/api/documents/<candidate_id>/<doc_type>")
def get_document(candidate_id, doc_type):
    filename = f"{candidate_id}_{doc_type}.pdf"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    if not os.path.exists(filepath):
        fallback_filename = f"{secure_filename(candidate_id)}_{doc_type}.pdf"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], fallback_filename)
        
    if os.path.exists(filepath):
        return send_file(filepath, mimetype='application/pdf', as_attachment=False)
    
    return jsonify(success=False, error="Fichier non trouvé"), 404


@app.route("/api/documents/<candidate_id>/<doc_type>/download")
def download_document(candidate_id, doc_type):
    filename = f"{candidate_id}_{doc_type}.pdf"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    if not os.path.exists(filepath):
        fallback_filename = f"{secure_filename(candidate_id)}_{doc_type}.pdf"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], fallback_filename)
        
    if os.path.exists(filepath):
        return send_file(filepath, mimetype='application/pdf', as_attachment=True, download_name=filename)
    
    return jsonify(success=False, error="Fichier non trouvé"), 404


@app.post("/request-documents")
def request_documents():
    if not supabase:
        return jsonify(success=False, error="Supabase non configuré"), 500

    corps = request.get_json() or {}
    candidate_id = corps.get("id")
    doc_type = corps.get("doc_type")
    remark = corps.get("remark")

    if not candidate_id or not doc_type or not remark:
        return jsonify(success=False, error="Paramètres manquants (id, doc_type, remark)"), 400

    if doc_type not in DOCUMENTS_REQUIS:
        return jsonify(success=False, error="Type de document invalide"), 400

    try:
        reponse = (
            supabase.table(TABLE_APPLICATIONS)
            .select("name, email")
            .eq("id", candidate_id)
            .single()
            .execute()
        )
        candidat = reponse.data
        if not candidat:
            return jsonify(success=False, error="Candidat non trouvé"), 404

        candidate_name = candidat.get("name")
        candidate_email = candidat.get("email") or ""

        supabase.table(TABLE_APPLICATIONS).update(
            {
                "remark": remark,
                "requested_doc_type": doc_type,
                "status": "action_required",
                "rh_status_hint": "",
            }
        ).eq("id", candidate_id).execute()

        doc_label = DOC_LABELS.get(doc_type, doc_type.upper())
        app_url = os.getenv("APP_URL", "http://127.0.0.1:5000")
        lien_dashboard = f"{app_url}/stagiaire"

        subject = "Dossier incomplet — action requise | Marsa Maroc"
        body = f"""Bonjour {candidate_name or 'Stagiaire'},

Votre dossier nécessite une action de votre part.

Document manquant : {doc_label}

Message du service RH :
« {remark} »

Connectez-vous à votre espace stagiaire pour téléverser uniquement le document demandé :
{lien_dashboard}

---
Direction du Capital Humain
Marsa Maroc
"""

        if candidate_email:
            envoyer_email_stagiaire(candidate_id, candidate_email, subject, body)
        else:
            print(f"[RH] Pas d'email pour candidat {candidate_id} — notification dashboard uniquement")

        return jsonify(success=True)

    except Exception as exc:
        print(f"[RH] Erreur request-documents: {exc}")
        return jsonify(success=False, error=str(exc)), 500


@app.post("/reupload-document")
@login_required("stagiaire")
def reupload_document():
    """Alias pour re-téléversement depuis le dashboard stagiaire."""
    if not supabase:
        return jsonify(success=False, error="Supabase non configuré"), 500

    if "file" not in request.files:
        return jsonify(success=False, error="Aucun fichier fourni"), 400

    file = request.files["file"]
    doc_type = request.form.get("type")

    if doc_type not in DOCUMENTS_REQUIS:
        return jsonify(success=False, error="Type de document invalide"), 400

    candidat, _ = charger_candidature_utilisateur()
    if not candidat:
        return jsonify(success=False, error="Candidature introuvable"), 404

    demande = (candidat.get("requested_doc_type") or "").strip()
    if candidat.get("status_db") != "action_required" or not demande:
        return jsonify(success=False, error="Aucune demande RH en cours pour ce document."), 400
    if doc_type != demande:
        return jsonify(
            success=False,
            error=f"Document attendu : {DOC_LABELS.get(demande, demande)}",
        ), 400

    return _reupload_document_interne(file, doc_type, str(candidat["id"]), candidat)


@app.route("/completer/<candidate_id>")
def completer_dossier(candidate_id):
    if not supabase:
        return "Supabase non configuré.", 500

    try:
        reponse = supabase.table(TABLE_APPLICATIONS).select("*").eq("id", candidate_id).single().execute()
        candidat = reponse.data
        if not candidat:
            return "Candidat non trouvé.", 404

        candidat_normalise = normaliser_candidat(candidat)

        return render_template(
            "completer.html",
            candidate=candidat_normalise,
            doc_labels=DOC_LABELS
        )
    except Exception as exc:
        print(f"[COMPLETER] Erreur chargement: {exc}")
        return f"Erreur lors du chargement du dossier : {exc}", 500


# ==========================================
# CHAT & REPORT ENDPOINTS (AFFECTATION / STAGIAIRE)
# ==========================================

@app.post("/api/chat/send")
def api_chat_send():
    if not supabase:
        return jsonify(success=False, error="Supabase non configuré"), 500
    
    corps = request.get_json() or {}
    candidate_id = corps.get("candidate_id")
    text = (corps.get("text") or "").strip()
    sender = corps.get("sender")  # "affectation" or "stagiaire"
    
    if not candidate_id or not text or not sender:
        return jsonify(success=False, error="Paramètres manquants (candidate_id, text, sender)"), 400
        
    try:
        # Charger le stagiaire
        res = supabase.table(TABLE_APPLICATIONS).select("chat_messages").eq("id", candidate_id).single().execute()
        if not res.data:
            return jsonify(success=False, error="Stagiaire non trouvé"), 404
            
        chat_messages = res.data.get("chat_messages") or []
        if not isinstance(chat_messages, list):
            chat_messages = []
            
        new_msg = {
            "id": f"msg_{int(datetime.now().timestamp())}",
            "text": text,
            "sender": sender,
            "date": datetime.now().isoformat()
        }
        chat_messages.append(new_msg)
        
        # Mettre à jour Supabase
        update_payload = {"chat_messages": chat_messages}
        supabase_executer_update_eq(supabase, TABLE_APPLICATIONS, update_payload, "id", candidate_id)
        
        return jsonify(success=True, messages=chat_messages)
    except Exception as exc:
        return jsonify(success=False, error=str(exc)), 500


@app.get("/api/chat/messages/<candidate_id>")
def api_chat_messages(candidate_id):
    if not supabase:
        return jsonify(success=False, error="Supabase non configuré"), 500
        
    try:
        res = supabase.table(TABLE_APPLICATIONS).select("chat_messages").eq("id", candidate_id).single().execute()
        if not res.data:
            return jsonify(success=False, error="Stagiaire non trouvé"), 404
            
        chat_messages = res.data.get("chat_messages") or []
        return jsonify(success=True, messages=chat_messages)
    except Exception as exc:
        return jsonify(success=False, error=str(exc)), 500


@app.post("/api/report/upload")
@login_required("stagiaire")
def api_report_upload():
    if not supabase:
        return jsonify(success=False, error="Supabase non configuré"), 500

    if "file" not in request.files:
        return jsonify(success=False, error="Aucun fichier fourni"), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify(success=False, error="Fichier vide"), 400

    candidat, _ = charger_candidature_utilisateur()
    if not candidat:
        return jsonify(success=False, error="Candidature introuvable"), 404

    if candidat.get("status") != "Accepté":
        return jsonify(
            success=False,
            error="Le rapport de stage est disponible uniquement après acceptation de la candidature.",
        ), 403
        
    # Le rapport ne peut être déposé qu'après affectation
    if not candidat.get("est_affecte"):
        return jsonify(
            success=False,
            error=(
                "Vous devez d'abord être affecté par le service d'affectation "
                "avant de pouvoir déposer votre rapport de stage."
            ),
        ), 403

    # ============================================================
    # LE RAPPORT N'EST DISPONIBLE QU'APRÈS LA DÉCISION DE STAGE
    # ============================================================

    if not candidat.get("decision_pdf"):

        return jsonify(
            success=False,
            error=(
                "Vous ne pouvez pas encore déposer votre rapport de stage. "
                "La décision de stage doit d'abord être générée par la RH."
            )
        ), 403




    candidate_id = str(candidat["id"])
    
    

    if not file.filename.lower().endswith(".pdf"):
        return jsonify(success=False, error="Seuls les fichiers PDF sont acceptés"), 400

    try:
        filename = f"{candidate_id}_report.pdf"
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

        nom = normaliser_candidat(candidat).get("name") or "Stagiaire"
        update_payload = {
            "intern_report_path": filename,
            "intern_report_status": "En attente",
            "notifications": ajouter_notification(
                candidat,
                "Votre rapport de stage a été déposé. En attente de validation par l'affectation.",
            ),
        }
        supabase_executer_update_eq(supabase, TABLE_APPLICATIONS, update_payload, "id", candidate_id)

        candidate_email = candidat.get("email")
        if candidate_email:
            envoyer_email_stagiaire(
                candidate_id,
                candidate_email,
                "[Marsa Maroc] Rapport de stage reçu",
                f"""Bonjour {nom},

Votre rapport de stage a bien été reçu et est en cours de validation par le service d'affectation.

Cordialement,
Le Service d'Affectation — Marsa Maroc
""",
            )

        envoyer_email(
            EMAIL_SERVICE_AFFECTATION,
            "[Marsa Maroc] Nouveau rapport de stage",
            f"""Bonjour,

Le stagiaire {nom} a déposé son rapport de stage (PDF).
Connectez-vous au tableau de bord Affectation pour le consulter et le valider.

Cordialement,
Système Marsa Maroc Stagiaires
""",
            fichier_tag=f"aff_report_{candidate_id}",
        )

        return jsonify(success=True, path=filename)
    except Exception as exc:
        return jsonify(success=False, error=str(exc)), 500


@app.post("/api/report/validate")
@login_required("affectation")
def api_report_validate():
    """Affectation : valide le rapport de stage du stagiaire."""
    if not supabase:
        return jsonify(success=False, error="Supabase non configuré"), 500

    corps = request.get_json() or {}
    candidate_id = corps.get("id")
    if not candidate_id:
        return jsonify(success=False, error="ID du candidat manquant"), 400

    try:
        res = supabase.table(TABLE_APPLICATIONS).select("*").eq("id", candidate_id).execute()
        if not res.data:
            return jsonify(success=False, error="Stagiaire non trouvé"), 404

        stagiaire = res.data[0]
        candidat = normaliser_candidat(stagiaire)

        if not candidat.get("intern_report_path"):
            return jsonify(success=False, error="Aucun rapport déposé par ce stagiaire"), 400

        if candidat.get("intern_report_status") == "Validé":
            return jsonify(success=True, message="Rapport déjà validé")

        update_payload = {
            "intern_report_status": "Validé",
            "notifications": ajouter_notification(
                stagiaire,
                "Votre rapport de stage a été validé par l'affectation. Votre encadrant pourra établir la fiche d'évaluation.",
            ),
        }
        supabase_executer_update_eq(supabase, TABLE_APPLICATIONS, update_payload, "id", candidate_id)

        email_stagiaire = stagiaire.get("email")
        if email_stagiaire:
            envoyer_email_stagiaire(
                candidate_id,
                email_stagiaire,
                "[Marsa Maroc] Rapport de stage validé",
                f"""Bonjour {candidat.get('name') or 'Stagiaire'},

Votre rapport de stage a été validé par le service d'affectation.

Cordialement,
Le Service d'Affectation — Marsa Maroc
""",
            )

        return jsonify(success=True)
    except Exception as exc:
        return jsonify(success=False, error=str(exc)), 500


@app.route("/download/report/<path:filename>")
def download_report(filename):
    return _servir_rapport_stage(filename, as_attachment=True)


@app.route("/preview/report/<path:filename>")
def preview_report(filename):
    return _servir_rapport_stage(filename, as_attachment=False)






def _servir_rapport_stage(filename: str, as_attachment: bool):
    safe_filename = secure_filename(os.path.basename(filename))
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], safe_filename)
    if not os.path.exists(filepath):
        return "Fichier de rapport introuvable.", 404

    if not supabase:
        return "Accès au rapport indisponible.", 503

    try:
        result = (
            supabase.table(TABLE_APPLICATIONS)
            .select("status")
            .eq("intern_report_path", safe_filename)
            .maybe_single()
            .execute()
        )
        candidate = normaliser_candidat(result.data) if result.data else None
        if not candidate or candidate.get("status") != "Accepté":
            return "Le rapport n'est disponible qu'après acceptation de la candidature.", 403
    except Exception as exc:
        print(f"[REPORT] Erreur contrôle accès: {exc}")
        return "Accès au rapport indisponible.", 503

    return send_file(filepath, mimetype="application/pdf", as_attachment=as_attachment)



def _servir_evaluation_pdf(filename: str, as_attachment: bool):
    filepath = trouver_pdf_genere(filename)

    if not filepath:
        return "Fiche d'appréciation introuvable.", 404

    return send_file(
        filepath,
        mimetype="application/pdf",
        as_attachment=as_attachment
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
