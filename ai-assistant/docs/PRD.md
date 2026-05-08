# PRD: ADHD-optimoitu puhe- ja kirjoitusohjattu AI-assistentti (Kaisa)

## Problem Statement

ADHD-arjessa suurimmat haasteet ovat aloittamisen vaikeus ja ajanhallinta. Asiat unohtuvat, tehtävät kasaantuvat, ja aika "katoaa" ilman ulkoista rakennetta. Olemassa olevat kalenteriohjelmat ja muistiinpanosovellukset vaativat liikaa kognitiivista työtä: niitä pitää erikseen avata, navigoida ja täyttää. Puheella toimiva assistentti poistaa tämän esteen — ajatus voidaan sanoa ääneen heti kun se tulee mieleen, ilman siirtymävaihetta.

## Solution

Kaisa on Windows-pöytäkoneella toimiva henkilökohtainen AI-assistentti joka yhdistää puheohjauksen, kalenterin, tehtävälistat, muistutukset, uutistenluennan ja tiedonhaun yhteen järjestelmään. Käyttäjä voi puhua tai kirjoittaa vapaasti — Kaisa tunnistaa intention ja ohjaa pyynnön oikealle moduulille. Moduulit voidaan ottaa käyttöön tai poistaa käytöstä sekä asetustiedostosta että puhekomennolla. Kaikki henkilökohtainen data säilyy paikallisesti, vain kalenteri synkronoituu Google Calendariin.

## User Stories

1. Käyttäjänä haluan sanoa "hei Kaisa, muistuta minua huomenna kello 10 lääkäristä", jotta muistutus tallentuu ilman että minun täytyy avata mitään sovellusta.
2. Käyttäjänä haluan kuulla aamuyhteenvedon herättyäni, jotta tiedän mitä päivä tuo tullessaan ilman että minun täytyy itse etsiä tietoja.
3. Käyttäjänä haluan että Kaisa lukee minulle tärkeimmät uutiset aamulla, jotta pysyn ajan tasalla ilman uutissivustojen selailua.
4. Käyttäjänä haluan lisätä tehtävän puhumalla, jotta se ei unohdu ennen kuin ehdin kirjata sen ylös.
5. Käyttäjänä haluan merkitä tehtävän tehdyksi sanomalla "hei Kaisa, merkitse lääkäriaika tehdyksi", jotta tehtävälistani pysyy ajan tasalla vaivattomasti.
6. Käyttäjänä haluan asettaa tehtävälle prioriteetin (tärkeä/normaali/ei kiireinen), jotta tiedän mistä aloittaa.
7. Käyttäjänä haluan asettaa tehtävälle deadlinen, joka synkronoituu Google Calendariin, jotta en unohda määräaikoja.
8. Käyttäjänä haluan saada muistutuksen sekä puheena, Windows-ilmoituksena että äänimerkkinä, jotta se varmasti tavoittaa minut vaikka olisin syväkeskittyneenä.
9. Käyttäjänä haluan kysyä Kaisalta "mitä minulla on tänään" ja saada vastauksen kalenteritapahtumista ja tehtävistä, jotta saan nopean tilannehaun.
10. Käyttäjänä haluan hakea tietoa sanomalla "hei Kaisa, hae tietoa...", jotta saan vastauksen ilman selaimen avaamista.
11. Käyttäjänä haluan että Kaisa etsii tietoa sekä webistä, Wikipediasta että omista tiedostoistani, jotta saan kattavan vastauksen.
12. Käyttäjänä haluan määritellä asetuksissa mitkä uutislähteet Kaisa lukee, jotta saan juuri minulle relevantit uutiset.
13. Käyttäjänä haluan vaihtaa Kaisan persoonallisuusprofiilia (kannustava / neutraali / sarkastinen) asetuksista, jotta voin valita mielialani mukaan sopivan tyylin.
14. Käyttäjänä haluan sanoa "hei Kaisa, sammuta uutismoduuli", jotta voin tilapäisesti poistaa käytöstä toimintoja joita en tarvitse.
15. Käyttäjänä haluan että Kaisa kysyy mikä estää aloittamisen kun tehtävä on jäänyt roikkumaan, jotta saan apua jumiin jäämiseen.
16. Käyttäjänä haluan että Kaisa ehdottaa yhtä konkreettista pientä askelta aloittamisen helpottamiseksi, jotta kynnys madaltuu.
17. Käyttäjänä haluan keskustella Kaisan kanssa vapaasti päivän asioista, jotta voin purkaa ajatuksiani ja saada näkökulmia.
18. Käyttäjänä haluan että Kaisa muistaa aiemmat keskustelut istuntojen välillä, jotta minun ei tarvitse toistaa kontekstia joka kerta.
19. Käyttäjänä haluan käyttää Kaisaa sekä puheella että kirjoittamalla tilanteen mukaan, jotta voin valita sopivamman tavan.
20. Käyttäjänä haluan illan purku -toiminnon joka kokoaa mitä tein ja mitä jäi tekemättä, jotta voin sulkea päivän selkeästi.

## Implementation Decisions

### Moduulirakenne

Järjestelmä rakentuu nykyisen plugin-arkkitehtuurin päälle. Jokainen moduuli rekisteröi itsensä Routerille käynnistyksessä. Uuden moduulin lisääminen ei vaadi muutoksia olemassa olevaan koodiin.

**Uudet moduulit:**

- `modules/calendar` — Google Calendar API -integraatio. Lukee ja kirjoittaa tapahtumia. Tarjoaa "mitä tänään on" -kyselyn. Käyttää OAuth2-autentikointia.
- `modules/tasks` — Tehtävälistojen hallinta. SQLite-pohjainen tallennus. Tukee prioriteetteja (korkea/normaali/matala) ja deadlineja. Synkronoi deadlinet Google Calendariin.
- `modules/reminders` — Ajastetut muistutukset. Laukaisee Windows-ilmoituksen (plyer-kirjasto), TTS-puheen ja äänisignaalin samanaikaisesti. Pyörii taustasäikeessä.
- `modules/news` — RSS-lukija. Hakee ja tiivistää uutiset asetuksissa määritellyistä lähteistä (oletus: Yle, HS). Käyttää LLM:ää tiivistämiseen.
- `modules/search` — Tiedonhaku. Yhdistää web-haun (DuckDuckGo API), Wikipedian ja käyttäjän omien tiedostojen hakemiston. Palauttaa tiivistetyn vastauksen.
- `modules/morning_routine` — Aamuyhteenveto. Aggregoi tiedot kalenterista, tehtävälistasta, säästä (Open-Meteo API, ilmainen) ja uutisista. Käynnistyy automaattisesti tai käskystä.
- `modules/module_manager` — Moduulien hallinta. Lukee ja kirjoittaa settings.yaml-tiedostoa. Reagoi puhe/teksti-komentoihin "sammuta X" / "käynnistä X".

**Laajennettavat osat:**

- `core/memory/persistent` — SQLite-pohjainen pitkäaikainen muisti. Tallentaa keskusteluhistorian, käyttäjäpreferenssit ja tehtävät. Nykyinen istuntomuisti säilyy lyhytaikaisena välimuistina.
- `core/personality/profiles` — Useampi persoonallisuusprofiili YAML-tiedostoina. Profiilit: `kannustava`, `neutraali`, `sarkastinen`. Vaihto asetuksista tai puhekomennolla.
- `core/router` — LLM-pohjainen intent-tunnistus avainsanapohjaisen rinnalle. Käytetään kun avainsanapohjainen tunnistus ei löydä osumaa.

### Teknologiavalinnat

- **Google Calendar:** `google-api-python-client` + OAuth2, tokeni tallennetaan paikallisesti
- **Windows-ilmoitukset:** `plyer` (cross-platform, toimii Windows 10/11)
- **RSS:** `feedparser`-kirjasto
- **Web-haku:** DuckDuckGo Instant Answer API (ei API-avainta tarvita)
- **Sää:** Open-Meteo API (ilmainen, ei API-avainta)
- **SQLite:** `sqlalchemy` (jo requirements.txt:ssä)
- **LLM-backend:** Google Gemini (gemini-2.0-flash), ilmainen tier

### Data-arkkitehtuuri

- Kaikki henkilökohtainen data (tehtävät, muistutukset, keskusteluhistoria) SQLite-tietokannassa paikallisesti
- Google Calendar synkronointi vain kalenteritapahtumille ja tehtävien deadlineille
- Asetukset `config/settings.yaml`:ssa, salaisuudet `.env`:ssä

### Moduulien käynnistys/sammutus

- `settings.yaml`:ssa jokaisella moduulilla `enabled: true/false`
- Puhekomento muuttaa asetuksen tilapäisesti muistissa (ei kirjoita levylle)
- Pysyvä muutos: "hei Kaisa, poista uutiset käytöstä pysyvästi" → kirjoittaa settings.yaml

## Testing Decisions

Hyvä testi testaa ulkoista käyttäytymistä, ei toteutuksen yksityiskohtia. Testeissä mockataan kaikki ulkoiset riippuvuudet (Google API, verkko, tietokanta).

**Testattavat moduulit:**

- `modules/tasks` — yksikkötestit: lisäys, poisto, prioriteetti, deadline, listaus. Käytetään in-memory SQLiteä.
- `modules/reminders` — yksikkötestit: ajastuksen logiikka, laukaisu oikeaan aikaan. Mockataan `plyer` ja TTS.
- `modules/calendar` — yksikkötestit: tapahtumien haku ja kirjoitus. Mockataan Google Calendar API.
- `modules/morning_routine` — integraatiotesti: varmistaa että aamuyhteenveto sisältää kaikki odotetut osat. Mockataan ulkoiset API:t.
- `modules/module_manager` — yksikkötestit: moduulin sammutus/käynnistys päivittää tilan oikein.
- `core/memory/persistent` — yksikkötestit: tallennus ja haku toimivat, FIFO-rajoitus toimii.

Esimerkkinä olemassa olevat testit: `tests/unit/test_memory.py`, `tests/unit/test_router.py`.

## Out of Scope

- Puhelintuki / mobiilisovellus (lisätään myöhemmin erillisenä moduulina)
- Sähköpostin hallinta
- Kotiautomaatio (valot, lämpötila jne.)
- Windows-sovellusten ohjaus (avaa/sulje ohjelmat)
- Pilvipalvelinratkaisu tai etäkäyttö
- Monikäyttäjätuki
- Reaaliaikainen kalenterin synkronointi (pollaus riittää MVP:ssä)

## Further Notes

- MVP-järjestys: 1) nopea muistutuksen lisäys, 2) tehtävälistat, 3) Google Calendar, 4) aamurutiini, 5) uutiset, 6) tiedonhaku
- Gemini-backend on jo toteutettu — LLM-integraatio on valmis uusille moduuleille
- Piper TTS (offline) on tavoite äänimoduulille, ElevenLabs varavalintana
- Focusrite Scarlett Solo -äänikortin device ID konfiguroidaan settings.yaml:ssa
- ADHD-huomio: moduulien käyttöliittymä pidetään minimalistisena — ei liikaa vaihtoehtoja kerralla
