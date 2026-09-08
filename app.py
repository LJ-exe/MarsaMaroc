import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from pdfrw import PdfReader, PdfWriter

load_dotenv()
load_dotenv('.env.local', override=True)

from flask import Flask, jsonify, redirect, render_template, request, send_file, session, url_for
from werkzeug.utils import secure_filename

from auth_helpers import (
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
from db_config import (
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
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "marsa-maroc-dev-secret-changez-moi")

UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

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

        # Rapport de stage
        ligne["intern_report_path"] = c.get("intern_report_path")
        ligne["intern_report_status"] = c.get("intern_report_status") or ""

        # Fiche d'évaluation
        ligne["evaluation_pdf"] = c.get("evaluation_pdf")
        ligne["evaluation_status"] = c.get("evaluation_status") or ""
        ligne["evaluation_submitted_at"] = c.get("evaluation_submitted_at")
        ligne["evaluation_reject_reason"] = c.get("evaluation_reject_reason")

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
            from auth_helpers import rafraichir_token_si_expire
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


def ajouter_notification(candidat: dict, texte: str) -> list:
    """Ajoute une notification in-app au tableau notifications du stagiaire."""
    import datetime as dt

    now_str = dt.datetime.now().isoformat()
    notifications = candidat.get("notifications") or []
    if not isinstance(notifications, list):
        notifications = []
    notifications.append(
        {
            "id": f"notif_{int(dt.datetime.now().timestamp())}",
            "text": texte,
            "date": now_str,
            "read": False,
        }
    )
    return notifications


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
            from auth_helpers import rafraichir_token_si_expire
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
            "Exécutez le fichier supabase_stagiaire_dashboard.sql dans le SQL Editor, "
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
        output_dir = os.path.join(app.root_path, 'generated_pdfs')
        os.makedirs(output_dir, exist_ok=True)

        # Path to the original PDF template (absolute for safety)
        base_dir = os.path.dirname(os.path.abspath(__file__))
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
        
        # Type of stage - checkboxes instead of text
        # 1.5 Dynamically detect checkbox positions from the template PDF using PyMuPDF (fitz)
        detected_boxes = []
        try:
            import fitz
            doc_temp = fitz.open(template_path)
            page_temp = doc_temp[0]
            h_page_temp = page_temp.rect.height
            
            # Find the Y position of the "Type de Stage" section by locating the word "Passage"
            words = page_temp.get_text("words")
            type_stage_y = None
            for w in words:
                if "passage" in w[4].lower() or "altern" in w[4].lower():
                    type_stage_y = w[1] # top coordinate of the text
                    break
            if type_stage_y is None:
                type_stage_y = 324.87
                
            # Get drawings and filter vertical lines near this Y
            drawings_temp = page_temp.get_drawings()
            v_lines = []
            for d in drawings_temp:
                r = d['rect']
                if abs(r.y0 - type_stage_y) < 15 and 8 <= r.height <= 15 and r.width < 1.5:
                    if 50 <= r.x0 <= 550:
                        v_lines.append(r)
            
            # Sort vertical lines by X coordinate
            v_lines.sort(key=lambda r: r.x0)
            
            # Group into pairs to form boxes
            i = 0
            while i < len(v_lines) - 1:
                l1 = v_lines[i]
                l2 = v_lines[i+1]
                dist = l2.x0 - l1.x0
                if 15 <= dist <= 40:
                    x = l1.x0
                    y = min(l1.y0, l2.y0)
                    width = dist
                    height = max(l1.height, l2.height)
                    
                    # Convert to ReportLab bottom-up coordinates
                    rl_x = x
                    rl_y = h_page_temp - (y + height)
                    
                    detected_boxes.append({
                        'x': rl_x,
                        'y': rl_y,
                        'width': width,
                        'height': height
                    })
                    i += 2
                else:
                    i += 1
            doc_temp.close()
        except Exception as e:
            print(f"[PDF] Checkbox detection error: {e}")

        # Fallback coordinates (in ReportLab system) if detection failed
        fallback_centers = [
            (242.33, 511.27),
            (344.41, 511.27),
            (505.84, 511.27)
        ]
        
        box_centers = []
        if len(detected_boxes) >= 3:
            for box in detected_boxes[:3]:
                cx = box['x'] + box['width'] / 2
                cy = box['y'] + box['height'] / 2
                box_centers.append((cx, cy))
            print(f"[PDF] Dynamically detected centers: {box_centers}")
        else:
            box_centers = fallback_centers
            print(f"[PDF] Using fallback centers (detection failed or incomplete): {box_centers}")

        type_lower = type_stage.lower() if type_stage else ''
        print(f"[CHECKBOX] Type stage value: '{type_stage}', lower: '{type_lower}'")
        
        selected_idx = 0
        if 'altern' in type_lower:
            selected_idx = 1
        elif 'pfa' in type_lower or 'fin' in type_lower:
            selected_idx = 2
            
        target_center_x, target_center_y = box_centers[selected_idx]
        print(f"[CHECKBOX] Selected index: {selected_idx}, drawing cross at center X={target_center_x}, Y={target_center_y}")
        draw_checkbox_cross(c, target_center_x, target_center_y, size=8)
        
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
        output_dir = os.path.join(os.getcwd(), 'generated_pdfs')
        os.makedirs(output_dir, exist_ok=True)

        base_dir = os.path.dirname(os.path.abspath(__file__))
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

        nombres = {
            1: "un",
            2: "deux",
            3: "trois",
            4: "quatre",
            5: "cinq",
            6: "six",
            7: "sept",
            8: "huit",
            9: "neuf",
            10: "dix",
            11: "onze",
            12: "douze",
        }

        if months == 1:
            return "d'un mois"

        if months in nombres:
            return f"de {nombres[months]} mois"

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
        output_dir = os.path.join(os.getcwd(), 'generated_pdfs')
        os.makedirs(output_dir, exist_ok=True)

        base_dir = os.path.dirname(os.path.abspath(__file__))
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
    # Debug: Log evaluation_pdf values for all candidates
    for c in candidates or []:
        print(f"[RH DEBUG] Candidate {c.get('id')}: evaluation_pdf='{c.get('evaluation_pdf')}', evaluation_status='{c.get('evaluation_status')}'")
    return render_template(
        "dashboard_rh.html",
        user=nom_utilisateur(),
        candidates=candidates,
        poles=POLES,
        db_error=db_error,
    )


@app.route("/affectation")
@login_required("affectation")
def affectation():
    # Afficher uniquement les stagiaires acceptés par le RH.
    # Le statut reste 'Accepté' (approved) tout au long du workflow affectation
    # (Fiche d'Accueil → Rapport → Évaluation → Attestation) pour qu'ils
    # restent visibles dans ce tableau jusqu'à la fin.
    candidats = [
        c
        for c in charger_candidats()
        if c.get("status") == "Accepté"
    ]
    return render_template(
        "dashboard_affectation.html",
        user=nom_utilisateur(),
        candidates=candidats,
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
                            "Exécutez supabase_auth.sql et mettez à jour la table profiles."
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
                f"'{STATUT_INITIAL_DB}'. Vérifiez supabase_fix_status.sql ou SUPABASE_STATUS_INITIAL dans .env"
            )
        return jsonify(success=False, error=msg), 500


@app.post("/api/candidates/status")
def api_status():
    if not supabase:
        return jsonify(success=False, error="Supabase non configuré"), 500

    corps = request.get_json() or {}
    nouveau_statut = statut_pour_db(corps.get("status"))
    mise_a_jour = {
        "status": nouveau_statut,
        "rh_status_hint": "",
    }
    if corps.get("department"):
        mise_a_jour["department"] = corps.get("department")
    if nouveau_statut != "action_required":
        mise_a_jour["requested_doc_type"] = None

    try:
        query = supabase.table(TABLE_APPLICATIONS).update(mise_a_jour)
        appliquer_filtre_identifiant(query, corps).execute()
        return jsonify(success=True)
    except Exception as exc:
        return jsonify(success=False, error=str(exc)), 500


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
            "project": corps.get("project") or "",
            "mentor": corps.get("mentor") or "",
        }

        if corps.get("mentor_id"):
            update_data["encadrant_id"] = corps.get(
                "mentor_id"
            )

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

        stagiaire["project"] = update_data["project"]
        stagiaire["mentor"] = update_data["mentor"]

        # =====================================================
        # 4. GENERATE FICHE ACCUEIL
        # =====================================================

        affectation_data = {
            "project": update_data["project"],
            "mentor": update_data["mentor"],
            "department": (
                stagiaire.get("department") or ""
            ),
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
            app.root_path,
            "generated_pdfs",
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
                "id,fiche_accueil_pdf,"
                "project,mentor"
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
@login_required("affectation")
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
@login_required("affectation")
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
                "nom": nom
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
            rh_data = {
                "directeur_rh": corps.get("directeur_rh", ""),
            }
            attestation_pdf = generer_attestation_pdf(stagiaire, rh_data)
            if not attestation_pdf:
                return jsonify(success=False, error="Erreur lors de la génération de l'attestation de stage"), 500

            update_data.update(
                {
                    "attestation_pdf": attestation_pdf,
                    "attestation_status": "Généré",
                    "attestation_generated_at": now_str,
                }
            )
            notif_text = (
                "Félicitations ! Votre fiche d'évaluation a été acceptée par la RH. "
                "Vos documents finaux (fiche d'évaluation et attestation) sont disponibles."
            )
            email_sujet = "[Marsa Maroc] Documents finaux disponibles"
            email_corps = f"""Bonjour {nom_stagiaire},

Votre fiche d'évaluation a été acceptée par la Direction des Ressources Humaines.
Votre attestation de stage officielle est disponible dans votre espace stagiaire.

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



@app.route("/download/fiche_accueil/<path:filename>")
def download_fiche_accueil(filename):
    """Télécharger la fiche d'accueil PDF from generated_pdfs directory."""
    try:
        base_filename = os.path.basename(filename)
        return send_file(
            os.path.join(app.root_path, 'generated_pdfs', base_filename),
            as_attachment=True,
            mimetype="application/pdf"
        )
    except Exception as exc:
        return f"Erreur lors du téléchargement: {str(exc)}", 404


@app.route("/download/evaluation/<path:filename>")
def download_evaluation(filename):
    """Télécharger la fiche d'évaluation PDF from generated_pdfs directory."""
    try:
        base_filename = os.path.basename(filename)
        return send_file(
            os.path.join(os.getcwd(), 'generated_pdfs', base_filename),
            as_attachment=True,
            mimetype="application/pdf"
        )
    except Exception as exc:
        return f"Erreur lors du téléchargement: {str(exc)}", 404


@app.route("/download/attestation/<path:filename>")
def download_attestation(filename):
    """Télécharger l'attestation de stage PDF from generated_pdfs directory."""
    try:
        base_filename = os.path.basename(filename)
        return send_file(
            os.path.join(app.root_path, 'generated_pdfs', base_filename),
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
        path_pdf = os.path.join(app.root_path, 'pdf', base_filename)
        if os.path.exists(path_pdf):
            return send_file(path_pdf, mimetype="application/pdf")
        # Check generated_pdfs directory
        path_gen = os.path.join(app.root_path, 'generated_pdfs', base_filename)
        if os.path.exists(path_gen):
            return send_file(path_gen, mimetype="application/pdf")
        
        # Check with space fallback (like "Evaluation stage .pdf")
        path_pdf_space = os.path.join(os.getcwd(), 'pdf', base_filename + " ")
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
def get_candidate_documents(candidate_id):
    docs = ["cv", "cin", "assurance", "convention", "demande"]
    result = {}
    for doc in docs:
        filename = f"{candidate_id}_{doc}.pdf"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        exists = os.path.exists(filepath)
        
        if not exists:
            fallback_filename = f"{secure_filename(candidate_id)}_{doc}.pdf"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], fallback_filename)
            exists = os.path.exists(filepath)
            
        result[doc] = {
            "uploaded": exists,
            "url": f"/api/documents/{candidate_id}/{doc}" if exists else None,
            "download_url": f"/api/documents/{candidate_id}/{doc}/download" if exists else None
        }
    return jsonify(success=True, documents=result)


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


@app.route("/preview/evaluation/<path:filename>")
def preview_evaluation(filename):
    return _servir_evaluation_pdf(filename, as_attachment=False)


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
    safe_filename = secure_filename(os.path.basename(filename))
    filepath = os.path.join(os.getcwd(), 'generated_pdfs', safe_filename)
    if not os.path.exists(filepath):
        return "Fichier d'évaluation introuvable.", 404
    return send_file(filepath, mimetype="application/pdf", as_attachment=as_attachment)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
