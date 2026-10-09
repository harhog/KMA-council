# KMA Council — Arkitektur (KMA-001)

**Task:** KMA-001 · **Fas:** PHASE_0_RECON (reconnaissance + planering, ingen implementation).
**Källa:** Notion-sidorna 00–11 (sida 07 = arbetsordern för denna task).
**Referenser:** lokala repon `idea-council`, `idea-developer-council` (mönster, ej blind kopiering).
**Regel för denna task:** endast detta dokument skapas/ändras. Ingen kod, config eller andra filer.

## 1. Filer lästa (arbetsorder punkt 1)

**KMA-council (eget repo):** tomt greenfield-repo, `git init` på `main`, inga commits.
`docs/` tom. Inget att refaktorera; denna task designar målarkitekturen.

**Notion (alla 12 sidor, lästa via notion-client i publikt läge):**
00 produktbeskrivning; 01 agentarkitektur; 02 källor/evidens; 03 arbetsflöden A–G;
04 tasks 001–005; 05 tasks 006–010; 06 MVP-gate/QA; 07 denna arbetsorder;
08 roadmap faser 0–8; 09 veckovis källsynkning; 10 tasks 011–015; 11 STATUS-modell.

**idea-developer-council (läst):** README, requirements, app/council.py, app/roles.py,
app/main.py, app/llm.py, app/memory.py, agents/CHAIR.md, TECH.md, LEGAL.md,
protocols/ROADMAP_PROTOCOL.md, protocols/MEMORY_PROTOCOL.md,
knowledge/SOURCE_CATALOG.json, tests/test_council.py.

**idea-council (läst):** README, requirements, app/council.py, app/roles.py,
protocols/COUNCIL_PROTOCOL.md, protocols/RESEARCH_AND_EXPERT_KNOWLEDGE.md,
agents/SAMAN_CHAIRMAN.md, SINA_RESEARCH.md, NIKA_LEGAL.md,
KAVEH_RED_TEAM.md, ADIL_JUDGE.md.

## 2. Reconnaissance — vad som finns, återanvänds, ersätts (arbetsorder punkt 2)

### 2.1 Mönster som återanvänds (förstådda, ej kopierade)

1. Fasta agentkontrakt i Markdown (roll, indata, obligatoriskt utdataformat).
   Källa: IDC agents/*.md. KMA-anpassning: 10 KMA-kontrakt där AFS aldrig
   gissar paragraf och RESEARCH äger primärkälla.
2. CHAIR-orkestrering: klassificera → minneskontext → parallella bidrag →
   konfliktregler → deterministisk gate. Källa: IDC app/council.py + CHAIR.md.
   KMA-anpassning: 11-stegs pipeline med evidence validation som egen etapp
   före slutoutput.
3. Intake-gate: INSUFFICIENT_EVIDENCE + saknas-lista i stället för gissningar.
   Källa: IDC check_intake. KMA-anpassning: required-intake per workflow (A–G);
   saknad kritisk info stoppar före analys.
4. Deterministisk beslutsgate. Källa: IDC FEASIBLE/PILOT/HOLD/NO-GO.
   KMA-anpassning: VERIFIED/PARTIALLY_VERIFIED/UNVERIFIED/HISTORICAL/
   CONFLICTING + INSUFFICIENT_EVIDENCE/CONFLICTING_EVIDENCE.
   Evidensen äger gaten, ej ordföranden.
5. Minne som audit trail: atomiska skrivningar, explicit validering, reflektion
   per aktiv medlem, bevarad dissent. Källa: IDC scripts/council_memory.py.
   KMA-anpassning: samma garantier + AuditEvent-ström (fråga, routing, bidrag,
   evidence refs, konflikter, red-team, beslut, timestamp, modell, källversioner).
6. Red-team + oberoende granskning före slutoutput. Källa: IC KAVEH + ADIL.
   KMA-anpassning: REDTEAM falsifierar; REVISION begär bevis ur
   inspektörsperspektiv; båda före CHAIR-syntes.
7. Källkatalog + kunskapskort med coverage-grader. Källa: IDC
   SOURCE_CATALOG.json, IC RESEARCH-protokoll. KMA-anpassning: 4-nivåers
   hierarki; nivå 4 får aldrig ensam bära regulatoriskt påstående.
8. Teststrategi per lager + regressionssvit, mockat nätverk. Källa: IDC tests/,
   IC-protokoll. KMA-anpassning: minst 1 positivt + 1 negativt test per
   workflow; 10 red-team-fall; synk-tester för alla failure modes.

### 2.2 Vad som ersätts / inte kopieras (kända svagheter i referenserna)

1. Deklarerad men ej ingestd expertkunskap → KMA bygger verklig synk-pipeline
   (KMA-011), normalizer (KMA-012) och lokalt index (KMA-013). Coverage-grader
   är ärliga tills ingestionen är verifierad.
2. Heuristisk offline-fallback som kan svara trots svag evidens → offline-läge
   i KMA får aldrig producera VERIFIED regulatoriska slutsatser; utan evidence
   blir svaret INSUFFICIENT_EVIDENCE.
3. Juridik som resultatsektion → i KMA är evidence en genomgående gate i varje
   pipeline-steg, inte en sektion i slutet. AFS-agenten äger regeltext;
   RESEARCH äger currentness; Evidence Engine äger verifiering.
4. Majoritetslogik mellan agenter → i KMA vinner ingen agent genom att vara
   expert. Vid konflikt kontrolleras primärkälla, aktuell version och exakt
   innebörd; därefter redovisas konflikten öppet (sida 01, konfliktregel).
5. RAG/vector-DB som default → KMA börjar deterministiskt (registry →
   evidence → index utan vektorer); vektorsök läggs till endast om pilotdata
   visar behov (KMA-013).
6. Dashboard-komplexitet före kärnflöde → KMA-010 bygger frågeflödet först;
   kedjan Påstående → Evidence → Källa → aktuell version ska vara lättare att
   kontrollera än AI-svaret.

### 2.3 Risker och beroenden

- Rättslägesrisk: AFS 2023:1–15 antar ny struktur; synken måste förstå
  konsoliderade versioner, författningshistorik och kommande ändringar
  (sida 09), annars blir "aktuell" fel.
- Upphovsrätt: lagtext är öppen, men allmänna råd/vägledningar och
  branschmaterial kräver licensprövning per källa; lagra endast metadata +
  korta citat med locator tills varje källas licens är klarlagd.
- LLM-hallucination av paragrafnummer är systemets farligaste felläge →
  Evidence Gate + REDTEAM-regression är MVP-kritiska, ej "senare kvalitet".
- Prompt injection från externa dokument/webbsidor (KMA-009): externt innehåll
  är nivå-4-data, aldrig instruktioner.
- Scope creep mot kvalitet/miljö/ISO före MVP-gates: arkitekturen är utbyggbar
  men piloten får inte vidgas utan pilotdata (sida 08, fas 7).
- Beroende: Python 3.13 lokalt verifierad; FastAPI/Uvicorn/Pydantic för
  API-lagret (samma som IDC); minne/kunskap stdlib-only.

### 2.4 Vad som byggs först (rekommendation)

KMA-002 (Source Registry) → KMA-003 (Evidence Engine) → KMA-008 (Research
Connector) = fas 1 "Regulatory data foundation". Först när en officiell källa
kan registreras, version/currentness avgöras och unsupported claims stoppas,
byggs rådets intelligens (KMA-004, KMA-005). Full sekvens i avsnitt 10.

## 3. Målarkitektur (översikt)

```
                    ┌──────────────┐
                    │    CHAIR     │  klassificering, routing, syntes
                    │  (orkestrer) │
                    └──────┬───────┘
                           │ 1. Intake-gate (per workflow A–G)
                           ▼
              ┌────────────────────────┐
              │  ROUTER (deterministisk)│  AFS-fråga / SAM / OSA /
              │  regler, ej LLM-tycke   │  BYGG / incident / full
              └──────┬─────────────────┘
                     │ 2-5. Parallella agentbidrag (fast kontrakt)
        ┌────────────┼────────────┬──────────────┐
        ▼            ▼            ▼              ▼
     ┌─────┐     ┌─────┐     ┌────────┐     ┌──────────┐
     │ AFS │     │ SAM │     │  OSA   │ ... │ RESEARCH │  + BYGG/RISK/
     │     │     │     │     │        │     │ primär-  │  PRAKTIK/REVISION/
     │     │     │     │     │        │     │ källa    │  REDTEAM
     └─────┘     └─────┘     └────────┘     └──────────┘
                     │ 6. RESEARCH verifierar currentness
                     ▼
              ┌────────────────┐
              │ CONFLICT DETECT│  primärkälla + version + innebörd
              └───────┬────────┘
                      │ 7-8. REDTEAM falsifierar, REVISION begär bevis
                      ▼
              ┌────────────────┐
              │ EVIDENCE ENGINE│  VERIFIED / PARTIALLY / UNVERIFIED /
              │  (gate, ej råd)│  HISTORICAL / CONFLICTING
              └───────┬────────┘
                      │ 9. CHAIR-syntes endast av det som passerat gaten
                      ▼
              ┌────────────────┐
              │  DECISION +    │  åtgärder, ansvar, dokumentation,
              │  AUDIT TRAIL   │  osäkerheter, källor, nästa steg
              └────────────────┘

Lager (modulärt, stdlib-first utom API):
agents/ · council/ · sources/ · evidence/ · research/ · memory/ · workflows/ · api/ui · tests/
```

Designprinciper: (a) evidensen äger sanningen, inte agenterna; (b) deterministiska
gates före LLM-syntes; (c) minsta tillräckliga råd per fråga; (d) allt regulatoriskt
spårbart till source snapshot + locator + modellversion; (e) osäkerhet är ett
förstklassigt output, inte en fotnot.

## 4. Domänmodell (arbetsorder punkt 3)

Alla modeller blir Pydantic v2 (samma som IDC) med strikt validering.
Regulatoriska claims länkar redan i datamodellen till evidence IDs —
ett Claim utan evidence_refs kan aldrig bli VERIFIED (typnivå-garanti).

- **Question:** id, text, workflow_hint (A–G), verksamhet, arbetsmoment,
  roller, geografi, jurisdiction (default SE), created_at. Äger intake-gaten.
- **Workflow:** id (A–G), required_intake[], optional_intake[], agent_route[],
  evidence_policy, output_schema, completion_criteria, escalation_criteria.
  Inga domänpåståenden i workflow-koden — de bor i source/evidence-lagret.
- **Agent:** key (CHAIR/AFS/SAM/OSA/BYGG/RISK/PRAKTIK/REVISION/REDTEAM/RESEARCH),
  contract_ref (agents/<KEY>.md), mission, scope, inputs, outputs.
  mission, scope, non_scope, inputs, outputs, evidence_requirements,
  confidence_rules, escalation, disagreement_rules. Kontraktet laddas från
  agents/*.md (samma mönster som IDC roles.py: REQUIRED_HEADINGS-validering).
- **Source:** source_id, publisher, title, source_type, canonical_url,
  effective_from/to, retrieved_at, version/status, jurisdiction, topics,
  authority_level (1–4), checksum/content_hash. Unik source_id; dubbletter avvisas.
- **SourceVersion:** source_id + version, effective_dates, amendment_history,
  consolidated_flag, supersedes/superseded_by, snapshot_ref. Förstår
  konsoliderade versioner och kommande ändringar (sida 09 golden rule).
- **Evidence:** evidence_id, source_id, locator (AFS+kapitel+paragraf+stycke),
  quote_or_excerpt, claim_supported, source_type, authority, effective_date,
  retrieved_at, confidence, limitations, status. Status sätts av Evidence Engine,
  aldrig av enskild agent.
- **Claim:** claim_id, text, claim_type (regulatory/practical/assumption),
  evidence_refs[], status (ärvd från svagaste evidensen). Regulatoriskt claim
  utan evidence_refs → valideringsfel, ej UNVERIFIED-svar.
- **Risk:** risk_id, hazard, exposed_group, likelihood, consequence,
  existing_controls, additional_measures[], residual_risk, owner, deadline.
  Åtgärdshierarki: eliminera → ersätt → teknik → organisation → personligt skydd.
- **Recommendation:** recommendation_id, text, addresses_risk[], evidence_refs[],
  responsible_role, deadline, verification_method. Varje åtgärd pekar på risk
  och bevis — aldrig fristående råd.
- **Conflict:** conflict_id, claim_ids[], agent_positions{}, source_check
  (primärkälla/version/nebörd), resolution (CONFLICTING_EVIDENCE eller löst
  mot primärkälla), dissent_preserved. Ingen majoritetsomröstning.
- **Decision:** decision_id, question_id, workflow_id, route, status
  (VERIFIED/PARTIALLY_VERIFIED/UNVERIFIED/HISTORICAL/CONFLICTING/
  INSUFFICIENT_EVIDENCE/CONFLICTING_EVIDENCE), contributions, evidence_pack,
  conflicts, redteam_findings, uncertainties, next_steps. Stängd decision kräver
  reflektion från varje aktiv agent (samma regel som IDC MEMORY_PROTOCOL).
- **AuditEvent:** event_id, decision_id, event_type (intake/routing/contribution/
  evidence_ref/conflict/redteam/decision), actor, timestamp, model_version,
  source_snapshot_ref, payload_hash. Append-only ström; svar återskapas mot
  snapshot + version + locator + modell (sida 09 reproducibility).

## 5. Agentrådet MVP (arbetsorder punkt 4)

Gemensamt kontrakt (sida 01): varje agent lämnar assessment,
applicable_requirements, evidence_refs, risks, missing_information,
recommendation, confidence, assumptions, dissent, reflection.
Alla regulatoriska påståenden spårbara till evidence_refs.
Konfliktregel: ingen agent vinner genom expertstatus — primärkälla +
aktuell version + exakt innebörd avgör, därefter redovisas konflikten öppet.

- **CHAIR:** klassificerar, routar, syntetiserar, stoppar överdrift.
  Gör ej egen sakbedömning; ändrar ej evidence-status.
  Output: Decision + audit trail. Stoppar vid INSUFFICIENT/CONFLICTING_EVIDENCE.
- **AFS:** tillämpliga AFS, kapitel/paragraf, föreskrift vs allmänt råd.
  Gissar ALDRIG paragraf; tolkar ej byggteknik.
  Varje paragrafclaim kräver evidence med exakt locator.
  Eskalerar till RESEARCH vid oklar currentness.
- **SAM:** SAM-cykeln (undersök, riskbedöm, åtgärda, handlingsplan, följ upp),
  policy, uppgiftsfördelning, medverkan. Ersätter ej AFS-regeltext.
  Kopplar varje SAM-krav till AFS-evidence.
- **OSA:** belastning, krav/resurser, arbetstid, kränkande särbehandling.
  Gör ej medicinsk bedömning eller individärenden.
  Evidence där regelstöd finns, annars explicit märkt praktikråd.
- **BYGG:** projektering, BAS-P/U, entreprenörskedja, produktionsrisk.
  Ersätter ej konstruktionsdimensionering. Bygg-AFS (2023:3 m.fl.) via evidence.
- **RISK:** faror → risk → åtgärdshierarki
  (eliminera, ersätt, teknik, organisation, personligt skydd) → kvarvarande risk.
  Accepterar ej risk åt användaren. Varje risk kräver farobeskrivning + åtgärd.
- **PRAKTIK:** regel till verkligt arbete; glapp dokument vs arbetsplats.
  Mildrar ej regelkrav. Praktikråd märks explicit som tolkning, ej regeltext.
- **REVISION:** inspektörsperspektiv — begär bevis, hittar luckor,
  prioriterar allvarlighet. Utfärdar ej föreläggande.
  Varje finding kräver referens till påstående utan bevis.
- **REDTEAM:** falsifierar slutsatsen, angriper antaganden, letar bortglömda
  regler/risker. Veto genom personlighet förbjudet; fabricerar ej risker.
  Kritik utan evidence märks som hypotes.
- **RESEARCH:** primärkällor, aktuell version, ändringshistorik, evidence-paket.
  Söker nivå 1–2; nivå 4 bär aldrig ensam ett regelclaim.
  Sökresultat blir ej juridisk sanning — passerar source validation.

Senare agenter (Kvalitet/ISO, Miljö, Kemi, Ergonomi, Utrustning, TA-plan,
Arbetsrätt, Entreprenadjuridik, Incidentutredning, Statistik) läggs till endast
när pilotdata visar gap (sida 08 fas 7): nytt kontrakt + routing-regel,
ingen arkitekturändring.

## 6. Evidence gate (arbetsorder punkt 5)

Ingen regulatorisk slutsats markeras VERIFIED utan verifierbar evidence.
Gaten är deterministisk kod i evidence/-lagret, ej LLM-omdöme:

- **VERIFIED:** claim stöds av evidence med nivå-1/2-källa, aktuell version
  (effective_date täcker frågedatum), exakt locator, hämtad mot current snapshot.
- **PARTIALLY_VERIFIED:** delar av claimet stöds; resten explicit markerat som
  antagande/praktikråd. Svagaste evidensen sätter claim-status.
- **UNVERIFIED:** claim utan evidence eller med endast nivå-4-stöd.
  Levereras med varning, aldrig som regel.
- **HISTORICAL:** evidence från superseded version — tillåtet som historik,
  aldrig som aktuell regel utan markering.
- **CONFLICTING:** källor motsäger varandra eller agenter oense efter
  source_check → CONFLICTING_EVIDENCE på Decision, båda sidor redovisas.

Currentness-gate per regulatoriskt svar (sida 02): jurisdiction, verksamhet,
fråga, relevanta regler, aktuell version, ändringshistorik,
föreskrift/allmänt råd/vägledning, exakt evidence.
Misslyckas något steg faller status till UNVERIFIED/INSUFFICIENT_EVIDENCE.

Förbjudet (sida 02): gissa paragrafnummer; använda gammal AFS utan historisk
markering; presentera sekundär källa som primär; påstå regelkrav utan evidence;
dölja osäkerhet.

## 7. Routing (arbetsorder punkt 6)

Deterministiska regler (kod, ej LLM-tycke), minsta tillräckliga råd:
AFS-fråga till AFS + RESEARCH; SAM till SAM + AFS + RESEARCH;
OSA till OSA + SAM + RESEARCH; bygg/anläggning till
BYGG + AFS + SAM + RISK + RESEARCH; incident till RISK + SAM + REVISION +
RESEARCH; inspektion/dokumentgranskning till REVISION + AFS + PRAKTIK +
RESEARCH; generell fråga till relevanta experter + source verification;
full review till hela rådet.

Pipeline, 11 steg (sida 04 KMA-005): 1 Intake, 2 Classification,
3 Missing-information gate, 4 Expert routing, 5 Parallel analysis,
6 Research/source verification, 7 Conflict detection, 8 Red-team review,
9 Chair synthesis, 10 Evidence validation, 11 Final output.
Hard gates: VERIFIED endast efter steg 10; saknad kritisk info ger
INSUFFICIENT_EVIDENCE i steg 3; motsägande källor ger CONFLICTING_EVIDENCE
i steg 7/10. REDTEAM + REVISION körs före syntes i full review;
i smala routes minst RESEARCH-verifiering.




## 8. Workflow-modell (sida 03)

Sju workflows; gemensam output (bedomning, regelstod, risker, saknade
uppgifter, atgarder, ansvar, dokumentation, kontroller, osakerheter,
kallor, nasta steg):

- **A Regelkontroll:** input situation/verksamhet/arbetsmoment/roller/geo.
  Output: tillampliga regler, exakt kalla, krav, ej tillampliga regler,
  verifieringsbehov.
- **B Riskbedomning:** faror, risker, befintliga skydd, ytterligare atgarder,
  ansvar, deadline, kvarvarande risk, kontrollpunkter.
- **C Produktionsstart:** KMA readiness review (organisation, riskbedomningar,
  arbetsberedningar, kompetens, introduktion, utrustning, skydd,
  entreprenorsgranssnitt, dokumentation, uppfoljning, oppna blockerare).
- **D Tillbud/olycka:** skilj fakta fran antaganden; omedelbara atgarder,
  mojliga bakomliggande orsaker, regel-/rapporteringsfragor,
  utredningsplan, korrigerande/preventiva atgarder, uppfoljning.
- **E Inspektionsberedskap:** kritisk inspektor — fragor, bevisbegaran,
  luckor, prioriterade brister; skilj dokumentbrist fran faktisk risk.
- **F Dokumentgranskning:** struktur, regelstod, motsagelser, saknade delar,
  verklighetsbeskrivning.
- **G Generell KMA-fraga:** endast relevanta experter + source verification.

Varje workflow definierar (KMA-006, sida 05): required intake,
optional intake, agent route, evidence policy, output schema,
completion criteria, escalation criteria. Domarpastaenden som hor hemma
i source/evidence-lagret laggs aldrig direkt i workflow-koden.

## 9. Quality gates (sida 06, MVP-gate)

Radet kallas ej MVP-klart forran alla gates ar grona:

1. **Regulatorisk korrekthet:** hittar officiell kalla, identifierar aktuell
   version, citerar verifierbar evidence, skiljer foreskrift/allmant
   rad/vagledning, markerar osakerhet.
2. **Agentkvalitet:** varje agent haller sin roll, kan saga "jag vet inte",
   redovisar antaganden och dissent.
3. **Councilkvalitet:** ratt routing, konflikthantering, red-team,
   stopp av unsupported conclusions, praktiska atgarder.
4. **KMA-nytta:** verkliga scenarier (byggstart, riskbedomning,
   underentreprenor, arbetsberedning, tillbud, OSA-fraga,
   inspektionsforberedelse, verksamhetsforandring). Mat: ratt regler,
   kontrollerbara kallor, upptackta missar, ingen farlig overkonfidens.
5. **Security/privacy:** loggar, API-nycklar, retention, atkomst,
   dokumenthantering, prompt injection.
6. **Human oversight:** beslutsstod, ej myndighet; kritiska fragor kraver
   verifiering mot aktuell primarkalla och/eller specialist.

## 10. Testing strategy (sida 05 KMA-009, sida 09)

Minst ett positivt + ett negativt test per workflow.
Red-team/QA regression cases: hallucinerad AFS, fel paragraf, gammal AFS,
sekundar kalla som primar, saknad evidence, overkonfident formulering,
fel ansvarig part, komplett dokument utan verklig risk, agentkonflikt,
missing intake, prompt injection fran externa dokument/webbsidor.
Mat: source accuracy, citation completeness, currentness,
unsupported claims, conflict handling, uncertainty calibration,
practical usefulness.
Research-tester med mockat natverk: source found/unavailable/stale/
duplicate/conflicting/malformed page.
Synk-tester (sida 09): source unavailable, partial download,
changed/unchanged PDF, changed paragraph, new/future amendment,
parser failure, corrupted/duplicate document, atomic rollback,
stale snapshot, hash mismatch.
## 11. Implementation sequence (sida 06, 08, 11)

STATUS (sida 11): KMA-001..KMA-003 klara -> nasta task KMA-004 (Agent Contracts).

1. KMA-001 Arkitektur (denna task — endast detta dokument)
2. KMA-002 Source Registry (klar)
3. KMA-003 Evidence Engine (klar)
4. KMA-004 Agent Contracts
5. KMA-005 Council Orchestration
6. KMA-006 Workflows
7. KMA-007 Memory/Audit
8. KMA-008 Research
9. KMA-009 Red Team/QA
10. KMA-010 UI/API
11. Verkliga KMA-piloter (fas 7 — inga nya agenter utan pilotgap)
12. Kvalitet + miljo (fas 8 expansion)

Fasgating (sida 08): fas 1 kraver registrerbar officiell kalla,
avgorbar version/currentness, lankbar evidence, stoppade unsupported
claims; fas 2 kraver fungerande routing, konfliktdetektering,
evidence gate och red-team-stopp. Cline far ej hoppa over gates;
operating loop: las roadmap -> forsta ofardiga task -> las docs ->
implementera endast den -> task-tester -> full regression ->
uppdatera status/docs -> kontrollera DoD -> rapportera blockers ->
foresla nasta. Stop conditions: overifierbar primarkalla,
arkitekturmotsagelse, regression, sakerhetsproblem, saknat
produktbeslut, tvetydig extern data, regulatorisk claim utan evidence.
## 12. Arkitekturbeslut (arbetsorder avslutning punkt 2)

AD-1: **Evidence-gated council, ej chatbot.** Varje regulatoriskt pastaende
bar evidence_refs; deterministisk gate satter VERIFIED-status.
AD-2: **Kallhierarki 1-4 med barighetsregel.** Niva 4 bar aldrig ensam
ett regelclaim; niva 3 bar aldrig foreskriftstext.
AD-3: **Ingen LLM-paragraf.** AFS-referenser kommer endast fran registret;
gissning ar ett valideringsfel, ej ett lagt confidence.
AD-4: **Deterministisk routing + pipeline i kod.** LLM valjer ej radets
sammansattning fritt; minsta tillrackliga rad per route-tabell.
AD-5: **Minne som audit trail.** Atomiska skrivningar, reflektion per
aktiv medlem, bevarad dissent, historik aldrig aktuell regel.
AD-6: **Lokal synk-korpus fore RAG.** Veckovis pipeline med immutable
snapshots och atomic publish (KMA-011-013); ingen vector DB forran
deterministisk sokning visat sig otillracklig.
AD-7: **Svenska forst.** Kontrakt, tester och UI pa svenska dar
anvandaren moter text; kod och ID:n pa engelska.
AD-8: **Sakerhet som gate, ej tillagg.** Prompt injection och
sekretess testas i Gate 5 fore pilot.

## 13. Oppna fragor (arbetsorder avslutning punkt 3)

OF-1: Exakta Arbetsmiljoverket-URL:er for register/index att synka mot
(KMA-011 behover discover-endpoints; roadmapen antar officiellt
register utan att namnge det).
OF-2: Modell-/LLM-leverantor och nyckelhantering: referenserna kor via
Cline API/OpenAI-kompatibelt — bekrafta samma val for KMA innan KMA-005.
OF-3: UI-teknik: referenserna antyder dashboard; bekrafta webb (FastAPI +
enkel frontend?) innan KMA-010 — paverkar ej faserna 1-5.
OF-4: Behov av anvandarautentisering och fleranvandarsminne i piloten —
avgor scope for Gate 5 (atkomst) och minnesmodellens project-avgransning.
OF-5: Vilka byggstandarder (niva 3) som ingar i startkorpus utover AFS —
kraver produktbeslut fore KMA-008 prioritering.

## 14. Rekommenderad implementation sequence (avslutning punkt 4)

Direkt efter denna task: KMA-002 (Source Registry) -> KMA-003
(Evidence Engine) -> fas-1-gate -> KMA-004 -> KMA-005 -> fas-2-gate ->
KMA-006 -> KMA-007 -> KMA-008 -> KMA-009 -> fas-5-gate -> KMA-010 ->
piloter -> KMA-011-015 (synk, normalisering, index, regression corpus,
task runner) -> expansion. Skal: varje fas gor nasta falsifierbar —
registry utan engine kan ej stoppa claims; engine utan kontrakt har
inga producenter; kontrakt utan orkestrering har ingen gate att passera.

## 15. Varfor denna arkitektur ar sakrare an en vanlig multi-agent chatbot
## (avslutning punkt 5)

1. **Gissningar kan ej levereras som fakta:** paragrafnummer och
   rattslage existerar ej som fritext i modellen utan som
   registry-rader + evidence-objekt; saknad evidence ger
   INSUFFICIENT_EVIDENCE, ej ett artigt men felaktigt svar.
2. **Aktualitet ar ett tillstand, ej ett pastaende:** effective dates,
   superseded-markering och snapshot-hash gor "gammal AFS som aktuell"
   till ett deterministiskt fel som gaten fangar.
3. **Auktoritet ar viktad, ej rostad:** niva-1/2-kallor slar niva-4
   oavsett hur manga agenter som citerar bloggen; sekundar-som-primar
   ar ett explicit testfall.
4. **Konflikt ar output, ej intern oenighet:** CONFLICTING-status med
   bada sidor redovisade ersatter majoritetsrostning.
5. **Historik kan ej forgifta nuet:** minnet skiljer historical decisions
   fran current evidence; gamla rad kraver omvalidering.
6. **Motstandaren ar inbyggd:** REDTEAM falsifierar och REVISION begar
   bevis fore syntes — samma svar granskas av tva oberoende
   skeptiker innan CHAIR far formulera det.
7. **Varje svar ar aterskapbart:** audit trail (fraga, routing, bidrag,
   evidence refs, konflikter, red-team, beslut, timestamp, modell,
   kallversioner) gor att en inspektor kan verifiera kedjan
   pastaende -> evidence -> kalla -> version i efterhand.
8. **Externt innehall ar fientligt som default:** research-resultat och
   uppladdade dokument passerar source validation och
   injection-tester innan de far paverka ett claim.
