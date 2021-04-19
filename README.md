# Serenissimo, domande frequenti

## Chi sei?

Sono [Alberto Granzotto](https:///www.granzotto.net/), libero professionista a Berlino. Mi occupo di servizi software, privacy, blockchain. La mia email è agranzot@mailbox.org.

## Cos'è Serenissimo?

Serenissimo è un bot (un assistente virtuale) che ti manda un messaggio sul telefono quando si liberano posti per il vaccino in Veneto. Puoi parlare con il bot tramite l'applicazione di messaggistica [Telegram](https://telegram.org/). Il bot ti chiede la ULSS di appartenenza e il tuo codice fiscale. Ottenuti i dati li memorizza e controlla periodicamente sul [sito ufficiale della Regione Veneto](vaccinicovid.regione.veneto.it/) i posti disponibili, se ce ne sono ti manda un messaggio.

## Perché hai fatto Serenissimo?

Il bot nasce da un'esigenza personale. Mia madre deve prenotarsi per il vaccino anti-covid. Controlla spesso, delle volte ogni ora, il sito ufficiale della Regione Veneto. Come lei, altre persone che conosco controllano continuamente (spesso per i propri genitori anziani) il sito ufficiale dei vaccini, sperando di trovare un posto.
 
Mi sono chiesto: perché non invertire il paradigma? Perché non avvisare le persone quando si liberano posti per la vaccinazione, invece di fargli attivamente controllare la situazione? Questo vale soprattutto per le persone anziane, che spesso si affidano ai propri figli per usare questi sistemi.

## Così privilegi le persone che sanno usare la tecnologia.

No. Non ho costruito il bot per *saltare la fila*, fare i furbi o per privilegiare alcune categorie di persone piuttosto che altre. **Al contrario** il bot è pensato per rendere più accessibile il servizio di prenotazione, soprattutto per i meno esperti e per chi ha difficoltà a controllare ripetutamente lo stato delle prenotazioni.

## Il bot fa troppe richieste e rischia di rendere la piattaforma di vaccinazione inaccessibile!

No. **Il bot fa richieste sequenziali, non in parallelo.** Cosa significa? Immagina di essere all'ufficio delle poste, davanti a te ci sono 10 sportelli liberi. Preferisci avere davanti a te una persona con 100 lettere, o 100 persone con una lettera? Meglio una persona con 100 lettere, visto che terrà occupato solo uno degli sportelli disponibili. Il bot ha tante lettere in mano ma occupa solo uno degli sportelli, e per molto poco tempo!

Entro volentieri nei dettagli tecnici. Tutto quello che dico è verificabile dal [codice sorgente](https://github.com/vrde/serenissimo):

- Per gli utenti che rientrano nelle categorie da vaccinare, il bot controlla ogni 30 minuti se ci sono dei posti liberi.
- Per gli utenti che non rientrano ancora nelle categorie da vaccinare, il bot controlla ogni 4 ore la situazione.

Il bot **non crea un carico maggiore ai server** perché le richieste che fa sono a nome di altri utenti. Inoltre il bot ottimizza le richieste, non carica file statici come immagini, JavaScript o fogli di stile, alleggerendo il traffico.

## Perché devo inserire la ULSS quando hai già il mio codice fiscale?

Il portale della Regione Veneto funziona così. Avevo pensato di chiedere solo il codice fiscale e "cercare" in tutte le 9 ULSS, ma questo avrebbe aumentato il numero di richieste del bot.

## Serenissimo funziona?

Sì. Ad oggi 19 aprile 2021, ore 14:00:

- 1429 persone hanno inserito il proprio codice fiscale e ULSS di appartenenza.
- Circa 100 rientrano nelle categorie che si possono vaccinare (il numero varia continuamente perché le categorie che hanno diritto al vaccino cambiano nel tempo). 
- 26 hanno trovato posto e si sono vaccinate.

## Serenissimo può inviare SMS?

Al momento no, ma valuterò se implementare questa funzione in futuro.

## I miei dati sono al sicuro?

Sì. Informativa sulla privacy:

- I tuoi dati vengono usati esclusivamente per controllare la disponibilità di un appuntamento per la vaccinazione usando il sito https://vaccinicovid.regione.veneto.it/
- Nel database i dati memorizzati sono:
    - Il tuo identificativo di Telegram (NON il numero di telefono).
    - Il tuo codice fiscale.
    - La ULSS di riferimento.
- I tuoi dati sono memorizzati in un server in Germania.
- Se digiti "cancella", i tuoi dati vengono eliminati completamente.
- Il codice del bot è pubblicato su https://github.com/vrde/serenissimo e chiunque può verificarne il funzionamento.