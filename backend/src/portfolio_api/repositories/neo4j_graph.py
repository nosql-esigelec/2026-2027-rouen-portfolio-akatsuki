"""Repository Neo4j pour les traversées de graphe (Lot B2 — R4, R5, R6, R7, R9)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from neo4j import AsyncSession

from portfolio_api.db.neo4j import get_neo4j_session


class Neo4jGraphRepository:
    """Exécute les requêtes Cypher sur le graphe Candidat - Projet - Competence."""

    def __init__(
        self,
        session_factory: Callable[[], AsyncSession] = get_neo4j_session,
    ) -> None:
        # L'injection par défaut de get_neo4j_session facilite l'usage en service
        # tout en permettant de mocker la session dans les tests unitaires (Lot E1).
        self._session_factory = session_factory

    # ------------------------------------------------------------------
    # R4 : GET /api/graph/projets/{slug}/similaires
    # ------------------------------------------------------------------
    async def get_similar_projects(
        self, projet_slug: str, limit: int = 5
    ) -> list[dict[str, Any]] | None:
        """Retourne les projets similaires (score = nb compétences communes).

        Retourne ``None`` si le projet source n'existe pas (pour lever 404),
        ou ``[]`` s'il existe mais n'a aucun projet similaire.
        """
        query = """
        MATCH (p:Projet {slug: $projet_slug})
        OPTIONAL MATCH (p)-[:UTILISE]->(c:Competence)<-[:UTILISE]-(other:Projet)
        WHERE other.slug <> $projet_slug
        WITH p, other, c
        ORDER BY c.slug ASC
        WITH p, other,
             count(DISTINCT c) AS score,
             collect(DISTINCT c.slug) AS competences_communes
        ORDER BY score DESC, other.slug ASC
        RETURN p.slug AS source_slug,
               collect(
                   CASE WHEN other IS NOT NULL THEN {
                       projet_slug: other.slug,
                       score: score,
                       competences_communes: competences_communes
                   } END
               ) AS similaires
        """
        async with self._session_factory() as session:
            result = await session.run(query, projet_slug=projet_slug)
            record = await result.single()

        if record is None:
            return None

        similaires = [item for item in record["similaires"] if item is not None]
        return similaires[:limit]

    # ------------------------------------------------------------------
    # R5 : GET /api/graph/competences/{slug}
    # ------------------------------------------------------------------
    async def get_candidate_skills_graph(
        self, candidat_slug: str
    ) -> dict[str, Any] | None:
        """Construit les tableaux ``nodes`` et ``links`` prêts à afficher pour un candidat.

        Retourne ``None`` si le candidat n'existe pas (404).
        Si le candidat n'a aucun projet, retourne uniquement son nœud et ``links: []``.
        """
        query = """
        MATCH (cand:Candidat {slug: $candidat_slug})
        OPTIONAL MATCH (cand)-[:A_REALISE]->(p:Projet)
        OPTIONAL MATCH (p)-[:UTILISE]->(comp:Competence)
        WITH cand,
             collect(DISTINCT p) AS projets,
             collect(DISTINCT {source: cand.slug, target: p.slug}) AS raw_cand_links,
             collect(DISTINCT {source: p.slug, target: comp.slug}) AS raw_proj_links
        OPTIONAL MATCH (cand)-[:A_REALISE]->(p2:Projet)-[:UTILISE]->(comp2:Competence)
        WITH cand, projets, raw_cand_links, raw_proj_links,
             comp2, count(DISTINCT p2) AS nb_projets
        ORDER BY nb_projets DESC, comp2.slug ASC
        RETURN cand.slug AS candidat_slug,
               trim(coalesce(cand.prenom, '') + ' ' + coalesce(cand.nom, '')) AS candidat_label,
               [proj IN projets WHERE proj IS NOT NULL | {
                   slug: proj.slug,
                   label: coalesce(proj.titre, proj.nom, proj.slug)
               }] AS projets,
               [item IN collect(
                   CASE WHEN comp2 IS NOT NULL THEN {
                       slug: comp2.slug,
                       label: coalesce(comp2.nom, comp2.slug),
                       nb_projets: nb_projets
                   } END
               ) WHERE item IS NOT NULL] AS competences,
               [l IN raw_cand_links WHERE l.target IS NOT NULL] AS cand_proj_links,
               [l IN raw_proj_links WHERE l.source IS NOT NULL AND l.target IS NOT NULL] AS proj_comp_links
        """
        async with self._session_factory() as session:
            result = await session.run(query, candidat_slug=candidat_slug)
            record = await result.single()

        if record is None:
            return None

        data = record.data()
        candidat_label = data["candidat_label"] or data["candidat_slug"]

        nodes: list[dict[str, Any]] = [
            {
                "id": f"candidat:{data['candidat_slug']}",
                "type": "candidat",
                "label": candidat_label,
            }
        ]

        # Tri déterministe des nœuds projets
        for proj in sorted(data["projets"], key=lambda item: item["slug"]):
            nodes.append(
                {
                    "id": f"projet:{proj['slug']}",
                    "type": "projet",
                    "label": proj["label"],
                }
            )

        for comp in data["competences"]:
            nodes.append(
                {
                    "id": f"competence:{comp['slug']}",
                    "type": "competence",
                    "label": comp["label"],
                    "nb_projets": comp["nb_projets"],
                }
            )

        links: list[dict[str, str]] = []
        for link in sorted(data["cand_proj_links"], key=lambda l: l["target"]):
            links.append(
                {
                    "source": f"candidat:{link['source']}",
                    "target": f"projet:{link['target']}",
                    "type": "A_REALISE",
                }
            )
        for link in sorted(
            data["proj_comp_links"], key=lambda l: (l["source"], l["target"])
        ):
            links.append(
                {
                    "source": f"projet:{link['source']}",
                    "target": f"competence:{link['target']}",
                    "type": "UTILISE",
                }
            )

        return {
            "candidat_slug": data["candidat_slug"],
            "nodes": nodes,
            "links": links,
        }

    # ------------------------------------------------------------------
    # R6 : GET /api/graph/competences/communes
    # ------------------------------------------------------------------
    async def get_existing_candidate_slugs(
        self, candidat_slugs: list[str]
    ) -> set[str]:
        """Vérifie quels slugs candidats existent dans Neo4j (permet de détecter un 404)."""
        query = """
        MATCH (c:Candidat)
        WHERE c.slug IN $candidat_slugs
        RETURN collect(DISTINCT c.slug) AS existing_slugs
        """
        async with self._session_factory() as session:
            result = await session.run(query, candidat_slugs=candidat_slugs)
            record = await result.single()

        if record is None:
            return set()
        return set(record["existing_slugs"])

    async def get_common_skills(
        self, candidat_slugs: list[str]
    ) -> list[dict[str, str]]:
        """Retourne les compétences utilisées par TOUS les candidats listés."""
        unique_slugs = list(dict.fromkeys(candidat_slugs))
        query = """
        MATCH (c:Candidat)-[:A_REALISE]->(:Projet)-[:UTILISE]->(comp:Competence)
        WHERE c.slug IN $candidat_slugs
        WITH comp, count(DISTINCT c.slug) AS matched_candidates
        WHERE matched_candidates = $expected_count
        RETURN comp.slug AS skill_slug,
               coalesce(comp.nom, comp.slug) AS nom
        ORDER BY skill_slug ASC
        """
        async with self._session_factory() as session:
            result = await session.run(
                query,
                candidat_slugs=unique_slugs,
                expected_count=len(unique_slugs),
            )
            return [record.data() async for record in result]

    # ------------------------------------------------------------------
    # R7 : GET /api/graph/candidats/{slug}/competences-transversales
    # ------------------------------------------------------------------
    async def get_transversal_skills(
        self, candidat_slug: str, min_projets: int = 2
    ) -> list[dict[str, Any]] | None:
        """Retourne les compétences utilisées dans au moins ``min_projets`` du candidat.

        Retourne ``None`` si le candidat n'existe pas (404).
        """
        query = """
        MATCH (cand:Candidat {slug: $candidat_slug})
        OPTIONAL MATCH (cand)-[:A_REALISE]->(p:Projet)-[:UTILISE]->(comp:Competence)
        WITH cand, comp, p
        ORDER BY p.slug ASC
        WITH cand, comp,
             count(DISTINCT p) AS nb_projets,
             collect(DISTINCT p.slug) AS projets
        ORDER BY nb_projets DESC, coalesce(comp.nom, comp.slug) ASC
        RETURN cand.slug AS candidat_slug,
               collect(
                   CASE WHEN comp IS NOT NULL AND nb_projets >= $min_projets THEN {
                       skill_slug: comp.slug,
                       nom: coalesce(comp.nom, comp.slug),
                       nb_projets: nb_projets,
                       projets: projets
                   } END
               ) AS competences
        """
        async with self._session_factory() as session:
            result = await session.run(
                query,
                candidat_slug=candidat_slug,
                min_projets=min_projets,
            )
            record = await result.single()

        if record is None:
            return None

        return [item for item in record["competences"] if item is not None]

    # ------------------------------------------------------------------
    # R9 : GET /api/competences/{slug}/preuves
    # ------------------------------------------------------------------
    async def get_skill_proofs(self, skill_slug: str) -> dict[str, Any] | None:
        """Retourne la compétence et les candidats/projets qui la mobilisent.

        Retourne ``None`` si la compétence n'existe pas (404).
        Les détails riches (prenom, nom, titre du candidat et titre des projets)
        seront ensuite hydratés depuis MongoDB dans la couche service (Lot C2).
        """
        query = """
        MATCH (comp:Competence {slug: $skill_slug})
        OPTIONAL MATCH (cand:Candidat)-[:A_REALISE]->(p:Projet)-[:UTILISE]->(comp)
        WITH comp, cand, p
        ORDER BY p.slug ASC
        WITH comp, cand,
             count(DISTINCT p) AS nb_projets,
             collect(DISTINCT p.slug) AS projet_slugs
        ORDER BY nb_projets DESC, cand.slug ASC
        RETURN comp.slug AS skill_slug,
               coalesce(comp.nom, comp.slug) AS nom,
               collect(
                   CASE WHEN cand IS NOT NULL THEN {
                       candidat_slug: cand.slug,
                       nb_projets: nb_projets,
                       projet_slugs: projet_slugs
                   } END
               ) AS candidats
        """
        async with self._session_factory() as session:
            result = await session.run(query, skill_slug=skill_slug)
            record = await result.single()

        if record is None:
            return None

        data = record.data()
        data["candidats"] = [c for c in data["candidats"] if c is not None]
        return data