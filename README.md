# looping-agent

Lire, modifier et créer des fichiers **Looping** (`.loo`, MCD Merise) sans ouvrir Looping :
en Python, en ligne de commande, ou depuis une IA (Claude Desktop, Claude Code, Cursor…) grâce à
un serveur **MCP**.

Exemple de demande à une IA :
> « Crée-moi un MCD d'une bibliothèque dans `biblio.loo`, puis donne-moi le MLD, le MPD et le script PostgreSQL. »

Le fichier produit s'ouvre ensuite normalement dans Looping.

Python 3.10+ uniquement, aucune dépendance.

> Projet indépendant, sans lien avec l'auteur de Looping. Looping est disponible gratuitement sur
> [looping-mcd.fr](https://www.looping-mcd.fr) et n'est pas inclus dans ce dépôt.

## Ce que ça fait

- Lire un `.loo` en JSON : entités, attributs (type, identifiant), associations, liens, cardinalités.
- Modifier : ajouter, renommer, déplacer ou supprimer une entité ou une association ; ajouter,
  modifier ou supprimer un attribut ; ajouter ou supprimer un lien ; changer une cardinalité.
- Créer un MCD complet à partir d'un JSON.
- Générer le **MLD**, le **MPD** (tableau des colonnes, types, NULL, PK, FK) et le **script SQL**
  (`generic`, `mysql`, `postgresql`, `sqlite`).
- Avant la première modification d'un fichier, une copie `<fichier>.loo.bak` est gardée.

## Installation

```bash
pip install git+https://github.com/Dr1mS/looping-agent
```

Ça installe deux commandes : `looping-agent` (ligne de commande) et `looping-mcp` (serveur MCP).
Sous Windows, si `pip` n'est pas reconnu, utilise `py -m pip install ...`.

Sans installation, depuis un clone du dépôt : `python3 -m looping_agent ...`.

## Utiliser avec une IA (MCP)

### Claude Desktop

Ouvre le fichier de configuration :

- Windows : `%APPDATA%\Claude\claude_desktop_config.json`
- macOS : `~/Library/Application Support/Claude/claude_desktop_config.json`
- Linux : `~/.config/Claude/claude_desktop_config.json`

Ajoute dans `mcpServers` :

```json
{
  "mcpServers": {
    "looping": { "command": "looping-mcp" }
  }
}
```

Si Claude Desktop ne trouve pas `looping-mcp`, mets le chemin complet donné par
`where looping-mcp` (Windows) ou `which looping-mcp` (macOS/Linux).

Quitte complètement Claude Desktop, puis relance-le. Les outils `loo_*` apparaissent dans le menu
des outils.

**Où sont les fichiers ?** Claude Desktop lance le serveur dans son propre dossier, souvent en
lecture seule. Un chemin relatif (`biblio.loo`) est donc enregistré dans le dossier de travail
`~/Documents/Looping` (créé au besoin). Chemins complets et `~/...` marchent aussi. Chaque résultat
donne le chemin complet du fichier à ouvrir dans Looping. Pour changer de dossier :

```json
"looping": { "command": "looping-mcp", "env": { "LOOPING_DIR": "C:\\Users\\moi\\MCD" } }
```

### Claude Code

```bash
claude mcp add --scope user looping -- looping-mcp
```

Le dépôt contient aussi un `.mcp.json` : en lançant `claude` dans le dossier du dépôt, le serveur
est proposé automatiquement.

### Outils disponibles

`loo_read`, `loo_new`, `loo_apply_spec`, `loo_add_entity`, `loo_add_association`, `loo_add_link`,
`loo_set_card`, `loo_remove_link`, `loo_add_attribute`, `loo_update_attribute`,
`loo_remove_attribute`, `loo_rename`, `loo_move`, `loo_remove`, `loo_mld`, `loo_mpd`, `loo_sql`.

## Ligne de commande

```bash
looping-agent read  modele.loo
looping-agent new   modele.loo --spec spec.json
looping-agent add_entity modele.loo --name Client \
    --attributes '[{"name":"idClient","type":"INT","pk":true},"nom",{"name":"email","type":"VARCHAR(120)"}]'
looping-agent add_association modele.loo --name passer
looping-agent add_link modele.loo --entity Client --association passer --card 0,n
looping-agent set_card modele.loo --entity Client --association passer --card 1,n
looping-agent mld modele.loo
looping-agent mpd modele.loo --dialect postgresql --out mpd.md
looping-agent sql modele.loo --dialect postgresql --out schema.sql
looping-agent --help
```

Format d'une spec (`new`, `apply_spec`), identique à la sortie de `read` :

```json
{
  "entities": [
    {"name": "Client", "x": 100, "y": 300,
     "attributes": [{"name": "idClient", "type": "INT", "pk": true}, "nom"]},
    {"name": "Commande", "attributes": [{"name": "idCommande", "type": "INT", "pk": true}]}
  ],
  "associations": [{"name": "passer", "attributes": []}],
  "links": [
    {"entity": "Client", "association": "passer", "card": "0,n"},
    {"entity": "Commande", "association": "passer", "card": "1,1"}
  ]
}
```

Un attribut donné comme simple texte est un `VARCHAR(50)`. Les positions `x` / `y` sont facultatives.

## En Python

```python
from looping_agent import Model
m = Model.open("modele.loo")
m.add_entity("Produit", [{"name": "idProduit", "type": "INT", "pk": True}, "libelle"])
m.add_association("contenir")
m.add_link("Produit", "contenir", "1,n")
m.save()
```

## Exemples

- `examples/demo_agent.loo` : petit MCD (Étudiant, Cours, Enseignant).
- `examples/hopital/` : MCD de 12 entités et 15 associations (dont une ternaire et une réflexive),
  avec la spec JSON, le MLD, le MPD et les scripts SQL générés.

## Ce qui est vérifié

- Relecture/réécriture **à l'octet près** de 4 vrais fichiers Looping (version de fichier 47,
  40 à 128 objets, héritage compris).
- Les fichiers générés s'ouvrent dans Looping (version du 06/03/2025, testé sous Wine 9 sur Linux)
  avec les entités, types, liens et cardinalités corrects.
- Le script de `examples/hopital` s'exécute sans erreur sur SQLite et PostgreSQL. MySQL n'a pas été testé.

## Limites

- Versions de fichier 42 à 51 seulement. Un fichier plus ancien : l'ouvrir et l'enregistrer une fois dans Looping.
- Pas encore décodés : titres, textes libres, formes, images, crayon, CIF, contraintes, règles, flèches.
  Un fichier qui en contient renvoie une erreur claire et n'est pas modifié.
- L'héritage est conservé dans le fichier, mais il n'apparaît pas dans le JSON et le SQL l'ignore.
- Types écrits nativement : `VARCHAR(n)`, `TEXT`, `INT`, `DECIMAL(p,s)`, `DATE`. Les autres
  (`DATETIME`, `BOOLEAN`…) sont écrits en « type libre » Looping avec le texte donné.
- Identification relative `(R)` non gérée.
- Le MLD/SQL est calculé par cet outil selon les règles Merise classiques, pas par Looping.
  Pour le résultat officiel, utilise le bouton **MLD** et l'export SQL de Looping.

## Comment ça marche

Le format `.loo` est une sérialisation MFC `CArchive`. Il a été décodé par rétro-ingénierie de
`Looping.exe` avec Ghidra, dans un but d'interopérabilité. Le détail champ par champ, avec les
adresses des fonctions de l'exe, est dans les docstrings de `looping_agent/archive.py` et
`looping_agent/model.py`.

## Tests

```bash
python3 -m unittest discover -s tests -t .
```

Pour tester aussi la relecture à l'octet près sur tes propres fichiers, mets des `.loo` dans
`tests/fixtures/` avant de lancer la commande.

## Licence

MIT
