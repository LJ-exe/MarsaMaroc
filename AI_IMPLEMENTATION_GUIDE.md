# 🤖 TECHNICAL IMPLEMENTATION GUIDE - For AI Applications

## Quick Project Understanding

### What is REMIX?
A **Supabase + Flask + HTML** web app where:
- Interns submit internship applications (form)
- HR reviews and approves/rejects them (dashboard table)
- Assignment officers assign approved interns to departments & mentors (management)

### Current Tech Stack
```
Frontend: Nunjucks (HTML templates) + CSS + Vanilla JS
Backend: Python Flask
Database: Supabase (PostgreSQL)
Auth: Supabase Auth (email/password)
```

---

## 🏛️ Architecture Patterns

### 1. Authentication Pattern
```python
# All protected routes use @login_required("role") decorator
@app.route("/rh")
@login_required("rh")
def rh():
    # Only RH role can access
    return render_template("dashboard_rh.html", ...)
```

### 2. Database Normalization Pattern
- Many column name variations (name, full_name, nom_complet, nom + prenom)
- Normalize all to standard names: `normaliser_candidat(ligne: dict)`
- Convert status between French UI and database values

### 3. Role-Based Access Control
```python
ROLES_VALIDES = ("stagiaire", "rh", "affectation")
role_utilisateur()  # Get from session
redirection_pour_role()  # Auto-redirect
```

---

## 📊 Data Models

### Application Object
```python
{
    "id": int,
    "name": str,
    "first_name": str,
    "last_name": str,
    "phone": str,
    "email": str,
    "school": str,
    "specialty": str,  # filiere
    "level": str,      # niveau
    "type": str,       # stage_type
    "period": str,     # periode
    "zone": str,       # zone_affectation
    "department": str, # pole
    "project": str,    # projet_stage
    "mentor": str,     # encadrant
    "status": str,     # pending, approved, rejected, action_required, awaiting_assignment
    "created_at": datetime,
    "submittedAtFormatted": str  # "01 Jan 2024, 14:30"
}
```

### User Profile Object
```python
{
    "id": uuid,
    "email": str,
    "name": str,
    "role": str  # stagiaire, rh, or affectation
}
```

---

## 🔌 API Endpoints to Build From

### Existing Endpoints
- `POST /api/apply` - Submit application
  - Input: JSON with application data
  - Output: `{success: bool, id: int, name: str}` or error

### Expandable Endpoints (for your AI apps)
```python
POST /api/analyze-cv         # AI analysis of application
GET  /api/candidates/stats   # Candidate statistics
PUT  /api/application/{id}   # Update application status
DELETE /api/application/{id} # Delete application
GET  /api/export             # Export candidates as CSV
```

---

## 🗂️ Supabase Schema (PostgreSQL)

### tables.applications
```sql
CREATE TABLE applications (
    id SERIAL PRIMARY KEY,
    name VARCHAR,
    first_name VARCHAR,
    last_name VARCHAR,
    phone VARCHAR,
    email VARCHAR,
    school VARCHAR,
    specialty VARCHAR,
    level VARCHAR,
    type VARCHAR,
    period VARCHAR,
    zone VARCHAR,
    department VARCHAR,
    project VARCHAR,
    mentor VARCHAR,
    status VARCHAR CHECK (status IN ('pending', 'approved', 'rejected', 'action_required', 'awaiting_assignment')),
    created_at TIMESTAMP DEFAULT now()
);
```

### auth.users (Built-in Supabase)
```sql
-- Managed by Supabase Auth
-- Fields: id, email, encrypted_password, last_sign_in_at, etc.
```

### tables.profiles
```sql
CREATE TABLE profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id),
    email VARCHAR,
    name VARCHAR,
    role VARCHAR CHECK (role IN ('stagiaire', 'rh', 'affectation'))
);
```

---

## 🎯 Data Flow Diagrams

### Application Submission Flow
```
User fills form
    ↓
POST /api/apply (JSON data)
    ↓
inserer_candidature() validates
    ↓
Data normalized (donnees_pour_insertion)
    ↓
INSERT to Supabase applications table
    ↓
Return success + application ID
```

### Login Flow
```
User enters email/password
    ↓
POST /login form submission
    ↓
supabase.auth.sign_in_with_password()
    ↓
Fetch user profile from profiles table
    ↓
Extract role from profile
    ↓
Store in Flask session: user_id, user_email, user_name, role
    ↓
Redirect to role-specific dashboard (/stagiaire, /rh, /affectation)
```

### HR Review Flow
```
HR accesses /rh dashboard
    ↓
charger_candidats() fetches all from applications table
    ↓
enrichir_candidats() normalizes and formats each
    ↓
Templates displays in HTML table
    ↓
HR updates status via form/modal
    ↓
PUT /api/application/{id} updates status in DB
    ↓
Refresh dashboard
```

### Assignment Flow
```
Assignment officer accesses /affectation
    ↓
charger_candidats() filtered for status == "Accepté"
    ↓
Dashboard displays eligible candidates only
    ↓
Assign to POLE (department) + ZONE (location) + MENTOR + PROJECT
    ↓
Update status to "Attente Affectation" or "Assigned"
    ↓
Save to database
```

---

## 🛠️ Key Functions to Understand

### auth_helpers.py
```python
# Check if user logged in
utilisateur_connecte()  → bool

# Get user's role from session
role_utilisateur()  → "stagiaire" | "rh" | "affectation"

# Check if registration allowed (block non-intern signups)
inscription_autorisee(email, role)  → (ok: bool, message: str)

# Create session after successful auth
enregistrer_session(auth_response, profil, inscription=False)

# Decorator for protecting routes
@login_required("rh")
def protected_route(): ...
```

### db_config.py
```python
# Create Supabase client
creer_client_supabase(url, key)  → SupabaseClient

# Normalize candidate data
normaliser_candidat(row: dict)  → standardized_dict

# Convert status French → DB
statut_pour_db("Accepté")  → "approved"

# Convert status DB → French
statut_pour_affichage("approved")  → "Accepté"

# Prepare data for insertion
donnees_pour_insertion(corps: dict)  → cleaned_dict
```

### app.py
```python
# Load all applications with error handling
charger_candidats_avec_erreur()  → (candidates, error_msg)

# Format timestamp in French
formater_date_soumission(iso_string)  → "01 Jan 2024, 14:30"

# Enrich candidates with formatted dates
enrichir_candidats(raw_data)  → formatted_data

# Insert new application
inserer_candidature(data: dict)  → supabase_response
```

---

## 📐 Common Patterns to Follow

### 1. Error Handling
```python
try:
    response = supabase.table("applications").select("*").execute()
    return response.data, None
except Exception as exc:
    print(f"[ERROR_CONTEXT] Error message: {exc}")
    return [], str(exc)
```

### 2. Session Management
```python
session.clear()  # Clear old session
session["user_id"] = ...
session["role"] = ...
session.modified = True  # Force save
```

### 3. Status Conversions
```python
# Always use these functions, don't hardcode status values
status_db = statut_pour_db(status_ui)
status_ui = statut_pour_affichage(status_db)
```

### 4. Data Normalization
```python
# Always normalize data before displaying or using
normalized = normaliser_candidat(row_from_db)
name = normalized["name"]  # Guaranteed to exist
```

### 5. Protected Routes
```python
@app.route("/protected")
@login_required("required_role")
def protected():
    user = nom_utilisateur()
    role = role_utilisateur()
    return render_template(...)
```

---

## 🎨 Template Variables Available

### All Templates Receive
```python
{
    "user": nom_utilisateur(),  # Display logged-in user name
    "role": role_utilisateur(),  # Current user role
    "poles": POLES,  # List of departments
    "zones": ZONES,  # List of work zones
    "candidates": [...],  # List of applications (for RH)
    "db_error": None  # Database error message if any
}
```

---

## 🔐 Important Security Notes

### Reserved Emails (Can only be created by admin)
```python
EMAILS_RESERVES_INSCRIPTION = {
    "rh@marsamaroc.ma",
    "aff@marsamaroc.ma"
}
# Anyone trying to signup with these emails gets rejected
```

### Session Timeout
- Max age: 24 hours
- Clear on logout
- Store: Flask server-side session

### CSRF Protection
- Use form submissions, not direct HTTP calls
- Supabase handles API security

---

## 📦 Dependencies & Versions

### Python (requirements.txt)
```
flask>=3.0.0
python-dotenv>=1.0.0
supabase>=2.0.0
certifi>=2024.0.0
httpx>=0.27.0
```

### Node.js (package.json)
- express
- express-session
- @supabase/supabase-js
- nunjucks
- dotenv

---

## 🚀 For Building New AI Features

### Recommended Approach
1. **Extend existing endpoints**: Add new routes like `/api/analyze`, `/api/export`
2. **Add new tables**: Create `analyses`, `assignments`, `logs` as needed
3. **Keep auth pattern**: Use same `@login_required()` decorator
4. **Use normalizer**: Always use `normaliser_candidat()` when reading from DB
5. **Follow status mapping**: Use conversion functions for any status values
6. **Template variables**: Pass data dict to render_template with user context

### Example: New CV Analysis Route
```python
@app.post("/api/analyze-cv/{application_id}")
@login_required("rh")
def analyze_cv(application_id):
    # Get application from DB
    app = supabase.table("applications").select("*").eq("id", application_id).execute()
    candidate = normaliser_candidat(app.data[0])
    
    # Call AI analysis (e.g., Gemini API)
    analysis = analyze_with_ai(candidate)
    
    # Store results
    supabase.table("cv_analyses").insert([{
        "application_id": application_id,
        "analysis": analysis,
        "created_at": datetime.now()
    }]).execute()
    
    return jsonify(analysis)
```

---

## 📝 File Modification Strategy

### Safe Edits (Won't break things)
- Add new routes to `app.py`
- Add new helper functions to `auth_helpers.py` or `db_config.py`
- Create new template files in `templates/`
- Add new scripts in `scripts/`

### Risky Edits (Test thoroughly)
- Modify authentication flow in `auth_helpers.py`
- Change status mappings in `db_config.py`
- Alter session handling in login/register routes
- Change database table names

### Never Edit
- The Flask secret_key mechanism (change only in .env)
- Supabase client initialization (it's fragile with SSL)
- The role validation lists (ROLES_VALIDES)

---

## 🧪 Testing the System

### Manual Testing Checklist
- [ ] Can register new intern account
- [ ] Can login with registered account
- [ ] Intern can submit application
- [ ] HR can see application in dashboard
- [ ] HR can update application status
- [ ] Assignment officer sees only approved apps
- [ ] Logout clears session properly

### API Testing (using curl or Postman)
```bash
# Submit application
curl -X POST http://localhost:5000/api/apply \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Ahmed",
    "last_name": "Hassan",
    "phone": "0612345678",
    "school": "Université Hassan II",
    "specialty": "Informatique",
    "zone": "Siège Social - Casablanca",
    "start": "2024-06-01",
    "end": "2024-08-31"
  }'
```

---

## 🔄 Version Control Notes

### Current State
- Python Flask backend fully functional
- Node.js Express backend available as alternative
- Authentication working with Supabase
- Dashboard for three roles working

### Future Compatibility
- Maintain Python/Node.js compatibility
- Keep status mapping constants centralized
- Don't hardcode user roles in templates
- Use helper functions, not direct database queries in routes

---

## 📞 Integration Points for AI

### For ChatBot/Q&A
- Use application data from `applications` table
- Implement FAQ route returning JSON

### For Document Analysis
- Parse uploaded CVs in `static/uploads/`
- Use cv_analyzer.py as reference

### For Recommendations
- Analyze applications, score candidates
- Store scores in new `candidate_scores` table
- Display in RH dashboard

### For Notifications
- Add email service for status changes
- Integrate SMS for zone assignments

### For Reporting
- Query applications with filters
- Generate statistics/charts
- Export to CSV/PDF

---

## 🎓 Summary

This project follows a **standard 3-tier architecture**:
- **Presentation** (Templates): Nunjucks HTML
- **Business Logic** (app.py): Flask routes + helpers
- **Data** (Supabase): PostgreSQL database

To extend it with AI features:
1. Add new routes in `app.py`
2. Create new tables in Supabase for analysis results
3. Use existing helper functions for data access
4. Maintain role-based access with `@login_required()`
5. Test thoroughly before deploying

**Key Principle**: Keep authentication/authorization centralized, use helper functions for data access, follow the status mapping pattern, and never hardcode values.
