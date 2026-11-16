# MPD (postgresql)

## Medicament

| Colonne | Type | NULL | Clé | Référence |
|---|---|---|---|---|
| idMedicament | INT | non | PK |  |
| nomCommercial | VARCHAR(50) | oui |  |  |
| prix | DECIMAL(10,2) | oui |  |  |

## Laboratoire

| Colonne | Type | NULL | Clé | Référence |
|---|---|---|---|---|
| idLabo | INT | non | PK |  |
| raisonSociale | VARCHAR(50) | oui |  |  |
| ville | VARCHAR(50) | oui |  |  |

## Assurance

| Colonne | Type | NULL | Clé | Référence |
|---|---|---|---|---|
| idAssurance | INT | non | PK |  |
| nom | VARCHAR(50) | oui |  |  |
| tauxRemboursement | DECIMAL(5,2) | oui |  |  |

## Patient

| Colonne | Type | NULL | Clé | Référence |
|---|---|---|---|---|
| idPatient | INT | non | PK |  |
| nom | VARCHAR(50) | oui |  |  |
| prenom | VARCHAR(50) | oui |  |  |
| dateNaissance | DATE | oui |  |  |
| numeroSecu | VARCHAR(15) | oui |  |  |
| idAssurance | INT | oui | FK | Assurance(idAssurance) |
| numeroContrat | VARCHAR(30) | oui |  |  |

Index conseillés : `idAssurance`

## Medecin

| Colonne | Type | NULL | Clé | Référence |
|---|---|---|---|---|
| idMedecin | INT | non | PK |  |
| nom | VARCHAR(50) | oui |  |  |
| specialite | VARCHAR(50) | oui |  |  |
| telephone | VARCHAR(20) | oui |  |  |
| idService | INT | non | FK | Service(idService) |
| idMedecin_superviser | INT | oui | FK | Medecin(idMedecin) |

Index conseillés : `idService`, `idMedecin_superviser`

## Service

| Colonne | Type | NULL | Clé | Référence |
|---|---|---|---|---|
| idService | INT | non | PK |  |
| libelle | VARCHAR(50) | oui |  |  |
| etage | INT | oui |  |  |
| idMedecin | INT | non | FK | Medecin(idMedecin) |

Index conseillés : `idMedecin`

## Chambre

| Colonne | Type | NULL | Clé | Référence |
|---|---|---|---|---|
| idChambre | INT | non | PK |  |
| numero | VARCHAR(10) | oui |  |  |
| tarifJour | DECIMAL(8,2) | oui |  |  |
| idService | INT | non | FK | Service(idService) |

Index conseillés : `idService`

## Lit

| Colonne | Type | NULL | Clé | Référence |
|---|---|---|---|---|
| idLit | INT | non | PK |  |
| type | VARCHAR(50) | oui |  |  |
| idChambre | INT | non | FK | Chambre(idChambre) |

Index conseillés : `idChambre`

## Consultation

| Colonne | Type | NULL | Clé | Référence |
|---|---|---|---|---|
| idConsultation | INT | non | PK |  |
| dateConsult | DATE | oui |  |  |
| motif | TEXT | oui |  |  |
| idPatient | INT | non | FK | Patient(idPatient) |
| idMedecin | INT | non | FK | Medecin(idMedecin) |

Index conseillés : `idPatient`, `idMedecin`

## Ordonnance

| Colonne | Type | NULL | Clé | Référence |
|---|---|---|---|---|
| idOrdonnance | INT | non | PK |  |
| dateEmission | DATE | oui |  |  |
| idConsultation | INT | non | FK | Consultation(idConsultation) |

Index conseillés : `idConsultation`

## Infirmier

| Colonne | Type | NULL | Clé | Référence |
|---|---|---|---|---|
| idInfirmier | INT | non | PK |  |
| nom | VARCHAR(50) | oui |  |  |
| grade | VARCHAR(50) | oui |  |  |
| idService | INT | non | FK | Service(idService) |

Index conseillés : `idService`

## Examen

| Colonne | Type | NULL | Clé | Référence |
|---|---|---|---|---|
| idExamen | INT | non | PK |  |
| typeExamen | VARCHAR(50) | oui |  |  |
| resultat | TEXT | oui |  |  |
| idLabo | INT | non | FK | Laboratoire(idLabo) |
| idConsultation | INT | non | FK | Consultation(idConsultation) |

Index conseillés : `idLabo`, `idConsultation`

## occuper

| Colonne | Type | NULL | Clé | Référence |
|---|---|---|---|---|
| idPatient | INT | non | PK, FK | Patient(idPatient) |
| idLit | INT | non | PK, FK | Lit(idLit) |
| dateEntree | DATE | oui |  |  |
| dateSortie | DATE | oui |  |  |

## comporter

| Colonne | Type | NULL | Clé | Référence |
|---|---|---|---|---|
| idOrdonnance | INT | non | PK, FK | Ordonnance(idOrdonnance) |
| idMedicament | INT | non | PK, FK | Medicament(idMedicament) |
| posologie | VARCHAR(255) | oui |  |  |
| dureeJours | INT | oui |  |  |

## administrer

| Colonne | Type | NULL | Clé | Référence |
|---|---|---|---|---|
| idInfirmier | INT | non | PK, FK | Infirmier(idInfirmier) |
| idPatient | INT | non | PK, FK | Patient(idPatient) |
| idMedicament | INT | non | PK, FK | Medicament(idMedicament) |
| dateHeure | TIMESTAMP | oui |  |  |
| dose | VARCHAR(50) | oui |  |  |
