"""Run: python3 -m unittest discover -s tests   (from the project folder)

Put real .loo files in tests/fixtures/ to also check byte-exact round trips.
"""
import glob
import os
import tempfile
import unittest

from looping_agent import archive as A, ops, sql
from looping_agent.model import Model

HERE = os.path.dirname(__file__)


class RoundTrip(unittest.TestCase):
    def test_fixtures_byte_exact(self):
        files = glob.glob(os.path.join(HERE, "fixtures", "*.loo"))
        for f in files:
            with self.subTest(f=f):
                data = open(f, "rb").read()
                self.assertEqual(A.write(A.read(data)), data)


class Build(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "m.loo")

    def test_build_edit_sql(self):
        ops.new(self.path, {
            "entities": [
                {"name": "Auteur", "attributes": [{"name": "idAuteur", "type": "INT", "pk": True}, "nom"]},
                {"name": "Livre", "attributes": [{"name": "idLivre", "type": "INT", "pk": True},
                                                 {"name": "prix", "type": "DECIMAL(6,2)"}]},
                {"name": "Genre", "attributes": [{"name": "idGenre", "type": "INT", "pk": True}]},
            ],
            "associations": [{"name": "ecrire"}, {"name": "classer"}],
            "links": [
                {"entity": "Auteur", "association": "ecrire", "card": "1,n"},
                {"entity": "Livre", "association": "ecrire", "card": "1,1"},
                {"entity": "Livre", "association": "classer", "card": "0,n"},
                {"entity": "Genre", "association": "classer", "card": "1,n"},
            ],
        })
        ops.add_attribute(self.path, owner="Livre", name="parution", type="DATE")
        ops.update_attribute(self.path, owner="Auteur", name="nom", type="VARCHAR(80)")
        ops.set_card(self.path, entity="Livre", association="ecrire", card="0,1")
        d = ops.read(self.path)
        self.assertEqual(len(d["entities"]), 3)
        self.assertEqual(len(d["links"]), 4)
        cards = {(l["entity"], l["association"]): l["card"] for l in d["links"]}
        self.assertEqual(cards[("Livre", "ecrire")], "0,1")
        auteur = next(e for e in d["entities"] if e["name"] == "Auteur")
        self.assertEqual(auteur["attributes"][1]["type"], "VARCHAR(80)")
        ddl = sql.sql_ddl(d)
        self.assertIn("FOREIGN KEY(idAuteur) REFERENCES Auteur(idAuteur)", ddl)
        self.assertIn("PRIMARY KEY(idLivre, idGenre)", ddl)
        # saved bytes are stable: read + write gives the same file
        data = open(self.path, "rb").read()
        self.assertEqual(A.write(A.read(data)), data)

    def test_remove(self):
        m = Model.new()
        m.add_entity("A", [{"name": "id", "type": "INT", "pk": True}])
        m.add_association("r")
        m.add_link("A", "r", "1,n")
        m.remove("A")
        m.save(self.path)
        d = Model.open(self.path).to_dict()
        self.assertEqual(d["entities"], [])
        self.assertEqual(d["links"], [])
        self.assertEqual(len(A.load(self.path).objects), 4)  # association + its 3 texts


if __name__ == "__main__":
    unittest.main()
