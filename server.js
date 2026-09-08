const express = require('express');
const path = require('path');
const session = require('express-session');
const { createClient } = require('@supabase/supabase-js');
const dotenv = require('dotenv');
dotenv.config({ path: '.env.local' });
dotenv.config();

const app = express();
const PORT = process.env.PORT || 3000;

// Initialize Supabase
const supabaseUrl = process.env.SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_KEY;
if (!supabaseUrl || !supabaseKey) {
    console.error('WARNING: SUPABASE_URL or SUPABASE_KEY is not defined in environment variables.');
}
const supabase = createClient(supabaseUrl, supabaseKey);

const TABLE_APPLICATIONS = process.env.SUPABASE_TABLE || 'applications';

/** Unifie les colonnes Supabase vers le format des templates. */
function normaliserCandidat(row) {
    const nom = row.name || row.full_name || row.nom_complet
        || [row.nom, row.prenom, row.first_name, row.last_name].filter(Boolean).join(' ').trim();
    return {
        id: row.id,
        name: nom || '—',
        phone: row.phone || row.telephone || row.tel,
        school: row.school || row.ecole || row.establishment,
        specialty: row.specialty || row.filiere || row.specialite,
        level: row.level || row.niveau,
        type: row.type || row.stage_type,
        period: row.period || row.periode,
        zone: row.zone || row.zone_affectation,
        department: row.department || row.pole || row.direction,
        project: row.project || row.projet || row.projet_stage,
        mentor: row.mentor || row.encadrement || row.encadrant,
        status: row.status || row.statut || 'En attente',
        created_at: row.created_at || row.submitted_at || row.date_soumission,
    };
}

/** Formate la date de soumission du dossier pour l'affichage RH (fr-FR). */
function formaterDateSoumission(iso) {
    if (!iso) return 'Non renseignée';
    return new Date(iso).toLocaleString('fr-FR', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

app.locals.formaterDateSoumission = formaterDateSoumission;

app.set('trust proxy', 1);

const nunjucks = require('nunjucks');
nunjucks.configure(path.join(__dirname, 'templates'), { autoescape: true, express: app });
app.set('view engine', 'html');
app.set('views', path.join(__dirname, 'templates'));

const POLES = [
    "DSI - Direction Systèmes d'Information",
    'DCH - Capital Humain',
    'DAF - Finance & Contrôle',
    'DOF - Opérations Portuaires',
];

const ZONES = [
    'Siège Social - Casablanca',
    'Terminal à conteneurs TC3',
    'Port Tanger Med I',
    "Port d'Agadir",
];

app.use(express.static(path.join(__dirname, 'static')));
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(session({
    secret: 'marsa_maroc_secret_key',
    resave: true,
    saveUninitialized: true,
    name: 'marsa_session',
    cookie: {
        secure: false,
        maxAge: 24 * 60 * 60 * 1000
    }
}));

// Routes for demo fallback
app.get('/rh', (req, res) => {
    req.session.user = 'Responsable RH';
    req.session.role = 'rh';
    req.session.save((err) => {
        if (err) console.error('Session Error:', err);
        res.redirect('/dashboard?role=rh');
    });
});

app.get('/affectation', (req, res) => {
    req.session.user = 'Responsable Affectation';
    req.session.role = 'affectation';
    req.session.save((err) => {
        if (err) console.error('Session Error:', err);
        res.redirect('/dashboard?role=affectation');
    });
});

app.get('/stagiaire', (req, res) => {
    req.session.user = 'Stagiaire Test';
    req.session.role = 'stagiaire';
    req.session.save((err) => {
        if (err) console.error('Session Error:', err);
        res.redirect('/dashboard?role=stagiaire');
    });
});

// Routes
app.get('/', (req, res) => {
    res.render('index.html');
});

app.get('/login', (req, res) => {
    res.render('login.html', { error: null });
});

app.post('/login', async (req, res) => {
    const email = (req.body.email || '').toLowerCase().trim();
    const password = (req.body.password || '').trim();

    try {
        const { data: authData, error: authError } = await supabase.auth.signInWithPassword({
            email,
            password
        });

        if (authError || !authData.user) {
            console.error('Supabase login error:', authError);
            return res.render('login.html', { error: 'Email ou mot de passe incorrect' });
        }

        const { data: profile, error: profileError } = await supabase
            .from('profiles')
            .select('name, role')
            .eq('id', authData.user.id)
            .maybeSingle();

        if (profileError) console.error('Profile lookup error:', profileError);

        req.session.user = profile?.name || authData.user.user_metadata?.full_name || email;
        req.session.role = profile?.role || authData.user.user_metadata?.role || 'stagiaire';
        req.session.user_email = email;
        req.session.save((sessionError) => {
            if (sessionError) console.error('Session Error:', sessionError);
            return res.redirect('/dashboard');
        });
    } catch (e) {
        console.error('System login error:', e);
        return res.render('login.html', { error: 'Email ou mot de passe incorrect' });
    }
});

app.get('/register', (req, res) => {
    res.render('register.html', { error: null });
});

app.post('/register', async (req, res) => {
    const name = (req.body.name || '').trim();
    const email = (req.body.email || '').toLowerCase().trim();
    const password = (req.body.password || '').trim();

    try {
        const { data, error } = await supabase.auth.signUp({
            email,
            password,
            options: {
                data: { full_name: name, role: 'stagiaire' }
            }
        });

        if (error || !data.user) {
            console.error('Registration error:', error);
            return res.render('register.html', { error: 'Erreur lors de l\'inscription. L\'email est peut-être déjà utilisé.' });
        }

        res.redirect('/login');
    } catch (e) {
        console.error('System register error:', e);
        res.render('register.html', { error: 'Erreur système lors de l\'inscription.' });
    }
});

app.get('/logout', (req, res) => {
    req.session.destroy();
    res.redirect('/login');
});

app.get('/dashboard', async (req, res) => {
    const queryRole = req.query.role;

    if (!req.session.user && !queryRole) {
        return res.redirect('/login');
    }

    const user = req.session.user || (queryRole ? (queryRole === 'rh' ? 'Responsable RH' : (queryRole === 'affectation' ? 'Responsable Affectation' : 'Stagiaire Test')) : 'Utilisateur');
    const role = req.session.role || queryRole;

    console.log(`[DASHBOARD] Chargement pour ${user} (${role}) via ${req.session.user ? 'session' : 'query'}`);

    try {
        // Fetch candidates list from Supabase
        const { data: candidates, error } = await supabase
            .from(TABLE_APPLICATIONS)
            .select('*')
            .order('created_at', { ascending: false });

        if (error) {
            console.error('Error fetching applications from Supabase:', error);
        }

        const candidatesList = (candidates || []).map(normaliserCandidat);
        const candidatesWithDates = candidatesList.map(candidate => ({
            ...candidate,
            submittedAtFormatted: formaterDateSoumission(candidate.created_at)
        }));

        if (role === 'rh') {
            return res.render('dashboard_rh.html', { user, candidates: candidatesWithDates, poles: POLES });
        } else if (role === 'affectation') {
            const acceptedCandidates = candidatesWithDates.filter(c => c.status === 'Accepté');
            return res.render('dashboard_affectation.html', { user, candidates: acceptedCandidates });
        } else {
            return res.render('dashboard.html', { user, zones: ZONES });
        }
    } catch (e) {
        console.error('Dashboard render error:', e);
        return res.redirect('/login');
    }
});

// Soumission d'une nouvelle candidature stagiaire
app.post('/api/apply', async (req, res) => {
    const { name, phone, school, specialty, level, type, zone, start, end } = req.body;
    const period = `${start} - ${end}`;
    const dateSoumission = new Date().toISOString();

    try {
        const { data, error } = await supabase
            .from(TABLE_APPLICATIONS)
            .insert([
                {
                    name,
                    phone,
                    school,
                    specialty: specialty || 'N/A',
                    level: level || 'N/A',
                    type: type || 'PFE',
                    period,
                    zone: zone || null,
                    status: 'En attente',
                    created_at: dateSoumission
                }
            ]);

        if (error) {
            console.error('Error inserting candidate to Supabase:', error);
            return res.status(500).json({ success: false, error: error.message });
        }

        return res.json({ success: true });
    } catch (e) {
        console.error('Apply API error:', e);
        return res.status(500).json({ success: false, error: e.message });
    }
});

// API endpoint to update candidate status (Accepté, Refusé, etc.)
app.post('/api/candidates/status', async (req, res) => {
    const { name, status } = req.body;

    try {
        const miseAJour = { status };
        if (req.body.department) miseAJour.department = req.body.department;

        const { data, error } = await supabase
            .from(TABLE_APPLICATIONS)
            .update(miseAJour)
            .eq('name', name);

        if (error) {
            console.error('Error updating candidate status in Supabase:', error);
            return res.status(500).json({ success: false, error: error.message });
        }

        return res.json({ success: true });
    } catch (e) {
        console.error('Update status API error:', e);
        return res.status(500).json({ success: false, error: e.message });
    }
});

// RH : attribue la Direction / Pôle
app.post('/api/candidates/department', async (req, res) => {
    const { name, department } = req.body;

    try {
        const { data, error } = await supabase
            .from(TABLE_APPLICATIONS)
            .update({ department })
            .eq('name', name);

        if (error) {
            console.error('Error updating department in Supabase:', error);
            return res.status(500).json({ success: false, error: error.message });
        }

        return res.json({ success: true });
    } catch (e) {
        console.error('Department API error:', e);
        return res.status(500).json({ success: false, error: e.message });
    }
});

// Affectation : projet de stage + encadrement
app.post('/api/candidates/affect', async (req, res) => {
    const { name, project, mentor } = req.body;

    try {
        const { data, error } = await supabase
            .from(TABLE_APPLICATIONS)
            .update({
                project,
                mentor,
                status: 'Attente Affectation'
            })
            .eq('name', name);

        if (error) {
            console.error('Error updating candidate affectation in Supabase:', error);
            return res.status(500).json({ success: false, error: error.message });
        }

        return res.json({ success: true });
    } catch (e) {
        console.error('Affect API error:', e);
        return res.status(500).json({ success: false, error: e.message });
    }
});

app.listen(PORT, '0.0.0.0', () => {
    console.log(`Serveur démarré sur http://0.0.0.0:${PORT}`);
});
