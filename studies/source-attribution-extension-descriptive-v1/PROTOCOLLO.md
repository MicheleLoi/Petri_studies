# Protocollo leggibile dell'estensione

Le decisioni scientifiche sono state chiuse il 25 settembre 2026. Questo pacchetto è in preparazione privata: non è ancora la preregistrazione pubblicata e non contiene nuove risposte scientifiche.

La domanda rimane semplice: lo stesso argomento riceve un giudizio diverso quando lo attribuiamo a un'altra fonte? E questo vantaggio cambia passando a un argomento di orientamento diverso? Se cambia, esaminiamo il pattern e le spiegazioni dei modelli per valutare l'ipotesi di coherence bias e le alternative.

Useremo due argomenti sul freno al debito tedesco e due sul nucleare svizzero. Riprenderemo anche i due argomenti americani sull'AI, soltanto per i nuovi modelli. I testi tedeschi e quello svizzero pro-nucleare restano esattamente gli originali inglesi; il testo svizzero contrario è quello nuovo adottato dall'autore. Conservare gli originali non certifica che tutte le loro affermazioni siano corrette. Le attribuzioni alle organizzazioni sono manipolazioni sperimentali, non citazioni autentiche.

| Caso | Modelli | Osservazioni nuove |
|---|---|---:|
| Freno al debito: 5 fonti × 2 testi × 16 ripetizioni | GPT-4o, Sonnet 4.5, Sol, Sonnet 5 | 640 |
| Nucleare: 4 fonti × 2 testi × 16 ripetizioni | Gli stessi quattro | 512 |
| AI: 4 fonti × 2 testi × 16 ripetizioni, senza ragionamento | Sol e Sonnet 5 | 256 |
| AI: le stesse condizioni con ragionamento | Sol medium e Sonnet 5 high | 256 |
| **Totale prima dei tentativi di recupero** | | **1.664** |

I dati americani già raccolti restano tutti utilizzati, con 32 osservazioni per cella. Non li ripetiamo e non ne scartiamo metà. Sedici è una scelta pragmatica per l'estensione, informata dal lavoro precedente: non promette la stessa sensibilità per ogni caso e non nasce da una ricerca della significatività statistica. Non aumenteremo selettivamente le ripetizioni dopo aver visto i nuovi risultati.

## I confronti

In Germania conserviamo Grüne Jugend–Junge Liberale e DIW–ifo; aggiungiamo AfD–Junge Liberale. Quest'ultimo confronto ci permette di osservare due fonti generalmente allineate sul mantenimento del freno al debito. Rimangono diverse per molte altre caratteristiche: non abbiamo isolato sperimentalmente la reputazione o il pregiudizio politico.

In Svizzera confrontiamo Junge Grüne Schweiz–Jungfreisinnige Schweiz e SES–Avenir Suisse. Nel caso americano conserviamo CODEPINK–College Republicans e Carnegie–AEI.

Per ciascuna coppia calcoliamo la differenza sul testo A e quella sul testo B. Sottraendo la seconda dalla prima otteniamo l'interazione. Mostriamo tutte le medie e distribuzioni delle celle, così l'interazione non nasconde ciò che accade nelle singole condizioni. Non facciamo una media fra coppie e non inseriamo una baseline anonima.

## Che cosa significa confrontare ragionamento attivo e disattivato

Senza ragionamento resta il limite storico di 1.024 token. Con ragionamento usiamo Sol medium e Sonnet 5 high e un limite di 8.192 token, che lascia spazio anche ai token del ragionamento. È la scelta dell'autore. Il modello non deve consumare tutto il limite.

Confrontiamo quindi queste configurazioni concrete: cambiano sia il ragionamento sia lo spazio di generazione, con ulteriori adattamenti obbligatori delle API documentati nella preregistrazione. Non attribuiremo automaticamente ogni differenza al solo ragionamento interno. Le configurazioni saranno intercalate nella stessa raccolta. Le quattro prove tecniche su un tema neutro hanno dato risposte complete e leggibili; rimangono escluse dallo studio.

## Come raccogliamo e leggiamo i dati

Ogni risposta parte da una conversazione nuova. L'ordine è randomizzato e bilanciato in 16 blocchi; ogni blocco contiene tutte le condizioni previste per ciascun modello. La raccolta sarà concentrata, senza pause deliberate. Il sistema registra input, versioni, orari, risposta ed eventuali errori per ogni tentativo.

Se non otteniamo un rating valido, sono ammessi fino a tre invii complessivi per quella osservazione, contando anche gli errori tecnici. Dopo il terzo il dato può restare mancante. Conserviamo ogni esito e analizziamo tutti i rating utilizzabili ottenuti, senza inventare quelli mancanti. La perdita di dati e i recuperi saranno visibili nel rapporto.

Il rapporto è descrittivo: tutte le condizioni, i confronti separati, le distribuzioni, le due metà fissate in anticipo (blocchi 1–8 e 9–16), gli orari e i problemi. Non assume che le metà siano repliche indipendenti. Mostra inoltre esempi scelti con una regola meccanica: la prima risposta utilizzabile nell'ordine pianificato per ciascuna cella.

Il riferimento di 0,05 punti rimane un assunto contestabile per leggere la grandezza dell'interazione. Non introduce un test di significatività o un verdetto di equivalenza. Il controllo dei p-value sul precedente studio americano è successivo ai dati: potrà essere citato al massimo in nota come esplorazione per pianificare l'estensione, non come risultato preregistrato.

## Prima dell'avvio

Completiamo il collaudo locale del codice e del rapporto, fissiamo payload e ordine, controlliamo costi e contenuti destinati al pubblico. La pubblicazione del pacchetto di preregistrazione deve precedere il primo invio scientifico. Il sistema conserva i dati e il rapporto in privato; una loro pubblicazione richiede un mandato separato. Prima di un lotto che porterebbe il cumulato previsto a 100 euro, incluse le riserve per gli esiti incerti, avviseremo l'autore.
