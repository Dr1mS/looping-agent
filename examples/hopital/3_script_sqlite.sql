CREATE TABLE Medicament(
   idMedicament INTEGER NOT NULL,
   nomCommercial VARCHAR(50),
   prix DECIMAL(10,2),
   PRIMARY KEY(idMedicament)
);

CREATE TABLE Laboratoire(
   idLabo INTEGER NOT NULL,
   raisonSociale VARCHAR(50),
   ville VARCHAR(50),
   PRIMARY KEY(idLabo)
);

CREATE TABLE Assurance(
   idAssurance INTEGER NOT NULL,
   nom VARCHAR(50),
   tauxRemboursement DECIMAL(5,2),
   PRIMARY KEY(idAssurance)
);

CREATE TABLE Patient(
   idPatient INTEGER NOT NULL,
   nom VARCHAR(50),
   prenom VARCHAR(50),
   dateNaissance DATE,
   numeroSecu VARCHAR(15),
   idAssurance INTEGER,
   numeroContrat VARCHAR(30),
   PRIMARY KEY(idPatient),
   FOREIGN KEY(idAssurance) REFERENCES Assurance(idAssurance)
);

CREATE TABLE Medecin(
   idMedecin INTEGER NOT NULL,
   nom VARCHAR(50),
   specialite VARCHAR(50),
   telephone VARCHAR(20),
   idService INTEGER NOT NULL,
   idMedecin_superviser INTEGER,
   PRIMARY KEY(idMedecin),
   FOREIGN KEY(idService) REFERENCES Service(idService),
   FOREIGN KEY(idMedecin_superviser) REFERENCES Medecin(idMedecin)
);

CREATE TABLE Service(
   idService INTEGER NOT NULL,
   libelle VARCHAR(50),
   etage INTEGER,
   idMedecin INTEGER NOT NULL,
   PRIMARY KEY(idService),
   FOREIGN KEY(idMedecin) REFERENCES Medecin(idMedecin)
);

CREATE TABLE Chambre(
   idChambre INTEGER NOT NULL,
   numero VARCHAR(10),
   tarifJour DECIMAL(8,2),
   idService INTEGER NOT NULL,
   PRIMARY KEY(idChambre),
   FOREIGN KEY(idService) REFERENCES Service(idService)
);

CREATE TABLE Lit(
   idLit INTEGER NOT NULL,
   type VARCHAR(50),
   idChambre INTEGER NOT NULL,
   PRIMARY KEY(idLit),
   FOREIGN KEY(idChambre) REFERENCES Chambre(idChambre)
);

CREATE TABLE Consultation(
   idConsultation INTEGER NOT NULL,
   dateConsult DATE,
   motif TEXT,
   idPatient INTEGER NOT NULL,
   idMedecin INTEGER NOT NULL,
   PRIMARY KEY(idConsultation),
   FOREIGN KEY(idPatient) REFERENCES Patient(idPatient),
   FOREIGN KEY(idMedecin) REFERENCES Medecin(idMedecin)
);

CREATE TABLE Ordonnance(
   idOrdonnance INTEGER NOT NULL,
   dateEmission DATE,
   idConsultation INTEGER NOT NULL,
   PRIMARY KEY(idOrdonnance),
   FOREIGN KEY(idConsultation) REFERENCES Consultation(idConsultation)
);

CREATE TABLE Infirmier(
   idInfirmier INTEGER NOT NULL,
   nom VARCHAR(50),
   grade VARCHAR(50),
   idService INTEGER NOT NULL,
   PRIMARY KEY(idInfirmier),
   FOREIGN KEY(idService) REFERENCES Service(idService)
);

CREATE TABLE Examen(
   idExamen INTEGER NOT NULL,
   typeExamen VARCHAR(50),
   resultat TEXT,
   idLabo INTEGER NOT NULL,
   idConsultation INTEGER NOT NULL,
   PRIMARY KEY(idExamen),
   FOREIGN KEY(idLabo) REFERENCES Laboratoire(idLabo),
   FOREIGN KEY(idConsultation) REFERENCES Consultation(idConsultation)
);

CREATE TABLE occuper(
   idPatient INTEGER NOT NULL,
   idLit INTEGER NOT NULL,
   dateEntree DATE,
   dateSortie DATE,
   PRIMARY KEY(idPatient, idLit),
   FOREIGN KEY(idPatient) REFERENCES Patient(idPatient),
   FOREIGN KEY(idLit) REFERENCES Lit(idLit)
);

CREATE TABLE comporter(
   idOrdonnance INTEGER NOT NULL,
   idMedicament INTEGER NOT NULL,
   posologie VARCHAR(255),
   dureeJours INTEGER,
   PRIMARY KEY(idOrdonnance, idMedicament),
   FOREIGN KEY(idOrdonnance) REFERENCES Ordonnance(idOrdonnance),
   FOREIGN KEY(idMedicament) REFERENCES Medicament(idMedicament)
);

CREATE TABLE administrer(
   idInfirmier INTEGER NOT NULL,
   idPatient INTEGER NOT NULL,
   idMedicament INTEGER NOT NULL,
   dateHeure DATETIME,
   dose VARCHAR(50),
   PRIMARY KEY(idInfirmier, idPatient, idMedicament),
   FOREIGN KEY(idInfirmier) REFERENCES Infirmier(idInfirmier),
   FOREIGN KEY(idPatient) REFERENCES Patient(idPatient),
   FOREIGN KEY(idMedicament) REFERENCES Medicament(idMedicament)
);
