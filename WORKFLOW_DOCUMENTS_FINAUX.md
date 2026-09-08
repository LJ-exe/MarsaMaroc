# Workflow — Documents finaux de stage

## Ordre du processus

1. **Fiche d'accueil** — générée à l'affectation (inchangé)
2. **Rapport de stage** — déposé par le stagiaire (`Déposer Rapport`)
3. **Validation rapport** — affectation valide dans le modal « Rapport »
4. **Fiche d'évaluation** — affectation remplit critères, textes et signatures → PDF template `pdf/Evaluation stage .pdf`
5. **Validation RH** — preview, accepter (attestation) ou refuser (motif → affectation)
6. **Attestation** — générée si RH accepte (`pdf/Attestation de stage .pdf`)
7. **Espace stagiaire** — documents finaux visibles après acceptation RH

## Migration Supabase

Exécuter si ce n'est pas déjà fait :

- `supabase_evaluation_workflow.sql`
- `supabase_chat_and_report.sql`
- `supabase_report_validation.sql` (colonnes `intern_report_status`, `evaluation_reject_reason`)

## API ajoutées / modifiées

| Méthode | Route | Rôle |
|---------|-------|------|
| POST | `/api/report/upload` | stagiaire |
| POST | `/api/report/validate` | affectation |
| GET | `/preview/report/<fichier>` | aperçu PDF |
| POST | `/api/candidates/evaluation` | affectation (rapport validé requis) |
| POST | `/api/candidates/evaluation/valider` | rh (motif obligatoire si refus) |

## E-mails (variables `.env`)

- `EMAIL_AFFECTATION` — défaut `aff@marsamaroc.ma`
- `EMAIL_RH` — défaut `rh@marsamaroc.ma`
- `SMTP_*` / `MAIL_FROM` — envoi réel optionnel
