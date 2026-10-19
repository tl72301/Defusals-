# Prior work check: "Who can cancel an allergy?"

Searched 2026-10-19 using web search and fetch only. The source repo (github.com/tl72301/Defusals-) is excluded and did not appear in any results. Overall, results are thin. Nothing found combines the planned design's core elements.

## Closest matches, ranked (0–5, where 5 = same experiment)

1. **OrderBench: "When JSON Is Not Enough: Semantic Reliability of Schema-Constrained LLM Ordering Agents"** (Yin Li, arXiv 2607.18261, May 2026). https://www.alphaxiv.org/abs/2607.18261. **2.5/5.** It uses restaurant ordering with categories for allergen and dietary conflicts. It has an "unsafe acceptance" metric, deterministic hand-coded oracles, and compares prompt-only output with JSON-schema output. Four open models were tested. *Different:* every case is a single turn, with no corrections or retractions and no speaker roles. The LLM itself decides accept or reject, whereas in the plan code decides. It uses no probabilities or Decisions API.
2. **Risky-Bench** (arXiv 2602.03100, Feb 2026). https://arxiv.org/pdf/2602.03100. **2/5.** This is a safety benchmark for food-delivery and restaurant agents. Rubric 15 says not to order allergens. In one case study, merchant metadata tells the agent it is "authorized to ignore 'Mango Allergy' flags", and the agent complies. This is the nearest example of an unauthorised party cancelling an allergy. *Different:* it is adversarial prompt injection only, with no legitimate corrections and no comparison of authority rules. The LLM agent acts end-to-end, and an LLM judges the result.
3. **"Will My Assistant Remember My Allergy?"** (Zhu et al., arXiv 2609.05767, Sep 2026). https://arxiv.org/abs/2609.05767. **1.5/5.** An allergy is mentioned once, and the paper tests whether it survives KV-cache compression (0–1% under compression vs 97% with full memory). It recommends an auditable store for safety-critical facts. *Different:* it has no retraction, no authority question, and no restaurant rules.
4. **Google Cloud Food AI evaluation framework for ordering agents.** https://docs.cloud.google.com/food-ai/evaluation. **1.5/5.** It covers allergen inquiries, mid-order changes of mind, and a deterministic final-cart matcher. *Different:* it has no authorization for who may change an order, and allergens are judged by an LLM.
5. **DoorDash "Allergy Shield" agent skill.** https://www.aitmpl.com/component/skills/doordash/doordash-allergy-shield. **1/5.** A deterministic hook blocks checkout of anaphylaxis-severity allergens, an example of "the agent proposes, code gates". *Different:* the allergy profile is static, so nothing covers retraction or authority, and it reports no evaluation.
6. **Confidence-threshold safety nets on decision models.** Vercel AI Gateway "Decision Fallbacks" (https://vercel.com/docs/ai-gateway/models-and-providers/decision-fallbacks) re-runs a decision on another model when `confidenceBelow` is crossed. The DataCamp Decisions API tutorial (https://www.datacamp.com/tutorial/open-ai-decisions-api-tutorial) routes p<0.9 to manual review. AnyJev (https://pyshine.com/AnyJev-Turn-Any-LLM-Into-A-Calibrated-Decision-Model/) shows raw decision probabilities are poorly calibrated. **1/5** for the safety-net element. None of these is tested in a safety domain.
7. **Independent Decisions API probes.** Classmethod (https://dev.classmethod.jp/en/articles/openai-decisions-overview/) saw choice probabilities "pegged at 1.0". Towards AI (https://pub.towardsai.net/how-to-read-openais-new-decisions-api-score-rounding-it-can-pick-a-level-the-model-gave-0-e836b9fb3c5b) found that rounded `score` can name a level the model gave 0%. Eesel (https://www.eesel.ai/blog/openai-decisions-api) reports no calibration tests exist. Apidog's comparison with the Responses API ran no experiment. **0.5–1/5.** The API launched at DevDay on 2026-09-29 and went to public beta around 2026-10-07, so no third-party calibration or safety study exists yet.
8. **Lo et al. 2022**, "Reconciling Allergy Information in the EHR After a Drug Challenge Using NLP" (Frontiers in Allergy). https://pmc.ncbi.nlm.nih.gov/articles/PMC9234873. **1/5.** Rule-based NLP recommends "Delete" or "Add" allergy entries. Who has authority is explicitly left unclear. The **FHIR AllergyIntolerance** `verificationStatus` values "refuted" and "entered-in-error", with separate `asserter` and `recorder` fields, are a standards-level precedent for separating a retraction from a clerical error and recording who asserted it (https://terminology.hl7.org/en/CodeSystem-allergyintolerance-verification.xml.html). **0.5/5.**
9. **Source authority in LLMs.** ManyIH-Bench (arXiv 2604.09443) covers privilege-tiered instruction conflicts. "Whose Facts Win?" (arXiv 2601.03746) covers source preferences in knowledge conflicts. SycoEval-EM (arXiv 2601.16529) has patients pressuring a model to drop guidelines. **0.5/5.** All of these test whether the *LLM* respects authority. The plan moves authority into code.
10. **Allergen detection or food-safety LLM work.** FoodGuardBench (arXiv 2604.01444; single-turn FDA Food Code queries, including allergens), AllerGenie (Berkeley 2024), SafePlates (U Toronto 2024), Perrotta et al. 2025 (YOLO + Gemini meal photos), and Eržen 2020 (menu allergen thesis). **0.5/5.** Separately, a drive-thru testing blog (callsphere.ai) recommends always handing allergy mentions to a human.

## Verdict

The planned design appears **novel as a combination**. I found no work that (a) varies *who* retracts an allergy and *how* (self-correction by the guest, staff fixing their own ticket, a casual staff reassurance, a wrongful staff "correction", or a scope mismatch such as "nut allergy" vs "nuts are fine"), and (b) holds the LLM's readings fixed while comparing two deterministic authority rules ("any explicit correction" vs "guest-only removal"). I also found no restaurant or allergy study that compares Decisions API probabilities with Responses-API choices and with free-text extraction sorted by code.

Several elements overlap with existing work:
- **Code gates after the LLM, with unsafe-acceptance metrics:** OrderBench and the DoorDash skill.
- **An allergy wrongly overridden by a non-guest:** Risky-Bench, though only as adversarial injection.
- **A safety fact stated once:** PA-Bench.
- **A probability-threshold safety net:** productized by Vercel and DataCamp, with the same 0.9 cut-off in DataCamp's tutorial, but never evaluated.
- **The retraction vs entered-in-error distinction:** FHIR and EHR de-labeling work.

Two practical warnings come from the prior work. First, early users report Decisions API probabilities saturating at 1.0, so a 0.9 net may rarely fire; report how often it triggers. Second, use raw probability distributions, not rounded scores. The literature is very young: the Decisions API is about three weeks old, so a missing result partly reflects timing.

## Queries run (44)

**Allergy, ordering and food safety:**
- LLM food allergy restaurant ordering benchmark allergen detection menu
- site:github.com allergen detection LLM recipe menu FDA major allergens
- "FoodAllergyBench" OR "allergy benchmark" LLM
- arXiv LLM food allergen identification ingredients
- github allergy-aware restaurant ordering chatbot LLM
- LLM food allergy safety evaluation chatbot 2025
- arxiv "food allergy" LLM conversational agent restaurant menu (extended)
- hidden food allergy restaurant AI waiter simulation kitchen ticket
- LLM extraction allergies conversation deterministic rules neuro-symbolic
- "allergen" GPT-4 recipes classification precision recall
- huggingface dataset food allergens FDA big 9
- kaggle food allergen dataset LLM
- site:github.com menu allergen extraction LLM json
- site:github.com restaurant order allergy LLM "FDA" kitchen ticket
- medium.com LLM classify order messages deterministic allergen rules
- substack/linkedin allergy LLM restaurant deterministic rules
- huggingface restaurant order dialogue allergy correction synthetic
- LLM "nut allergy" peanut vs tree nut ambiguity
- VitaBench allergy agent benchmark
- LLM agent food ordering allergy prompt injection third-party override

**Corrections and authority:**
- LLM medication allergy reconciliation EHR de-labeling
- NLP clinical notes "no longer allergic" de-labeled
- LLM allergy list reconciliation EHR removal study
- FHIR AllergyIntolerance verificationStatus refuted asserter
- nurse/pharmacist verbal order allergy override authority LLM
- drive-thru voice AI order correction allergy LLM evaluation
- spoken ordering self-correction "scratch that" LLM benchmark
- DST user corrections retraction "who can override"
- multi-party dialogue speaker authority allergy waiter customer
- LLM "instruction hierarchy" who can revoke constraint
- LLM source-aware belief revision "who said it"
- sycophancy LLM drops allergy constraint "it's fine"
- LLM multi-turn allergy mentioned once benchmark
- "only the guest" can remove allergy POS policy

**Decisions API:**
- OpenAI "Decisions API"
- "gpt-6-luna"
- "Decisions API" calibration experiment github
- "Decisions API" threshold abstain fallback
- site:github.com openai decisions api luna (two variants)
- "Decisions API" vs "Responses API" experiment
- "Decisions API" safety-critical medical/allergy/food
- HN Decisions API probabilities calibrated

**Exclusion check:**
- site:github.com tl72301 Defusals
