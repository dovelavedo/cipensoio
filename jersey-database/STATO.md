# Jersey Database - stato del progetto

Archivio storico delle maglie da calcio (nome provvisorio). Questo file va aggiornato a ogni sessione.

## Dove siamo (12 novembre 2026)
- Piano approvato dal proprietario.
- Fatto: programma di raccolta dati da Wikipedia in italiano e primo set di dati della Serie A 1997-98
  (`data/serie-a-1997-1998.json`) con elenco di mancanti e incerti (`data/DA-VERIFICARE-1997-1998.md`).
- NON ancora fatto: sito, database, login, voti, area admin.
- Bloccato in attesa del proprietario: repository GitHub dedicato, account Supabase e Vercel.

## Sistemazione provvisoria
Questa cartella sta sul ramo `ccr-d9a1959c-rnurpe` del repository `cipensoio` (un altro progetto, i fotolibri)
solo per non perdere il lavoro. Va spostata nel repository dedicato `jersey-database` appena esiste.
Il ramo non va unito a `main` di cipensoio.

## Decisioni prese
- Repository dedicato, nome `jersey-database`. Nome del sito provvisorio: Jersey Database.
- Tecnologie: Next.js (sito), Supabase (database, login, foto), Vercel (pubblicazione).
- Costi: si parte sui piani gratuiti. Si paga solo se e quando servirà (traffico, uso commerciale con i link ai negozi).
- Login utenti: link via email senza password + accesso con Google.
- Fase 1: solo Serie A (la Serie B verrà dopo; il database prevede già più competizioni).
- Ordine: prima la sola stagione 1997-98 completa, prova del proprietario, poi estensione 1990-91 -> 2026-27.
- Voto "top 3 giocatori": votabile tutta la rosa della squadra-stagione, anche chi ha zero presenze.
- Classifiche dai voti: 3 punti al primo, 2 al secondo, 1 al terzo.
- Foto: nessuna raccolta automatica. Campo immagine con fonte, credito, licenza e segnaposto neutro.
  Questione marchi (stemmi, sponsor) ancora aperta: da decidere con il proprietario prima di pubblicare foto.
- Numeri di maglia mostrati solo dal 1995-96; prima la rosa è senza numeri.
- Niente maglie dei portieri.
- Interfaccia in italiano, testi separati dal codice per aggiungere l'inglese.

## Regole sui dati
- La maglia è il record principale: una maglia usata più stagioni è un solo record con stagione di inizio e fine.
- Campionato, piazzamento e rosa appartengono alla coppia squadra-stagione.
- Fonti ammesse: Wikipedia IT/EN e Wikidata. Mai siti concorrenti o negozi.
- Ogni dato ha fonte e stato "da verificare / verificato". Ciò che manca si elenca, non si inventa.

## Struttura del database (da costruire)
nazioni, competizioni, stagioni, squadre, squadra_stagione (campionato + piazzamento), maglie (tipo, stagione
inizio/fine, sponsor tecnico, main sponsor), sponsor, maglia_sponsor_secondari, immagini (file, fonte, credito,
licenza), giocatori, rosa (squadra_stagione, giocatore, numero, ruolo, presenze, gol), utenti, voti (3 categorie,
posizioni 1-3). Predisposte ma non costruite: negozi, offerte, storico_prezzi, avvisi_prezzo.

## Raccolta dati
`python3 scripts/raccolta_wikipedia.py 1997-1998` (richiede accesso di rete a it.wikipedia.org).
Wikipedia limita le richieste: lo script aspetta e riprova da solo, e tiene una copia locale delle pagine.

Esito 1997-98: 18 squadre e piazzamenti completi; rose complete; sponsor per 14 squadre su 18; maglie per 14
su 18; presenze e gol per 15 su 18. Mancano del tutto su Wikipedia: maglie di Atalanta, Bari, Brescia, Udinese;
sponsor di Atalanta, Bari, Sampdoria, Udinese; presenze di Bari, Sampdoria, Udinese.

## Prossimi passi
1. Proprietario: creare il repository `jersey-database` e gli account Supabase e Vercel.
2. Spostare questa cartella nel nuovo repository.
3. Creare progetto Next.js e tabelle; caricare i dati 1997-98.
4. Pagine: ricerca, squadra-stagione, squadra, stagione, scheda maglia, rosa.
5. Login, voti e classifiche. 6. Area admin. 7. Link di prova al proprietario.
