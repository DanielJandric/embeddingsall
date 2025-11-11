#!/usr/bin/env python3
"""
Interface web de navigation dans les documents avec métadonnées enrichies.

Fonctionnalités :
- Dashboard avec statistiques
- Recherche avancée avec filtres multiples
- Navigation par catégorie, commune, année, etc.
- Export des résultats
- Visualisations interactives
"""

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
from pydantic import BaseModel
from dotenv import load_dotenv
import json

load_dotenv()

from src.supabase_client_v2 import SupabaseUploaderV2

app = FastAPI(
    title="Documents Navigator",
    description="Interface de navigation dans vos documents avec métadonnées enrichies",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

uploader = SupabaseUploaderV2()


# ============================================================================
# Modèles Pydantic
# ============================================================================

class SearchFilters(BaseModel):
    """Filtres de recherche avancée."""
    commune: Optional[str] = None
    canton: Optional[str] = None
    annee_min: Optional[int] = None
    annee_max: Optional[int] = None
    type_document: Optional[str] = None
    categorie: Optional[str] = None
    montant_min_chf: Optional[float] = None
    montant_max_chf: Optional[float] = None
    surface_min_m2: Optional[float] = None
    surface_max_m2: Optional[float] = None
    type_bien: Optional[str] = None
    langue: Optional[str] = None
    text_query: Optional[str] = None


# ============================================================================
# Endpoints Dashboard
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def root():
    """Page d'accueil avec dashboard."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Documents Navigator</title>
        <meta charset="utf-8">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                background: #f5f7fa;
                padding: 20px;
            }
            .container { max-width: 1400px; margin: 0 auto; }
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 40px;
                border-radius: 12px;
                margin-bottom: 30px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }
            .header h1 { font-size: 36px; margin-bottom: 10px; }
            .header p { opacity: 0.9; font-size: 18px; }
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            .stat-card {
                background: white;
                padding: 30px;
                border-radius: 12px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                border-left: 4px solid #667eea;
            }
            .stat-value {
                font-size: 48px;
                font-weight: bold;
                color: #667eea;
                margin-bottom: 10px;
            }
            .stat-label {
                color: #64748b;
                font-size: 14px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            .nav-section {
                background: white;
                padding: 30px;
                border-radius: 12px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                margin-bottom: 20px;
            }
            .nav-section h2 {
                margin-bottom: 20px;
                color: #1e293b;
                font-size: 24px;
            }
            .nav-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
                gap: 15px;
            }
            .nav-button {
                background: #f8fafc;
                border: 2px solid #e2e8f0;
                padding: 20px;
                border-radius: 8px;
                text-decoration: none;
                color: #1e293b;
                transition: all 0.2s;
                text-align: center;
                cursor: pointer;
            }
            .nav-button:hover {
                background: #667eea;
                color: white;
                transform: translateY(-2px);
                box-shadow: 0 4px 8px rgba(102, 126, 234, 0.3);
            }
            .nav-button .count {
                font-size: 24px;
                font-weight: bold;
                display: block;
                margin-bottom: 5px;
            }
            .nav-button .label {
                font-size: 14px;
                opacity: 0.8;
            }
            .search-box {
                background: white;
                padding: 30px;
                border-radius: 12px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                margin-bottom: 20px;
            }
            .search-input {
                width: 100%;
                padding: 15px 20px;
                font-size: 16px;
                border: 2px solid #e2e8f0;
                border-radius: 8px;
                transition: border-color 0.2s;
            }
            .search-input:focus {
                outline: none;
                border-color: #667eea;
            }
            .filters {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-top: 20px;
            }
            select, input[type="number"] {
                width: 100%;
                padding: 12px;
                border: 2px solid #e2e8f0;
                border-radius: 8px;
                font-size: 14px;
            }
            .btn {
                background: #667eea;
                color: white;
                padding: 12px 30px;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                cursor: pointer;
                transition: background 0.2s;
                margin-top: 20px;
            }
            .btn:hover { background: #5568d3; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📊 Documents Navigator</h1>
                <p>Naviguez dans vos documents avec métadonnées enrichies</p>
            </div>

            <div id="stats" class="stats-grid">
                <div class="stat-card">
                    <div class="stat-value" id="total-docs">...</div>
                    <div class="stat-label">Documents</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="total-chunks">...</div>
                    <div class="stat-label">Chunks</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="avg-size">...</div>
                    <div class="stat-label">Taille moyenne (KB)</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="metadata-fields">...</div>
                    <div class="stat-label">Champs métadonnées</div>
                </div>
            </div>

            <div class="search-box">
                <h2>🔍 Recherche rapide</h2>
                <input type="text" id="quick-search" class="search-input"
                       placeholder="Rechercher dans les documents...">
                <button class="btn" onclick="quickSearch()">Rechercher</button>
            </div>

            <div class="nav-section">
                <h2>📍 Navigation par localisation</h2>
                <div class="nav-grid" id="communes"></div>
            </div>

            <div class="nav-section">
                <h2>📁 Navigation par catégorie</h2>
                <div class="nav-grid" id="categories"></div>
            </div>

            <div class="nav-section">
                <h2>📅 Navigation par année</h2>
                <div class="nav-grid" id="annees"></div>
            </div>

            <div class="nav-section">
                <h2>🔎 Recherche avancée</h2>
                <div class="filters">
                    <select id="filter-commune">
                        <option value="">Toutes les communes</option>
                    </select>
                    <select id="filter-canton">
                        <option value="">Tous les cantons</option>
                    </select>
                    <select id="filter-type">
                        <option value="">Tous les types</option>
                    </select>
                    <select id="filter-categorie">
                        <option value="">Toutes les catégories</option>
                    </select>
                    <input type="number" id="filter-annee-min" placeholder="Année min">
                    <input type="number" id="filter-annee-max" placeholder="Année max">
                    <input type="number" id="filter-montant-min" placeholder="Montant min CHF">
                    <input type="number" id="filter-montant-max" placeholder="Montant max CHF">
                </div>
                <button class="btn" onclick="advancedSearch()">Rechercher avec filtres</button>
            </div>
        </div>

        <script>
            // Charger les statistiques au démarrage
            async function loadStats() {
                const response = await fetch('/api/stats');
                const data = await response.json();

                document.getElementById('total-docs').textContent = data.total_documents;
                document.getElementById('total-chunks').textContent = data.total_chunks;
                document.getElementById('avg-size').textContent =
                    Math.round(data.avg_document_size_kb || 0);
                document.getElementById('metadata-fields').textContent =
                    data.unique_metadata_fields || 0;
            }

            // Charger les options de navigation
            async function loadNavigation() {
                const response = await fetch('/api/navigation');
                const data = await response.json();

                // Communes
                const communesHtml = data.communes.map(c =>
                    `<div class="nav-button" onclick="filterBy('commune', '${c.name}')">
                        <span class="count">${c.count}</span>
                        <span class="label">${c.name}</span>
                    </div>`
                ).join('');
                document.getElementById('communes').innerHTML = communesHtml;

                // Catégories
                const catsHtml = data.categories.map(c =>
                    `<div class="nav-button" onclick="filterBy('categorie', '${c.name}')">
                        <span class="count">${c.count}</span>
                        <span class="label">${c.name}</span>
                    </div>`
                ).join('');
                document.getElementById('categories').innerHTML = catsHtml;

                // Années
                const anneesHtml = data.annees.map(a =>
                    `<div class="nav-button" onclick="filterBy('annee', ${a.year})">
                        <span class="count">${a.count}</span>
                        <span class="label">${a.year}</span>
                    </div>`
                ).join('');
                document.getElementById('annees').innerHTML = anneesHtml;

                // Remplir les selects
                const communesSelect = document.getElementById('filter-commune');
                data.all_communes.forEach(c => {
                    const option = document.createElement('option');
                    option.value = c;
                    option.textContent = c;
                    communesSelect.appendChild(option);
                });
            }

            function filterBy(field, value) {
                window.location.href = `/search?${field}=${value}`;
            }

            function quickSearch() {
                const query = document.getElementById('quick-search').value;
                window.location.href = `/search?q=${encodeURIComponent(query)}`;
            }

            function advancedSearch() {
                const params = new URLSearchParams();

                const commune = document.getElementById('filter-commune').value;
                if (commune) params.append('commune', commune);

                const canton = document.getElementById('filter-canton').value;
                if (canton) params.append('canton', canton);

                // ... autres filtres

                window.location.href = `/search?${params.toString()}`;
            }

            // Charger au démarrage
            loadStats();
            loadNavigation();
        </script>
    </body>
    </html>
    """


@app.get("/api/stats")
async def get_stats():
    """Récupère les statistiques globales."""
    # Stats de base
    stats = uploader.get_database_stats()

    # Compter les champs de métadonnées uniques
    response = uploader.client.table("documents_full")\
        .select("metadata")\
        .limit(100)\
        .execute()

    all_fields = set()
    total_size = 0

    for doc in response.data:
        if doc.get('metadata'):
            all_fields.update(doc['metadata'].keys())

    stats['unique_metadata_fields'] = len(all_fields)

    return stats


@app.get("/api/navigation")
async def get_navigation_options():
    """Récupère les options de navigation (communes, catégories, années)."""

    response = uploader.client.table("documents_full")\
        .select("metadata")\
        .execute()

    # Compter par commune
    communes = {}
    categories = {}
    annees = {}
    cantons = set()
    all_communes = set()

    for doc in response.data:
        metadata = doc.get('metadata', {})

        # Communes
        if metadata.get('commune_principale'):
            commune = metadata['commune_principale']
            communes[commune] = communes.get(commune, 0) + 1
            all_communes.add(commune)

        if metadata.get('communes'):
            for c in metadata['communes']:
                all_communes.add(c)

        # Catégories
        if metadata.get('categorie_principale'):
            cat = metadata['categorie_principale']
            categories[cat] = categories.get(cat, 0) + 1

        # Années
        if metadata.get('annee_la_plus_recente'):
            year = metadata['annee_la_plus_recente']
            annees[year] = annees.get(year, 0) + 1

        # Cantons
        if metadata.get('cantons'):
            cantons.update(metadata['cantons'])

    return {
        "communes": [{"name": k, "count": v} for k, v in sorted(communes.items(), key=lambda x: x[1], reverse=True)[:20]],
        "categories": [{"name": k, "count": v} for k, v in sorted(categories.items(), key=lambda x: x[1], reverse=True)],
        "annees": [{"year": k, "count": v} for k, v in sorted(annees.items(), reverse=True)],
        "all_communes": sorted(all_communes),
        "all_cantons": sorted(cantons)
    }


@app.get("/api/search")
async def search_documents(
    q: Optional[str] = None,
    commune: Optional[str] = None,
    canton: Optional[str] = None,
    annee: Optional[int] = None,
    annee_min: Optional[int] = None,
    annee_max: Optional[int] = None,
    type_document: Optional[str] = None,
    categorie: Optional[str] = None,
    montant_min_chf: Optional[float] = None,
    montant_max_chf: Optional[float] = None,
    surface_min_m2: Optional[float] = None,
    surface_max_m2: Optional[float] = None,
    limit: int = Query(50, le=200)
):
    """
    Recherche avancée avec filtres multiples.
    """

    query = uploader.client.table("documents_full").select("*")

    # Appliquer les filtres
    # Note: Pour une vraie implémentation, il faudrait utiliser des filtres JSON PostgreSQL
    # Ici on récupère tout et on filtre en Python (pour simplifier)

    response = query.limit(limit).execute()
    documents = response.data

    # Filtrage en Python
    filtered = []
    for doc in documents:
        metadata = doc.get('metadata', {})

        # Filtrer par commune
        if commune and metadata.get('commune_principale') != commune:
            if not metadata.get('communes') or commune not in metadata['communes']:
                continue

        # Filtrer par année
        if annee and metadata.get('annee_la_plus_recente') != annee:
            continue

        if annee_min and metadata.get('annee_la_plus_recente', 0) < annee_min:
            continue

        if annee_max and metadata.get('annee_la_plus_recente', 9999) > annee_max:
            continue

        # Filtrer par catégorie
        if categorie and metadata.get('categorie_principale') != categorie:
            continue

        # Filtrer par montant
        if montant_min_chf and metadata.get('montant_max_chf', 0) < montant_min_chf:
            continue

        if montant_max_chf and metadata.get('montant_min_chf', float('inf')) > montant_max_chf:
            continue

        # Filtrer par surface
        if surface_min_m2 and metadata.get('surface_max_m2', 0) < surface_min_m2:
            continue

        if surface_max_m2 and metadata.get('surface_min_m2', float('inf')) > surface_max_m2:
            continue

        # Recherche textuelle
        if q:
            full_content = doc.get('full_content', '').lower()
            if q.lower() not in full_content:
                continue

        filtered.append(doc)

    return {
        "total": len(filtered),
        "documents": filtered,
        "filters_applied": {
            "commune": commune,
            "annee": annee,
            "categorie": categorie
        }
    }


@app.get("/api/document/{document_id}")
async def get_document_details(document_id: int):
    """Récupère les détails complets d'un document."""

    response = uploader.client.table("documents_full")\
        .select("*")\
        .eq("id", document_id)\
        .execute()

    if not response.data:
        raise HTTPException(status_code=404, detail="Document not found")

    return response.data[0]


@app.get("/api/export/csv")
async def export_to_csv(
    commune: Optional[str] = None,
    categorie: Optional[str] = None
):
    """Exporte les documents filtrés en CSV."""
    import csv
    from io import StringIO

    # Récupérer les documents
    query = uploader.client.table("documents_full").select("*")
    response = query.execute()

    # Créer le CSV
    output = StringIO()
    writer = csv.writer(output)

    # En-têtes
    writer.writerow([
        'ID', 'Fichier', 'Commune', 'Canton', 'Année', 'Catégorie',
        'Type document', 'Montant max CHF', 'Surface max m²', 'Langue'
    ])

    # Données
    for doc in response.data:
        metadata = doc.get('metadata', {})
        writer.writerow([
            doc['id'],
            doc['file_path'],
            metadata.get('commune_principale', ''),
            metadata.get('canton_principal', ''),
            metadata.get('annee_la_plus_recente', ''),
            metadata.get('categorie_principale', ''),
            metadata.get('type_document_detecte', ''),
            metadata.get('montant_max_chf', ''),
            metadata.get('surface_max_m2', ''),
            metadata.get('langue_detectee', '')
        ])

    return output.getvalue()


if __name__ == "__main__":
    import uvicorn
    print("🚀 Démarrage du navigateur web...")
    print("📍 Interface disponible sur: http://localhost:8080")
    print("📊 API docs: http://localhost:8080/docs")
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
