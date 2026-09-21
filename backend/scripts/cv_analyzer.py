import sys
import json

def analyze_cv(text):
    skills_found = []
    text_lower = text.lower()
    
    keywords = ["logistique", "transport", "portuaire", "déchargement",
     "manutention", "sécurité", "rh", "gestion"]
    
    for kw in keywords:
        if kw in text_lower:
            skills_found.append(kw.capitalize())
            
    return {
        "status": "success",
        "analysis": {
            "skills": skills_found,
            "score": len(skills_found) * 10,
            "recommendation": "Candidat potentiel" if len(skills_found) > 2 else "A examiner"
        },
        "python_version": sys.version
    }

if __name__ == "__main__":
    input_text = sys.argv[1] if len(sys.argv) > 1 else ""
    result = analyze_cv(input_text)
    print(json.dumps(result))
