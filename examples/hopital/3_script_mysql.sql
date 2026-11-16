CREATE TABLE Medicament(
   idMedicament INT NOT NULL,
   nomCommercial VARCHAR(50),
   prix DECIMAL(10,2),
   PRIMARY KEY(idMedicament)
);

CREATE TABLE Laboratoire(
   idLabo INT NOT NULL,
   raisonSociale VARCHAR(50),
   ville VARCHAR(50),
   PRIMARY KEY(idLabo)
);

CREATE TABLE Assurance(
   idAssurance INT NOT NULL,
   nom VARCHAR(50),
   tauxRemboursement DECIMAL(5,2),
   PRIMARY KEY(idAssurance)
);

CREATE TABLE Patient(
   idPatient INT NOT NULL,
   nom VARCHAR(50),
   prenom VARCHAR(50),
   dateNaissance DATE,
   numeroSecu VARCHAR(15),
   idAssurance INT,
   numeroContrat VARCHAR(30),
   PRIMARY KEY(idPatient),
   FOREIGN KEY(idAssurance) REFERENCES Assurance(idAssurance)
);

CREATE TABLE Medecin(
   idMedecin INT NOT NULL,
   nom VARCHAR(50),
   specialite VARCHAR(50),
   telephone VARCHAR(20),
   idService INT NOT NULL,
   idMedecin_superviser INT,
   PRIMARY KEY(idMedecin),
   FOREIGN KEY(idMedecin_superviser) REFERENCES Medecin(idMedecin)
);

CREATE TABLE Service(
   idService INT NOT NULL,
   libelle VARCHAR(50),
   etage INT,
   idMedecin INT NOT NULL,
   PRIMARY KEY(idService),
   FOREIGN KEY(idMedecin) REFERENCES Medecin(idMedecin)
);

CREATE TABLE Chambre(
   idChambre INT NOT NULL,
   numero VARCHAR(10),
   tarifJour DECIMAL(8,2),
   idService INT NOT NULL,
   PRIMARY KEY(idChambre),
   FOREIGN KEY(idService) REFERENCES Service(idService)
);

CREATE TABLE Lit(
   idLit INT NOT NULL,
   type VARCHAR(50),
   idChambre INT NOT NULL,
   PRIMARY KEY(idLit),
   FOREIGN KEY(idChambre) REFERENCES Chambre(idChambre)
);

CREATE TABLE Consultation(
   idConsultation INT NOT NULL,
   dateConsult DATE,
   motif TEXT,
   idPatient INT NOT NULL,
   idMedecin INT NOT NULL,
   PRIMARY KEY(idConsultation),
   FOREIGN KEY(idPatient) REFERENCES Patient(idPatient),
   FOREIGN KEY(idMedecin) REFERENCES Medecin(idMedecin)
);

CREATE TABLE Ordonnance(
   idOrdonnance INT NOT NULL,
   dateEmission DATE,
   idConsultation INT NOT NULL,
   PRIMARY KEY(idOrdonnance),
   FOREIGN KEY(idConsultation) REFERENCES Consultation(idConsultation)
);

CREATE TABLE Infirmier(
   idInfirmier INT NOT NULL,
   nom VARCHAR(50),
   grade VARCHAR(50),
   idService INT NOT NULL,
   PRIMARY KEY(idInfirmier),
   FOREIGN KEY(idService) REFERENCES Service(idService)
);

CREATE TABLE Examen(
   idExamen INT NOT NULL,
   typeExamen VARCHAR(50),
   resultat TEXT,
   idLabo INT NOT NULL,
   idConsultation INT NOT NULL,
   PRIMARY KEY(idExamen),
   FOREIGN KEY(idLabo) REFERENCES Laboratoire(idLabo),
   FOREIGN KEY(idConsultation) REFERENCES Consultation(idConsultation)
);

CREATE TABLE occuper(
   idPatient INT NOT NULL,
   idLit INT NOT NULL,
   dateEntree DATE,
   dateSortie DATE,
   PRIMARY KEY(idPatient, idLit),
   FOREIGN KEY(idPatient) REFERENCES Patient(idPatient),
   FOREIGN KEY(idLit) REFERENCES Lit(idLit)
);

CREATE TABLE comporter(
   idOrdonnance INT NOT NULL,
   idMedicament INT NOT NULL,
   posologie VARCHAR(255),
   dureeJours INT,
   PRIMARY KEY(idOrdonnance, idMedicament),
   FOREIGN KEY(idOrdonnance) REFERENCES Ordonnance(idOrdonnance),
   FOREIGN KEY(idMedicament) REFERENCES Medicament(idMedicament)
);

CREATE TABLE administrer(
   idInfirmier INT NOT NULL,
   idPatient INT NOT NULL,
   idMedicament INT NOT NULL,
   dateHeure DATETIME,
   dose VARCHAR(50),
   PRIMARY KEY(idInfirmier, idPatient, idMedicament),
   FOREIGN KEY(idInfirmier) REFERENCES Infirmier(idInfirmier),
   FOREIGN KEY(idPatient) REFERENCES Patient(idPatient),
   FOREIGN KEY(idMedicament) REFERENCES Medicament(idMedicament)
);

ALTER TABLE Medecin ADD FOREIGN KEY(idService) REFERENCES Service(idService);
