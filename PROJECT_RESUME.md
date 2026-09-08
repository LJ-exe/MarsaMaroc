# 📋 PROJECT RESUME: REMIX - Marsa Maroc Stagiaires Management System

## 🎯 Project Overview
**REMIX** is a comprehensive **Internship Management Platform** designed for **Marsa Maroc** (Morocco's largest port company). It streamlines the entire internship lifecycle from application submission to final assignment across different departments and port zones.

---

## 📊 Project Type & Scope
- **Type**: Full-Stack Web Application
- **Purpose**: Manage internship applications, track candidates, and assign them to departments/zones
- **Target Users**: 
  - Stagiaires (Interns) - Apply for internships
  - RH (Human Resources) - Review and evaluate applications
  - Affectation (Assignment Officers) - Assign approved interns to positions

---

## 🏗️ Technology Stack

### Backend
- **Primary**: Python Flask (REST API + Web Server)
- **Alternative**: Node.js/Express (for API routes)
- **Database**: Supabase (PostgreSQL)
- **Authentication**: Supabase Auth (email/password)
- **File Handling**: Werkzeug for secure file uploads

### Frontend
- **Template Engine**: Nunjucks (HTML templating)
- **Styling**: CSS (custom style.css)
- **Static Files**: JavaScript, CSS, uploaded files (CVs, documents)

### Configuration
- **Environment**: .env for sensitive data (API keys, database URLs)
- **Dependencies**: Flask, Supabase Python client, httpx, python-dotenv

---

## 📁 Project Structure

```
project-root/
├── app.py                          # Main Flask application + all routes
├── auth_helpers.py                 # Authentication logic & session management
├── db_config.py                    # Database configuration & data normalization
├── server.js                       # Alternative Node.js/Express server
├── requirements.txt                # Python dependencies
├── package.json                    # Node.js dependencies
├── metadata.json                   # Project metadata
├── README.md                       # Installation & deployment guide
│
├── static/                         # Static assets
│   ├── css/
│   │   └── style.css              # Main stylesheet
│   └── uploads/                    # User-uploaded files (CVs, documents)
│
├── templates/                      # HTML templates (Nunjucks)
│   ├── index.html                 # Landing page
│   ├── login.html                 # User login page
│   ├── register.html              # User registration page
│   ├── dashboard.html             # Intern dashboard
│   ├── dashboard_rh.html          # HR dashboard (all applications)
│   └── dashboard_affectation.html # Assignment dashboard
│
└── scripts/                        # Utility scripts
    ├── cv_analyzer.py             # CV/Application analysis tool
    ├── creer_comptes_admin.py     # Admin account creation script
    ├── test_routes.py             # Route testing utility
    └── verify_setup.py            # Setup verification script
```

---

## 🔐 Authentication & Authorization

### Three User Roles
1. **Stagiaire (Intern)**
   - Can create account via registration page
   - Can submit internship applications
   - Can view their own application status
   - Redirect to `/stagiaire` after login

2. **RH (Human Resources)**
   - Reserved account (email: rh@marsamaroc.ma)
   - Can view all applications in a table/dashboard
   - Can update application status (Pending → Approved/Rejected/Action Required)
   - Can search and filter candidates
   - Redirect to `/rh` after login

3. **Affectation (Assignment Officer)**
   - Reserved account (email: aff@marsamaroc.ma)
   - Can view only APPROVED applications
   - Can assign interns to departments (POLES) and zones
   - Redirect to `/affectation` after login

### Authentication Flow
1. User signs up/logs in via Supabase Auth
2. Session stored in Flask session object
3. Role determined from `profiles` table
4. User redirected to role-specific dashboard

---

## 🗄️ Database Schema (Supabase)

### Main Tables
1. **applications** (Internship Applications)
   - Columns: id, name, first_name, last_name, phone, email
   - Fields: school, specialty/filiere, level, type, period
   - Assignment: zone, department/pole, project, mentor
   - Status: pending, approved, rejected, action_required, awaiting_assignment
   - Timestamps: created_at, submitted_at

2. **profiles** (User Profiles)
   - Columns: id (FK from auth.users), name, email, role
   - Roles: stagiaire, rh, affectation
   - Created on first login/registration

### Key Constants
- **POLES (Departments)**:
  - DSI - Direction Systèmes d'Information
  - DCH - Capital Humain
  - DAF - Finance & Contrôle
  - DOF - Opérations Portuaires

- **ZONES (Work Locations)**:
  - Siège Social - Casablanca
  - Terminal à conteneurs TC3
  - Port Tanger Med I
  - Port d'Agadir

- **Status Mapping** (French UI ↔ Database):
  - En attente ↔ pending
  - Accepté ↔ approved/accepted
  - Refusé ↔ rejected/refused
  - Action Requise ↔ action_required
  - Attente Affectation ↔ awaiting_assignment

---

## 🛣️ API Routes & Endpoints

### Public Routes
- `GET /` - Landing page
- `GET/POST /login` - User login
- `GET/POST /register` - User registration (interns only)

### Protected Routes (Role-based)
- `GET /stagiaire` - Intern dashboard (requires: stagiaire role)
- `GET /rh` - HR dashboard with all candidates (requires: rh role)
- `GET /affectation` - Assignment dashboard with approved candidates (requires: affectation role)

### API Endpoints
- `POST /api/apply` - Submit internship application
  - Required fields: name/first_name+last_name, phone, school, specialty, zone, start, end
  - Returns: {success: bool, id: int, name: string} or error

### Auth Endpoints
- `GET /logout` - Clear session and sign out

---

## 🔄 Key Features & Functionality

### 1. **Application Submission**
   - Interns fill form with personal & educational info
   - Select internship period (start/end dates)
   - Choose preferred zone and department (if applicable)
   - System validates required fields
   - Application status defaults to "pending"

### 2. **Application Review (HR)**
   - View all applications in table format
   - Sort by submitted date, name, school, etc.
   - Update candidate status (approve/reject/request action)
   - Search and filter applications
   - See formatted submission timestamps

### 3. **CV Analysis**
   - Python script (`cv_analyzer.py`) to analyze application content
   - Extract keywords: logistics, transport, port operations, security, HR
   - Score candidates based on keyword matches
   - Generate recommendations

### 4. **Assignment Management**
   - Assignment officers view approved candidates
   - Assign interns to specific POLES (departments)
   - Assign to ZONES (physical work locations)
   - Assign mentor/supervisor (encadrant)
   - Assign project/internship topic

### 5. **Session & User Management**
   - Session timeout: 24 hours
   - Role-based access control (login_required decorator)
   - Auto-redirect to role-specific dashboard
   - Session persistence across requests

---

## 🛠️ Key Helper Functions & Modules

### auth_helpers.py
- `utilisateur_connecte()` - Check if user is logged in
- `role_utilisateur()` - Get user's role from session
- `inscription_autorisee()` - Validate registration permissions
- `enregistrer_session()` - Create session after login/signup
- `login_required()` - Decorator for protected routes
- `redirection_pour_role()` - Get role-specific dashboard URL

### db_config.py
- `creer_client_supabase()` - Initialize Supabase client
- `normaliser_candidat()` - Unify candidate data from different column names
- `statut_pour_db()` - Convert French status → database value
- `statut_pour_affichage()` - Convert database status → French display
- `donnees_pour_insertion()` - Prepare application data for database insert
- `appliquer_filtre_identifiant()` - Filter records by ID

### app.py (Main Application)
- `charger_candidats()` - Fetch all applications from database
- `enrichir_candidats()` - Format candidate data for display
- `formater_date_soumission()` - Format timestamps in French locale
- `inserer_candidature()` - Insert new application to database

---

## 📝 Configuration & Environment Variables

Required `.env` variables:
```
SUPABASE_URL=<your-supabase-project-url>
SUPABASE_KEY=<your-supabase-api-key>
SUPABASE_TABLE=applications
SUPABASE_STATUS_INITIAL=pending
SUPABASE_SSL_VERIFY=true
SECRET_KEY=<flask-session-secret-key>
GEMINI_API_KEY=<optional-for-ai-features>
```

---

## 🚀 Deployment & Running

### Local Development
```bash
# Install dependencies
npm install  # for Node.js modules
pip install -r requirements.txt  # for Python

# Set environment variables in .env file

# Run Flask app
python app.py

# OR run Node.js server
node server.js
```

### AI Studio Deployment
- Project is integrated with AI Studio
- View app: https://ai.studio/apps/7691bfc4-59dd-4242-a698-70d1d4ae6178

---

## 🔗 Integration Points

### Supabase Integration
- **Authentication**: Supabase Auth manages user accounts
- **Database**: PostgreSQL database via Supabase
- **Realtime**: Potential for real-time updates (not currently implemented)
- **SSL**: Configurable SSL verification for different environments

### AI/Gemini Integration
- CV analysis can be powered by Gemini API
- Application scoring and recommendations
- GEMINI_API_KEY stored in environment

---

## 📱 User Workflows

### Intern (Stagiaire) Workflow
1. Visit homepage
2. Register account (email + password)
3. Access personal dashboard
4. Fill internship application form
5. Submit application
6. Monitor application status
7. Wait for HR review and assignment

### HR Workflow
1. Login with rh@marsamaroc.ma
2. Access HR dashboard
3. View all pending applications
4. Review candidate qualifications
5. Update status (approve/reject/request action)
6. Pass approved candidates to assignment team

### Assignment Officer (Affectation) Workflow
1. Login with aff@marsamaroc.ma
2. Access assignment dashboard
3. View approved candidates only
4. Assign to departments (POLES)
5. Assign to zones (locations)
6. Assign mentors and projects
7. Finalize internship placements

---

## 🐛 Known Utilities & Helpers

### Scripts
- **cv_analyzer.py** - Analyzes application text for relevant keywords
- **creer_comptes_admin.py** - Helper to create admin/HR accounts
- **test_routes.py** - Test script for API endpoints
- **verify_setup.py** - Verify environment setup and database connection

### SQL Files
- **supabase_auth.sql** - Initial authentication setup
- **supabase_migration.sql** - Database schema creation
- **supabase_fix_*.sql** - Various database constraint fixes

---

## 🎨 Frontend Architecture

### Page Structure
1. **index.html** - Landing page with welcome message
2. **login.html** - Login form (email/password)
3. **register.html** - Registration form (name/email/password) - Interns only
4. **dashboard.html** - Intern application form & status tracker
5. **dashboard_rh.html** - HR management table with filters
6. **dashboard_affectation.html** - Assignment management interface

### Static Assets
- **style.css** - Global styling for all pages
- **uploads/** - Directory for storing CV files and documents

---

## 🔮 Extension Opportunities

This project can be extended with:
1. **Advanced CV Analysis** - Integration with ML/AI models for automatic screening
2. **Email Notifications** - Notify interns of status changes
3. **Document Management** - Upload and store CVs, cover letters, documents
4. **Analytics Dashboard** - Statistics on applications, approvals, assignments
5. **Interview Scheduling** - Calendar integration for interviews
6. **Reporting** - Generate internship placement reports
7. **Mobile App** - React Native/Flutter mobile version
8. **Blockchain** - Certificate generation for completed internships

---

## 📋 Summary for AI Implementation

This project is a **role-based internship management system** with three tiers:
- **Data Collection**: Interns submit applications
- **Review Process**: HR evaluates and filters candidates
- **Placement**: Assignment officers match interns to positions and mentors

The system uses **Supabase** for authentication and data, **Flask** for backend logic, and **Nunjucks templates** for frontend. All user data flows through a **status pipeline** (pending → approved/rejected → assigned) with role-based access control at each stage.

**For new applications/features**: Focus on expanding the dashboard capabilities, adding document management, implementing automated CV screening, or creating mobile versions while maintaining the existing authentication and database structure.
