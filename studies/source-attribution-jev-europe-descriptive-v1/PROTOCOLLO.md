# Jev nei due casi europei: supplemento prospettico

Questo supplemento completa lo studio descrittivo aggiungendo Jev al freno al debito tedesco e al nucleare svizzero. L'autore ha chiarito che intendeva includerlo in tutti i casi. Il piano viene congelato e pubblicato prima di queste nuove osservazioni. Al momento della progettazione sono già noti i dati USA di Jev e quelli europei dei quattro modelli generativi: la scelta del supplemento non è indipendente da quella storia. I depositi precedenti rimangono immutati.

## Domanda e osservazioni

La domanda è se lo stesso argomento riceva uno score diverso cambiando solo la fonte attribuita, e se quel divario cambi fra i due argomenti. Le attribuzioni sono manipolazioni sperimentali, non citazioni autentiche. Non introduciamo una fonte anonima né misuriamo il prestigio delle organizzazioni.

| Caso | Fonti | Testi | Ripetizioni per cella | Nuovi slot |
|---|---:|---:|---:|---:|
| Freno al debito tedesco | 5 | 2 | 16 | 160 |
| Nucleare svizzero | 4 | 2 | 16 | 128 |
| Totale | | | | **288** |

Germania: Grüne Jugend–Junge Liberale; DIW Berlin–ifo Institut; AfD–Junge Liberale. AfD indica il partito stesso. I due confronti che includono Junge Liberale riusano le stesse osservazioni. Svizzera: Junge Grüne Schweiz–Jungfreisinnige Schweiz; SES–Avenir Suisse. Le coppie restano separate.

I testi inglesi e i nomi sono quelli esatti del deposito europeo precedente, inclusi i limiti delle loro affermazioni storiche. Per Jev conserviamo esattamente il testo introduttivo, attribuzione e argomento della richiesta generativa, prima delle istruzioni specifiche per la risposta. La domanda Jev cambia soltanto il tema: `German fiscal policy` o `energy policy`.

## Misura e limiti

Manteniamo la rubrica USA Jev: cinque descrizioni di livello, score nativo fra 0 e 4 e conversione score/4. Il campo confidence non è il rating e non decide l'inclusione. Conserviamo score, probabilità, legenda e metadati; nessuna spiegazione discorsiva viene richiesta o inferita.

La rubrica è una definizione operativa non validata, formulata dall'assistente sotto mandato. Uniformare l'intervallo numerico non calibra questa misura con quella dei modelli generativi. Non useremo l'ampiezza minore delle differenze per proclamare Jev più imparziale. Neppure i confronti fra temi isolano il tema: le raccolte avvengono in date diverse e il gateway non certifica una versione immutabile. Usiamo l'alias storico e documentiamo Jev 1.13.0 come versione presunta; un'identità o provider inatteso sospende l'esecuzione.

## Raccolta

Sedici blocchi consecutivi, ciascuno con tutte le diciotto celle in ordine casuale fissato dal piano. Un solo invio attivo alla volta, stato nuovo, nessuna pausa deliberata fra blocchi. Sedici ripetizioni riprendono la numerosità europea adottata: non sono una garanzia di potenza o indipendenza. Non si amplia il campione in funzione dei risultati.

Primo score utilizzabile per slot; al massimo tre invii totali, includendo errori tecnici e timeout. Ogni tentativo è salvato prima dell'invio e resta nella storia. Nessun reinvio di uno slot già utilizzabile. Esiti incerti consumano il budget dei tentativi e mantengono la riserva economica. I mancanti dopo tre invii restano mancanti. SDK retry e redirect automatici sono disabilitati; attendiamo i ritardi previsti o il maggiore Retry-After. Non sostituiamo modello, provider o scala automaticamente.

Score non numerico/non finito/fuori intervallo è inutilizzabile; legenda o identità incompatibili sospendono. Distribuzioni ausiliarie mancanti o non valide sono segnalate senza scartare uno score utilizzabile, senza rinormalizzare. Una distribuzione valida ma incoerente con lo score richiede controllo. Tolleranze e dettagli sono fissati nel piano e nel codice pubblico.

## Rapporto fissato prima dei dati

Mostriamo tutte le diciotto medie e distribuzioni, cinque coppie, i due divari per coppia e la loro differenza: I = (fonte 1 − fonte 2) sul testo A meno lo stesso divario sul testo B. Riportiamo anche le metà 1–8 e 9–16, senza considerarle repliche indipendenti. Diagnostica della scala nativa, distribuzioni, range, errori, recuperi, mancanti, orari e modello restituito accompagna gli effetti. Gli esempi strutturati seguono la prima risposta utilizzabile nell'ordine pianificato di ogni cella.

Il rapporto è descrittivo, senza p-value, intervalli di confidenza o verdetti di equivalenza. Il riferimento 0,05 è un assunto di lettura della scala convertita, non una soglia di verità o una calibrazione fra sistemi. Pubblichiamo il piano prima della raccolta; dati e rapporto restano privati finché l'autore non autorizzi la pubblicazione. Il paper distinguerà questo supplemento dai due studi precedenti e riferirà anche risultati piccoli, contrari o mancanti.

## Verifiche e spesa

Prima della raccolta: prove offline su identità dei materiali, parsing, recuperi, blocchi, hash e rapporto; controllo documentale datato di modello e prezzi; deposito pubblico verificato. Le eventuali prove tecniche neutre sono escluse dai dati. Il budget conserva il cumulato precedente e gli esiti incerti, con riserva prudenziale di EUR 0,01 per invio Jev; un blocco con tutti i recuperi riserva EUR 0,54. Il controllo si ferma prima di un lotto che porterebbe il cumulato con riserva a EUR 100 e informa l'autore. Non si assume che la vecchia promozione gratuita sia ancora valida.
