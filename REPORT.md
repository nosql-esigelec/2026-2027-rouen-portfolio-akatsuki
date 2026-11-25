# 📦 REPORT — Portfolio Polyglotte · Équipe Akatsuki

> Rendu du projet NoSQL (ESIGELEC Rouen). Une API FastAPI commune expose un portfolio
> d'ingénieur en s'appuyant sur **MongoDB** (fiches candidats/projets) et **Neo4j**
> (graphe de relations). Chaque membre développe en plus son propre frontend.

| | |
|---|---|
| **Équipe** | Akatsuki (5 membres) |
| **Dépôt** | `nosql-esigelec/2026-2027-rouen-portfolio-akatsuki` |
| **Backend déployé** | <https://2026-2027-rouen-portfolio-akatsuki.vercel.app> |
| **Swagger / OpenAPI** | <https://2026-2027-rouen-portfolio-akatsuki.vercel.app/docs> |

---

## 1. Documents de spécification (à jour)

Les deux documents font foi et sont alignés avec le code final (routes, modèles, index, requêtes Cypher) :

- **[ARCHITECTURE.md](./ARCHITECTURE.md)** — modèles MongoDB & Neo4j, index, pipeline d'agrégation (R3), requêtes Cypher clés (R4/R5/R6), règles de cohérence inter-bases.
- **[API_ROUTES.md](./API_ROUTES.md)** — contrat d'API consommé par tous les frontends (9 routes, codes d'erreur, pagination).

La numérotation `R#` est homogène entre les deux documents et correspond à l'ordre des routes.

---

## 2. Backend déployé & accès aux bases

- **API** : <https://2026-2027-rouen-portfolio-akatsuki.vercel.app>
- **Documentation interactive (Swagger)** : <https://2026-2027-rouen-portfolio-akatsuki.vercel.app/docs> — toutes les routes y sont testables directement.
- **Hébergement** : backend FastAPI sur **Vercel**, connecté à **MongoDB Atlas** (base documentaire) et **Neo4j Aura** (graphe).
- **Accès enseignant** : l'API, sa documentation `/docs` et toutes les routes de la section 3 sont **publiques et vérifiables directement** via les liens ci-dessous. Une invitation au projet Vercel peut être envoyée par e-mail sur demande.

> Santé de l'API : `GET /api/health` → `{"status":"ok"}`
> <https://2026-2027-rouen-portfolio-akatsuki.vercel.app/api/health>

---

## 3. Validation de la connexion aux BDD (endpoints & requêtes)

Les 9 routes du contrat sont déployées et renvoient de vraies données. Chaque lien ci-dessous est **cliquable** et interroge la ou les bases indiquées.

| # | Route (exemple cliquable) | Base(s) | Vérifie |
|---|---|---|---|
| R1 | [`/api/candidats/erwann-nobime`](https://2026-2027-rouen-portfolio-akatsuki.vercel.app/api/candidats/erwann-nobime) | MongoDB | lecture d'une fiche candidat |
| R2 | [`/api/candidats/erwann-nobime/projets?page=1&size=5`](https://2026-2027-rouen-portfolio-akatsuki.vercel.app/api/candidats/erwann-nobime/projets?page=1&size=5) | MongoDB | projets paginés + filtre indexé |
| R3 | [`/api/candidats/erwann-nobime/stats`](https://2026-2027-rouen-portfolio-akatsuki.vercel.app/api/candidats/erwann-nobime/stats) | MongoDB | **pipeline d'agrégation** par compétence |
| R4 | [`/api/graph/projets/automatisation-ia-scraping-offres/similaires?limit=3`](https://2026-2027-rouen-portfolio-akatsuki.vercel.app/api/graph/projets/automatisation-ia-scraping-offres/similaires?limit=3) | Neo4j → MongoDB | projets similaires (compétences partagées) |
| R5 | [`/api/graph/competences/erwann-nobime`](https://2026-2027-rouen-portfolio-akatsuki.vercel.app/api/graph/competences/erwann-nobime) | Neo4j | graphe `nodes`+`links` d'un candidat |
| R6 | [`/api/graph/competences/communes?candidats=erwann-nobime,rayan-marmouri`](https://2026-2027-rouen-portfolio-akatsuki.vercel.app/api/graph/competences/communes?candidats=erwann-nobime,rayan-marmouri) | Neo4j | intersection de compétences entre candidats |
| R7 | [`/api/graph/candidats/erwann-nobime/competences-transversales?min_projets=2`](https://2026-2027-rouen-portfolio-akatsuki.vercel.app/api/graph/candidats/erwann-nobime/competences-transversales?min_projets=2) | Neo4j | compétences récurrentes (≥ 2 projets) |
| R8 | [`/api/projets/recents?limit=5`](https://2026-2027-rouen-portfolio-akatsuki.vercel.app/api/projets/recents?limit=5) | MongoDB | derniers projets de l'équipe (index date) |
| R9 | [`/api/competences/xgboost/preuves`](https://2026-2027-rouen-portfolio-akatsuki.vercel.app/api/competences/xgboost/preuves) | Neo4j → MongoDB | qui prouve une compétence |

**Gestion d'erreurs vérifiable** (conforme au contrat) :

- `404` ressource inexistante — [`/api/candidats/inexistant-xyz`](https://2026-2027-rouen-portfolio-akatsuki.vercel.app/api/candidats/inexistant-xyz)
- `400` paramètre invalide (route 6, < 2 candidats) — [`/api/graph/competences/communes?candidats=erwann-nobime`](https://2026-2027-rouen-portfolio-akatsuki.vercel.app/api/graph/competences/communes?candidats=erwann-nobime)

> Preuve que **les deux bases** répondent : R3 passe par une agrégation **MongoDB** ;
> R5/R6/R7 exécutent des traversées **Neo4j** ; R4/R9 combinent les deux
> (slugs depuis Neo4j, puis hydratation des fiches depuis MongoDB).

### Lancer et valider en local (optionnel)

```bash
just up        # MongoDB (27018) + Neo4j (7475 / 7688) via Docker
just install   # dépendances backend (uv)
just seed      # peuple MongoDB + Neo4j depuis data/ (idempotent)
just dev       # API sur http://localhost:8000/docs
just test      # tests unitaires (toutes les couches)
```

---

## 4. Portfolios déployés (1 par personne)

| Membre | Portfolio déployé |
|---|---|
| Erwann | <https://portfolio-erwann.vercel.app> |
| Donatien | <https://donatien-tovihouande.vercel.app> |
| Manuella | <https://manuella-gbedan.vercel.app> |
| Andréa | <https://the-data-museum.vercel.app> |
| Rayan | <https://portfolio-rayan-orcin.vercel.app> |

Tous les frontends consomment la **même API commune** (section 2) ; chacun est un projet Vercel
indépendant pointant sur son dossier `frontends/frontend-<pseudo>/`.
