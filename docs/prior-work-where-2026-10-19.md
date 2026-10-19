# Prior-work check: "Does it matter where an allergy is written down, and can the AI tell whose allergy it is?"

Checked 19 October 2026. Tools: web search and web fetch only. No GitHub tools, no paid APIs.

## Verdict

**No.** I found nothing that runs this experiment. Nobody I found holds one allergy sentence fixed, moves it between author roles, channels and wordings (server ticket, manager note, host-stand note, "Reservation note for Table N:", kitchen chat) inside a multi-table stream, and then measures two things for each reader: how often the allergy is missed, and how often another table's note is applied to the order being asked about. I also found no published comparison of OpenAI's Decisions API with the ordinary Responses API on any extraction task. The Decisions API was announced on 29 September 2026 and went into public beta on 6 October 2026. Every source I opened says no accuracy comparison with Responses has been published, and the only measurements are informal forum posts.

The closest items each cover one piece:

- **OrderBench** ("When JSON Is Not Enough", 2026) tests restaurant ordering with allergens, and compares prompt-only JSON with schema-constrained output. It uses single-turn utterances and has no tables, notes or sources.
- **Vishwanath et al. 2026** ("LLMs are vulnerable to incidental information in clinical documentation") is the nearest work on wrong-entity contamination. Audio from an adjacent patient's encounter leaked into notes about the target patient. Its setting is ambient-scribe generation, not per-entity extraction with controlled source labels.
- **Source-framing studies** (Germani & Spitale 2025; Bajaj & Tiganj 2026) show that the same text under a different source label changes LLM behaviour. Their tasks are opinion rating and conformity, not extraction.

Clinical NLP work on note type and section is mostly section identification, or observational position effects. I found no controlled study that relocates the same fact across sections or authors. The planned test therefore looks new as a whole. Each of its two effects has neighbours: source-label framing, distractor and bystander interference, and entity-binding or merge errors.

## Queries run

1. LLM information extraction section header effect same fact different note section clinical
2. LLM allergy extraction clinical notes nursing notes vs physician notes missed allergies
3. large language model wrong patient error entity confusion multiple patients context
4. "wrong patient" large language model clinical notes multiple patients attribution error
5. source attribution framing effect LLM extraction same text different source label controlled experiment
6. LLM restaurant order allergy reservation notes AI evaluation
7. LLM multi-patient context contamination cross-patient information leakage summarization benchmark
8. LLM entity attribution errors multi-entity documents "attribute" fact to wrong entity benchmark
9. OpenAI Decisions API
10. Decisions API vs Responses API accuracy comparison benchmark gpt-6-luna classification
11. LLM food allergen extraction from orders benchmark nine major allergens
12. EHR allergy documentation discrepancies across note types natural language processing allergies not in allergy list
13. "document type" OR "note type" effect on LLM clinical information extraction performance same content
14. LLM sensitivity to metadata headers in prompt same content different header extraction robustness
15. contraindication extraction LLM missed when placed in different section of record perturbation study
16. counterfactual relocation of the same sentence across sections clinical note LLM extraction sensitivity
17. "who wrote it" author role nurse vs physician note LLM interpretation bias same text
18. LLM multi-party conversation "whose" attribution which speaker said what benchmark errors
19. LLM nursing shift handoff multiple patients summarization misattribution of findings between patients
20. entity tracking language models attribute binding errors interleaved entities benchmark
21. LLM agent multiple concurrent orders confusion order mix-up evaluation restaurant simulation
22. SevenRooms OR OpenTable OR Resy AI reservation notes allergy extraction guest profile
23. LLM allergy reconciliation free-text notes vs structured allergy list GPT-4 evaluation JAMIA
24. large language models identify allergies from clinical text accuracy by note source discharge summary nursing note
25. LLM "distractor" other patient record in context answer about target patient interference experiment
26. RAG "wrong entity" retrieved document about similar entity misapplied LLM measurement customer tickets
27. batch prompting cross-sample contamination multiple patients one prompt LLM clinical extraction errors
28. "multi-patient" prompt LLM information leakage between patients "cross-patient" errors study
29. AmbigDocs reasoning across documents different entities same name LLM merge answers
30. LLM streaming messages state tracking per entity "proactive interference" key value updates benchmark
31. github LLM kitchen ticket allergy table order simulation benchmark
32. huggingface dataset restaurant orders allergies dietary restrictions LLM evaluation
33. SIMMER benchmark latent failures LLM executable planning world model
34. Toast POS AI allergy modifier ticket kitchen display AI feature evaluation
35. "reservation note" OR "guest note" LLM extraction allergies hospitality AI accuracy study
36. hospital food service meal tray allergy LLM extraction diet orders evaluation
37. LLM attention to speaker role label "same message" different sender role changes model behavior experiment
38. LLM extraction performance varies by where information is documented in EHR section location allergies medications study 2025 (extended search)
39. arXiv perturbation "section header" removal or swap clinical note LLM robustness information extraction
40. LLM which customer does this note belong to misrouting notes between orders attribution accuracy experiment
41. LLM food allergy safety restaurant study chatbot misses allergens evaluation paper 2025 2026
42. LLM allergen detection menu items allergy-aware recommendation benchmark arXiv
43. LLMs credibility source labels same information "attributed to" doctor nurse patient changes answer clinical
44. LLM conversation disentanglement interleaved threads group chat attribution evaluation 2025
45. structured outputs vs free-text generation LLM extraction accuracy comparison constrained choice enum vs open generation recall
46. "Decisions API" OpenAI evaluation recall misses "not mentioned" extraction test blog
47. github openai decisions api eval benchmark responses comparison repository
48. LLM allergy attribution "family history" vs patient allergy wrong attribution experiencer detection clinical NLP LLM
49. restaurant benchmark LLM agent waiter multiple tables orders dietary constraints arXiv
50. kaggle restaurant allergy notes dataset NLP classification orders
51. "When JSON Is Not Enough" Semantic Reliability of Schema-Constrained LLM Ordering Agents
52. arXiv 2610.08585 ambient scribe small talk adjacent patient audio Vishwanath Oermann
53. LLM generated handoff I-PASS multiple patients errors attributed to wrong patient evaluation
54. LLM reads messages sequentially stream per-entity question "for order" distractor other entity same fact misapplied evaluation agent memory
55. OpenTable AI guest notes summary allergies dietary restrictions feature 2026
56. LLM clinical information extraction "nursing notes" versus "physician notes" performance difference allergies medications GPT
57. "note author" role metadata nurse physician language model attention underweighting nursing documentation study
58. LLM ignores information in administrative or non-clinical sections "registration" "scheduling note" missed clinical fact
59. same fact placed in different document type LLM recall "document type" framing ablation "email" "memo" "chat log" extraction
60. "host stand" OR "server notes" LLM allergy experiment restaurant AI misses allergy blog
61. "Decisions API" allergy OR allergen OR "food safety" test
62. lost in the middle clinical notes LLM extraction position of fact in long patient record recall drops
63. github restaurant LLM agent allergy safety order routing kitchen "allergen" evaluation repo
64. LLM "header" vs "body" mention entity which entity a note refers to attribution errors emails tickets study
65. LLM medication reconciliation multiple sources nursing intake note pharmacy note discrepancy which source missed GPT-4 study
66. restaurant food allergy communication front of house back of house order ticket errors study CDC EHS-Net

## Nearest items

1. **When JSON Is Not Enough: Semantic Reliability of Schema-Constrained LLM Ordering Agents** (OrderBench). Yin Li, University of Birmingham. https://www.alphaxiv.org/abs/2607.18261 (arXiv 2607.18261), 2026.
   - **What it does:** A deterministic restaurant-ordering benchmark of 300 cases, using a seven-item menu with allergens and dietary tags, run on four open models. It scores schema validity, item semantics, allergen preservation and "unsafe acceptance," and compares prompt-only JSON with provider JSON-schema mode. Allergen conflicts had some of the highest unsafe-acceptance rates.
   - **How it differs:** Each case is one customer utterance. There are no tables, no stream, no notes from different staff roles, and no measure of one order's allergy being applied to another. It compares two JSON modes, not a choice API with free generation.

2. **Large language models are vulnerable to incidental information in clinical documentation and reasoning.** Vishwanath, Ye, Alyakin, Markert, Hsieh, Mańkowski, Oermann. https://arxiv.org/abs/2610.08585, 2026 (submitted 6 Oct 2026).
   - **What it does:** In 57 mock consultations, background speech from a separate patient's encounter leaked into 48.2% of transcripts and contaminated 5.3% of downstream notes. In 576 dialogues, small talk appeared in 35% of notes and was misattributed or used clinically in 3.7%.
   - **How it differs:** This is the closest wrong-entity contamination result. It concerns audio and free-text note generation, and does not vary where or by whom a fact is written. The abstract does not say whether "contamination" means the fact was attributed to the target patient.

3. **Medical large language models are easily distracted** (MedDistractQA). Vishwanath et al. https://arxiv.org/html/2504.01201v1, 2025.
   - **What it does:** Adds "bystander" distractors to USMLE-style questions, giving a medical detail about a third party ("my aunt's fish had a heart attack"). Accuracy falls by up to 17.9%.
   - **How it differs:** It measures the overall accuracy drop on multiple-choice QA, not whether the other person's fact is applied to the target. There is no per-entity stream and no variation of source or channel.

4. **ClinicalBench: Stress-Testing Assertion-Aware Retrieval for Cross-Admission Clinical QA on MIMIC-IV.** Alex Stinard. https://arxiv.org/pdf/2605.11143, 2026.
   - **What it does:** Includes an experiencer field (patient or family). It reports one configuration "leaking" family findings into patient state (for example, "The patient has Lymphoma"), which a propagation fix improved by 10 percentage points.
   - **How it differs:** It is about attributing a fact to the patient versus a family member within one patient's record, retrieved through a knowledge graph. It has no other-patient negative control and no controlled manipulation of note type or author.

5. **AmbigDocs: Reasoning across Documents on Different Entities under the Same Name.** Lee, Ye, Choi. https://arxiv.org/abs/2404.12447v2, 2024.
   - **What it does:** A benchmark showing that LLMs merge information belonging to different entities that share a name.
   - **How it differs:** It uses Wikipedia documents and open QA. The entities share a name rather than being distinct labelled orders, and there is no variation of source or header.

6. **Unable to Forget: Proactive Interference Reveals Working Memory Limits in LLMs Beyond Context Length** (PI-LLM). Chupei Wang, Jiaqiu Vince Sun. https://arxiv.org/pdf/2506.08184, 2025.
   - **What it does:** Streams interleaved key-value updates and asks for the latest value of each key. Accuracy falls roughly log-linearly as interference grows, and most errors are earlier values of the same key.
   - **How it differs:** It uses synthetic key-value pairs and measures within-key staleness, not cross-entity misapplication. Source labels and wording are not varied.

7. **Source framing triggers systematic evaluation bias in Large Language Models.** Germani, Spitale. https://arxiv.org/abs/2505.13488v1, 2025.
   - **What it does:** Holds 4,800 statements fixed and changes only the stated source (blind, another LLM, or a human of a stated nationality). Model agreement shifts depending on the attribution.
   - **How it differs:** It shows the same "same text, different source label" design, but the task is rating agreement, not extracting a fact. The sources are nationalities, not staff roles or channels.

8. **Who Do LLMs Trust? Human Experts Matter More Than Other LLMs.** Bajaj, Tiganj. https://www.alphaxiv.org/abs/2602.13568.md, 2026.
   - **What it does:** The same prior answers are labelled as coming from friends, experts or LLMs. Models conform more to answers labelled as from experts.
   - **How it differs:** It measures conformity in yes/no QA, not whether a fact is extracted or missed depending on who wrote it.

9. **The Medium is the Message: How Non-Clinical Information Shapes Clinical Decisions in LLMs.** Gourabathina, Pan, Gerych, Ghassemi (FAccT 2025). Read via MIT News: https://news.mit.edu/2025/llms-factor-unrelated-information-when-recommending-medical-treatments-0623, 2025.
   - **What it does:** Keeps clinical content fixed and perturbs presentation (gender markers, colourful or uncertain language, typos, whitespace). Self-management recommendations shifted by 7 to 9%.
   - **How it differs:** It tests how a note is written, not which channel or author it comes from. The task is a treatment recommendation, not extraction. I read only the MIT News coverage, not the paper.

10. **Measuring the sensitivity of LLM-based structured extraction to prompt, model, and schema choices in clinical discharge summaries.** Martin Murin. https://arxiv.org/pdf/2606.05970, 2026.
    - **What it does:** Holds the notes fixed and varies prompt wording, model size and schema granularity. Most disagreement falls on the "no" versus "not documented" distinction, which resembles the planned test's "not mentioned" misses.
    - **How it differs:** Fact placement is never varied, and only discharge summaries are used.

11. **Inhibitory Attention for Clinical Long-Context Reasoning: Characterizing and Mitigating Lost-in-the-Middle Effects in EHR Processing.** https://arxiv.org/abs/2608.20348, 2026.
    - **What it does:** Reports that accuracy on EHR questions depends on where the answer sits in the record (peaking at 59.5% and dropping to 37.6%).
    - **How it differs:** The position effect is observational, using natural answer locations in MedAlign rather than relocating the same fact. Section and note type are not treated as variables.

12. **Beyond Prompts: Dynamic Conversational Benchmarking of Large Language Models** (LTM Benchmark). Castillo-Bolado, Davidson, Gray, Rosa. https://arxiv.org/pdf/2409.20222, 2024 (NeurIPS Datasets and Benchmarks).
    - **What it does:** Interleaves several tasks in one long conversation, and performance degrades under interleaving. It includes a restaurant role-play in which the agent is the diner.
    - **How it differs:** It has no allergy extraction and no per-entity attribution measure. Interference is measured only as lower task success.

13. **Let Me Speak Freely? A Study on the Impact of Format Restrictions on Performance of Large Language Models.** Tam et al. https://arxiv.org/html/2408.02442v1, 2024.
    - **What it does:** Compares constrained formats (JSON mode, format instructions) with free generation. Constraints hurt reasoning tasks but are competitive or better on classification with fixed label sets.
    - **How it differs:** This is the general "structured choice vs generation" question, but it does not cover the Decisions API, extraction misses by location, or entity attribution.

14. **OpenAI Developer Community thread on the Decisions API public beta.** https://community.openai.com/raw/1403877, October 2026.
    - **What it does:** Contains the only hands-on comparisons I found. One user compared Decisions with TypeSafe's Jev, finding about three times as many confident wrong answers from Luna on nuanced judgments. Another ran a calibration check in which the "choice" format returned "heads" 98% of the time for a coin biased to 70% heads, and option order changed the probabilities.
    - **How it differs:** It is informal and does not compare against the Responses API. Related articles (apidog, https://apidog.com/pt/blog/openai-decisions-api-vs-responses-api/, 10 Oct 2026; horadecodar, https://horadecodar.com.br/decisions-api-casos-rotulados/, 7 Oct 2026) explicitly say no accuracy comparison with Responses has been published. Promptfoo has added an `openai:decisions` provider (https://www.promptfoo.dev/docs/providers/openai-decisions/, updated 17 Oct 2026), so tooling exists, but no results are published.

15. **Chunk Anchoring — A Simple Technique to Prevent Ticket ID Hallucination in RAG.** Classmethod. https://dev.classmethod.jp/en/articles/rag-chunk-anchoring-ticket-id-hallucination-prevention/, 12 July 2026.
    - **What it does:** An engineering blog post. When a ticket's ID sits only in the header and later chunks lack it, the LLM attaches the wrong or an invented ticket ID. The fix is to repeat the ID in every chunk.
    - **How it differs:** It is anecdotal with no before-and-after rate. It resembles the planned contrast between "other table named only in the header" and "other table named in the text," but nothing is measured.

## What exists in parts

- **Same content, different source label:** Shown for opinion rating, conformity and sycophancy (items 7 and 8, plus a 2026 medRxiv factorial study on stated user credentials, https://www.medrxiv.org/content/10.64898/2026.08.28.26361634). None of these tests fact extraction, staff roles, or wordings such as "reservation."
- **Clinical note type and section:** The work is mostly section identification, for example "LLM-Based Section Identifiers Excel on Open Source but Stumble in Real World Applications" (https://arxiv.org/pdf/2404.16294) and MedSlice. There are observational position effects (item 11), single-variable in-place counterfactual edits (DeVisE, https://arxiv.org/pdf/2506.15339, which edits values in place and never relocates them), and word-level noise (JMIR AI 2026, https://ai.jmir.org/2026/1/e83640). I found no study moving the same allergy or contraindication between note types or authors. Pre-LLM allergy NLP (for example JAMIA 2020, Wang et al., dynamic reaction picklist, DOI 10.1093/jamia/ocaa042) reconciles free-text and structured allergy entries but does not test note-type effects on a model.
- **Wrong-entity attribution:**
  - Neighbouring results: contamination from an adjacent patient (item 2), bystander distractors (item 3), family-versus-patient experiencer leakage (item 4), merging of same-name entities (item 5), proactive interference in streams (item 6).
  - Mechanistic work on how LLMs bind attributes to multiple entities (Bogdan and Lindsey, "Slot Machines," arXiv 2604.21139, 2026).
  - Speaker-attribution errors in LLM transcription (Nolan and Burke 2026, BMC Med Inform Decis Mak, via https://healthmanagement.org/c/it/News/llm-errors-in-doctor-patient-transcripts).
  - None of these uses multiple labelled orders with a fixed question about one of them.
- **Restaurant and hospitality AI:**
  - Vendor content from SevenRooms and Carly (https://www.usecarly.com/blog/sevenrooms-ai/, AI note cleanup with no accuracy data), Hostie (https://hostie.ai/resources/2025-ai-vs-human-hosts-accuracy-showdown-restaurant-reservations, self-published "95% vs 78%" with no allergy metric), Mews feature requests for AI parsing of reservation notes (no allergy evaluation), and a Toast community idea for AI ticket-modifier cleanup (no evaluation).
  - Google Cloud's Food AI ordering-agent evaluation (https://docs.cloud.google.com/food-ai/evaluation) tests one session at a time, with one allergen-inquiry test case judged by an LLM.
  - SIMMER (arXiv 2606.14574, kitchen planning hazards) and VitaBench (food-delivery agents) have no allergy-from-notes or multi-table element.
  - Human-side evidence on restaurant allergy practice exists (CDC MMWR 2017, https://cdc.gov/mmwr/volumes/66/wr/mm6615a2.htm), but it does not cover how allergies are communicated or written down.
- **Decisions API versus generation:** I found no published study. There are general results on constrained versus free generation (item 13), and informal forum notes suggesting the choice format is miscalibrated and sensitive to option order (item 14). Those notes are worth checking as a confound when reading the Decisions misses.

### Caveats on coverage

Several arXiv PDFs came back empty through the fetch tool. For SIMMER and OrderBench I read the abstracts on chatpaper and alphaxiv instead. PMC pages were blocked by a reCAPTCHA. The Gourabathina paper was read only through MIT News coverage. Search coverage of items from the last two to three weeks (October 2026) may be incomplete.
