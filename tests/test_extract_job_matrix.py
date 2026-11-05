import csv
import json
import tempfile
import unittest
from pathlib import Path

from tools.extract_job_matrix import (
    MATRIX_COLUMNS,
    export_matrix,
    extract_matrix_from_text,
)


class ExtractJobMatrixTests(unittest.TestCase):
    def test_extracts_all_8_criteria_from_french_posting(self):
        sample_posting = """
        Résumé : Rattaché à la Direction Data, vous pilotez la plateforme analytique.
        Vos missions :
        - Concevoir et maintenir les pipelines ETL en Python et SQL sur Snowflake
        - Accompagner les équipes métier dans la définition des KPIs
        Compétences attendues :
        - Solide maîtrise de la modélisation de données et du Cloud GCP
        - Rigueur, autonomie et esprit d'équipe
        Outils et technologies :
        - Python, SQL, Snowflake, dbt, Airflow, GitLab, Power BI
        Profil recherché :
        - Formation Bac +5 avec 5 ans d'expérience dans le secteur bancaire ou assurance
        Télétravail partiel (2 jours par semaine).
        Rémunération : 55 000 - 65 000 € / an selon profil.
        """
        row = extract_matrix_from_text(
            sample_posting,
            title="Senior Data Engineer H/F",
            company="FinTech Corp",
            location="Paris 9e - 75",
            url="https://www.hellowork.com/fr-fr/emplois/99999999.html",
            portal="HelloWork",
            score_fit="85",
        )

        self.assertEqual(row["intitule_offre"], "Senior Data Engineer H/F")
        self.assertEqual(row["entreprise"], "FinTech Corp")
        self.assertIn("Paris 9e - 75", row["localisation_teletravail"])
        self.assertIn("Hybride", row["localisation_teletravail"])
        self.assertIn("Concevoir et maintenir les pipelines ETL", row["missions_principales"])
        self.assertIn("modélisation de données", row["competences_attendues"])
        self.assertIn("Snowflake", row["outils_technologies"])
        self.assertIn("Python", row["outils_technologies"])
        self.assertIn("5 ans d'expérience", row["experience_sectorielle"])
        self.assertIn("55 000 - 65 000 € / an", row["salaire"])
        self.assertEqual(row["score_fit"], "85")
        self.assertEqual(row["portail"], "HelloWork")

    def test_exports_csv_with_utf8_bom_and_json_with_dedup(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            csv_path = tmp / "matrix.csv"
            json_path = tmp / "matrix.json"

            row1 = {
                "intitule_offre": "Data Analyst H/F",
                "entreprise": "Acme France",
                "localisation_teletravail": "Lyon (Hybride)",
                "missions_principales": "Créer des dashboards ; Automatiser les reportings",
                "competences_attendues": "Analyse statistique ; Communication",
                "outils_technologies": "SQL, Python, Power BI",
                "experience_sectorielle": "3 ans d'expérience en retail",
                "salaire": "45 000 - 52 000 € / an",
                "score_fit": "78",
                "portail": "HelloWork",
                "url": "https://www.hellowork.com/fr-fr/emplois/12345.html",
            }
            summary1 = export_matrix([row1], csv_path=csv_path, json_path=json_path)
            self.assertEqual(summary1["added"], 1)
            self.assertEqual(summary1["total"], 1)

            # Re-exporting same URL updates in place instead of duplicating
            row1_updated = {**row1, "score_fit": "82"}
            summary2 = export_matrix([row1_updated], csv_path=csv_path, json_path=json_path)
            self.assertEqual(summary2["added"], 0)
            self.assertEqual(summary2["updated"], 1)
            self.assertEqual(summary2["total"], 1)

            raw_bytes = csv_path.read_bytes()
            self.assertTrue(raw_bytes.startswith(b"\xef\xbb\xbf"), "CSV must start with UTF-8 BOM for Google Sheets/Excel")

            with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
                reader = list(csv.reader(fh))
            self.assertEqual(reader[0], [label for _, label in MATRIX_COLUMNS])
            self.assertEqual(len(reader), 2)
            self.assertEqual(reader[1][0], "Data Analyst H/F")

            doc = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(doc["total_offers"], 1)
            self.assertEqual(doc["offers"][0]["score_fit"], "82")


if __name__ == "__main__":
    unittest.main()
