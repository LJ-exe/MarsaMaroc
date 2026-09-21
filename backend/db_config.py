"""Configuration Supabase — table et mapping des colonnes."""

import os
import re

import certifi
import httpx
from supabase import create_client
from supabase.lib.client_options import SyncClientOptions


def _verification_ssl():
    """Certificats SSL : certifi par défaut, désactivable via .env (Windows / proxy)."""
    valeur = (os.getenv("SUPABASE_SSL_VERIFY") or "true").strip().lower()
    if valeur in ("0", "false", "no", "off"):
        return False
    return certifi.where()


def creer_client_supabase(url: str, key: str):
    """Client Supabase (httpx + SSL configurable)."""
    if not url or not key:
        return None
    httpx_client = httpx.Client(verify=_verification_ssl(), timeout=30.0)
    options = SyncClientOptions(httpx_client=httpx_client)
    return create_client(url, key, options=options)

# Table réelle dans Supabase (hint PostgREST : public.applications)
TABLE_APPLICATIONS = os.getenv("SUPABASE_TABLE", "applications")

# Statut initial à l'insertion (doit respecter applications_status_check)
STATUT_INITIAL_DB = os.getenv("SUPABASE_STATUS_INITIAL", "pending")

# Interface FR → valeurs en base (CHECK constraint Supabase)
STATUT_UI_VERS_DB = {
    "En attente": "pending",
    "Accepté": "approved",
    "Refusé": "rejected",
    "Action Requise": "action_required",
    "Attente Affectation": "awaiting_assignment",
}

STATUT_DB_VERS_UI = {v: k for k, v in STATUT_UI_VERS_DB.items()}

# Alias si la base utilise d'autres libellés
# Colonnes ajoutées par supabase/migrations/supabase_stagiaire_dashboard.sql (optionnelles si migration non exécutée)
COLONNES_OPTIONNELLES_APPLICATIONS = (
    "dossier_submitted",
    "submitted_to_rh_at",
    "requested_doc_type",
    "rh_status_hint",
    "user_id",
    "email",
    "evaluation_pdf",
    "evaluation_status",
    "evaluation_submitted_at",
    "evaluation_data",
    "attestation_pdf",
    "attestation_status",
    "attestation_generated_at",
    "mentor_function",
    "notifications",
    "chat_messages",
    "intern_report_path",
    "intern_report_status",
    "evaluation_reject_reason",
    "encadrant_id",
)

STATUT_DB_VERS_UI.update(
    {
        "pending": "En attente",
        "approved": "Accepté",
        "accepted": "Accepté",
        "rejected": "Refusé",
        "refused": "Refusé",
        "action_required": "Action Requise",
        "awaiting_assignment": "Attente Affectation",
        "submitted": "En attente",
        "under_review": "En attente",
    }
)


def statut_pour_db(statut_ui: str) -> str:
    """Convertit le statut affiché (FR) vers la valeur base de données."""
    if not statut_ui:
        return STATUT_INITIAL_DB
    return STATUT_UI_VERS_DB.get(statut_ui, statut_ui)


def statut_pour_affichage(statut_db: str) -> str:
    """Convertit le statut base de données vers l'affichage FR."""
    if not statut_db:
        return "En attente"
    return STATUT_DB_VERS_UI.get(statut_db, statut_db)


def normaliser_candidat(ligne: dict) -> dict:
    """Unifie les noms de colonnes DB vers le format utilisé par les templates."""
    prenom = ligne.get("first_name") or ligne.get("prenom") or ""
    nom_famille = ligne.get("last_name") or ligne.get("nom") or ""
    nom = (
        ligne.get("name")
        or ligne.get("full_name")
        or ligne.get("nom_complet")
        or f"{prenom} {nom_famille}".strip()
        or " ".join(
            filter(
                None,
                [ligne.get("nom"), ligne.get("prenom")],
            )
        ).strip()
    )

    statut_db = ligne.get("status") or ligne.get("statut") or STATUT_INITIAL_DB

    return {
        "id": ligne.get("id"),
        "name": nom or "—",
        "phone": ligne.get("phone") or ligne.get("telephone") or ligne.get("tel"),
        "school": ligne.get("school") or ligne.get("ecole") or ligne.get("establishment"),
        "specialty": ligne.get("specialty") or ligne.get("filiere") or ligne.get("specialite"),
        "level": ligne.get("level") or ligne.get("niveau"),
        "type": ligne.get("type") or ligne.get("stage_type"),
        "period": ligne.get("period") or ligne.get("periode"),
        "zone": ligne.get("zone") or ligne.get("zone_affectation"),
        "department": ligne.get("department") or ligne.get("pole") or ligne.get("direction"),
        "project": ligne.get("project") or ligne.get("projet") or ligne.get("projet_stage"),
        "mentor": ligne.get("mentor") or ligne.get("encadrement") or ligne.get("encadrant"),
        "status": statut_pour_affichage(statut_db),
        "status_db": statut_db,
        "created_at": ligne.get("created_at") or ligne.get("submitted_at") or ligne.get("date_soumission"),
        "remark": ligne.get("remark") or "",
        "email": ligne.get("email") or "",
        "user_id": ligne.get("user_id"),
        "dossier_submitted": bool(ligne.get("dossier_submitted")),
        "submitted_to_rh_at": ligne.get("submitted_to_rh_at"),
        "requested_doc_type": ligne.get("requested_doc_type") or "",
        "rh_status_hint": ligne.get("rh_status_hint") or "",
        "fiche_accueil_pdf": ligne.get("fiche_accueil_pdf") or "",
        "evaluation_pdf": ligne.get("evaluation_pdf") or "",
        "evaluation_status": ligne.get("evaluation_status") or "",
        "evaluation_submitted_at": ligne.get("evaluation_submitted_at"),
        "evaluation_data": ligne.get("evaluation_data") or {},
        "attestation_pdf": ligne.get("attestation_pdf") or "",
        "attestation_status": ligne.get("attestation_status") or "",
        "attestation_generated_at": ligne.get("attestation_generated_at"),
        "mentor_function": ligne.get("mentor_function") or "",
        "notifications": ligne.get("notifications") or [],
        "chat_messages": ligne.get("chat_messages") or [],
        "intern_report_path": ligne.get("intern_report_path") or "",
        "intern_report_status": ligne.get("intern_report_status") or "",
        "evaluation_reject_reason": ligne.get("evaluation_reject_reason") or "",
        "encadrant_id": ligne.get("encadrant_id"),
    }


def colonne_manquante_dans_erreur(exc: Exception) -> str | None:
    """Extrait le nom de colonne depuis une erreur PostgREST PGRST204."""
    msg = str(exc)
    match = re.search(r"the '(\w+)' column", msg, re.I)
    return match.group(1) if match else None


def supabase_executer_insert(client, table: str, donnees: dict):
    """Insert avec retrait automatique des colonnes absentes en base."""
    payload = dict(donnees)
    derniere_erreur = None
    for _ in range(len(payload) + len(COLONNES_OPTIONNELLES_APPLICATIONS) + 2):
        try:
            return client.table(table).insert([payload]).execute()
        except Exception as exc:
            derniere_erreur = exc
            col = colonne_manquante_dans_erreur(exc)
            if col and col in payload:
                payload.pop(col)
                continue
            if "applications_status_check" in str(exc) or "23514" in str(exc):
                payload.pop("status", None)
                continue
            raise
    if derniere_erreur:
        raise derniere_erreur
    raise RuntimeError("Échec insert Supabase")


def supabase_executer_update_eq(client, table: str, donnees: dict, filtre_col: str, filtre_val):
    """Update (.eq) avec retrait automatique des colonnes absentes en base."""
    payload = dict(donnees)
    derniere_erreur = None
    for _ in range(len(payload) + len(COLONNES_OPTIONNELLES_APPLICATIONS) + 2):
        try:
            return client.table(table).update(payload).eq(filtre_col, filtre_val).execute()
        except Exception as exc:
            derniere_erreur = exc
            col = colonne_manquante_dans_erreur(exc)
            if col and col in payload:
                payload.pop(col)
                continue
            raise
    if derniere_erreur:
        raise derniere_erreur
    raise RuntimeError("Échec update Supabase")


def message_hint_rh(candidat: dict) -> str:
    """Message visuel sous le statut dans le tableau RH (pas un nouveau statut DB)."""
    return (candidat.get("rh_status_hint") or "").strip()


def donnees_pour_insertion(corps: dict) -> dict:
    """Prépare un enregistrement pour Supabase (colonnes table applications)."""
    prenom = (corps.get("first_name") or corps.get("prenom") or "").strip()
    nom_famille = (corps.get("last_name") or corps.get("nom") or "").strip()

    if not prenom or not nom_famille:
        nom_complet = (corps.get("name") or "").strip()
        parts = nom_complet.split(None, 1)
        if not prenom and parts:
            prenom = parts[0]
        if not nom_famille and len(parts) > 1:
            nom_famille = parts[1]
        elif not nom_famille and parts:
            nom_famille = parts[0]

    nom_affiche = f"{prenom} {nom_famille}".strip() or (corps.get("name") or "").strip()
    period = f"{corps.get('start', '')} - {corps.get('end', '')}"
    level = corps.get("level") or "N/A"
    if level == "Choisir":
        level = "N/A"

    donnees = {
        "first_name": prenom,
        "last_name": nom_famille,
        "name": nom_affiche,
        "phone": corps.get("phone"),
        "school": corps.get("school"),
        "specialty": corps.get("specialty") or "N/A",
        "level": level,
        "type": corps.get("type") or "PFE",
        "period": period,
        "zone": corps.get("zone"),
        "status": STATUT_INITIAL_DB,
    }
    if corps.get("email"):
        donnees["email"] = corps.get("email")
    if corps.get("user_id"):
        donnees["user_id"] = corps.get("user_id")
    return donnees


def appliquer_filtre_identifiant(query, corps: dict):
    """Filtre une requête update/delete par id ou par name."""
    if corps.get("id"):
        return query.eq("id", corps.get("id"))
    return query.eq("name", corps.get("name"))
