# Prior-work check: "Just ask the guest?"

Date: 2026-10-19, before any message text for the test existed (ALLERGY_PROTOCOL.md §10). Run by a research agent
with web search only; five earlier queries on indirect yes/no answers are included in spirit (Circa, Wang et al. 2024,
Risky-Bench and commercial allergy bots were already known). The search for the first October 19 test is in
[prior-work-2026-10-19.md](prior-work-2026-10-19.md).

Scope: web search (WebSearch + WebFetch only) across arXiv, ACL Anthology, PMC/JMIR/medRxiv, Hugging Face, Kaggle mirrors, GitHub (via web search only), dev.to/Medium/Substack, and restaurant-tech product pages and docs. No GitHub MCP tools were used. Known items (Circa, Wang et al. 2024, Risky-Bench, hostie.ai, loman.ai, OrderBench, this repository) were not re-reviewed except to compare against.

## Queries run (60)

More than the 25 to 35 planned: the first 30 turned up nothing direct, so the rest ruled out near misses in each of five areas (a code or rule that asks the person before a constraint is removed; reading indirect yes/no answers where safety matters; restaurant allergy pipelines tested on simulated orders; read-back and closed-loop checks with LLMs; hospital allergy de-labelling and reconciliation).

1. LLM food allergy restaurant order simulation safety evaluation
2. LLM interpreting indirect answers yes-no questions medical intake allergy safety
3. large language model penicillin allergy delabeling who can remove allergy label
4. ChatGPT penicillin allergy risk assessment PEN-FAST large language model study
5. LLM EHR allergy list reconciliation natural language processing allergy entries
6. "closed-loop communication" LLM evaluation read-back safety
7. LLM agent asks user confirmation before overriding safety constraint third party instruction allergy
8. "Cooking Up Risks" benchmarking food safety risks large language models allergen
9. "Medication counseling with large language models" flexibility rigidity
10. restaurant AI ordering allergy "clarifying question" LLM benchmark simulated customers
11. "yeah no" discourse marker polarity LLM interpretation
12. teach-back LLM evaluation patient comprehension check large language model
13. food allergy chatbot LLM evaluation "allergen" simulated diners study 2025 2026 arXiv
14. LLM allergy history taking chatbot patient interpret answers evaluation drug allergy interview
15. LLM penicillin allergy delabeling chatbot direct oral challenge eligibility GPT-4 accuracy
16. github restaurant allergy order simulation LLM agent allergen guardrail
17. huggingface dataset indirect answers yes no questions allergy food dietary
18. LLM clinical decision support "allergy override" alert LLM evaluation who can override
19. large language models resolving allergy discrepancies across clinical notes contradictory allergy documentation
20. LLM agent memory conflicting updates from different sources authority who can revoke constraint benchmark
21. CURATe benchmark personalised alignment safety-critical constraints allergy conflicting preferences third parties
22. LLM peanut allergy benchmark agent forgets user constraint later message "allergy" multi-turn
23. pharmacy chatbot LLM patient answers "no" ambiguous negation misinterpretation safety evaluation contraindication screening
24. AI agent removes allergy from chart requires patient verification human-in-the-loop LLM EHR write safety
25. restaurant POS allergy modifier "allergy" ticket kitchen display staff override confirm guest software
26. LLM understanding elliptical short answers "yep" "nope" dialogue question context benchmark
27. indirect answers yes-no questions doctor-patient conversations dataset clinical dialogue polar question response classification
28. food delivery special instructions allergy notes NLP classification LLM Uber Eats DoorDash Deliveroo allergen detection
29. LLM order-taking read-back confirmation drive-thru voice AI accuracy study allergy
30. tau-bench style restaurant domain agent policy allergy benchmark simulated user
31. LLM probability calibration yes/no answer interpretation abstain ask again threshold safety-critical confirmation question
32. "allergy" "correction" handoff note conflict LLM nurse handoff safety evaluation simulated
33. LLM sycophancy clinician claims "allergy is fine" overrides contraindication authority bias evaluation
34. CaMeL provenance policy code enforces LLM agent data flow "only user" authorization deterministic policy
35. Kaggle restaurant orders allergy dataset simulated LLM
36. LLM chatbot pre-visit patient confirms allergy list reconciliation "remove" allergy patient-reported study
37. voice agent allergy confirmation question guest "does anyone in your party have" AI host reservation notes allergy
38. "scope" answer "not me, my daughter" LLM interpretation who the answer refers to allergy question multi-person dialogue
39. GPT-4 extract penicillin allergy history from clinical notes delabeling candidates large language model 2025
40. "Interpreting Answers to Yes-No Questions" follow-up 2025 2026 LLM evaluation safety domain indirect answers
41. "Just ask" confirmation gate LLM agent human-in-the-loop safety constraint removal experiment code-enforced rule ask affected person
42. arXiv kitchen ticket allergy LLM restaurant service simulation multi-agent waiter chef allergen
43. Medium Substack "allergy" AI agent "staff says" guest confirmation restaurant LLM safety rule blog
44. ACL anthology answer polarity "yeah no" "no yeah" corpus English discourse NLP classifier
45. LLM nurse triage telephone yes/no symptom answers misinterpretation hedged responses patient simulated replies robustness
46. LLM verbal medication order read-back verification evaluation "read-back" clinical large language model
47. huggingface datasets food allergy restaurant conversation dialogue dataset allergen waiter
48. github LLM allergy guardrail "only the patient" OR "only the guest" can remove allergy rule simulation repo
49. chatbot penicillin allergy history patient self-assessment conversational agent delabelling pathway evaluation
50. LLM answer interpretation "yes/no" negation polarity errors "No, I'm allergic" medical chatbot misread study
51. LLM medical flowchart navigation patient response interpretation yes no node accuracy simulated patient conversations varied phrasing
52. OpenTable SevenRooms reservation allergy note AI kitchen ticket guest verification feature 2026
53. LLM agent clarification question cost-benefit when to ask user benchmark risk of acting vs latency of asking safety-critical
54. AllergyBench OR AllergenBench LLM benchmark food allergy safety 2026
55. LLM structured output option probabilities vs free-text vs category mapping comparison same model classification reliability safety threshold
56. "Large language models are not zero-shot communicators" implicature yes no indirect answer evaluation
57. caregiver or family member says patient not allergic verify with patient AI assistant policy medication allergy proxy reporter reliability
58. HCI study conversational agent food allergy communication diners servers restaurant chatbot CHI CSCW
59. site:github.com allergy LLM restaurant order simulation safety policy evaluation
60. "verificationStatus" refuted allergy FHIR who can refute allergy patient-reported asserter AI agent

## Nearest items (15), closest first

1. **Multi-agent Self-triage System with Medical Flowcharts** (Liu, Yu, Jin, ... Qin, Liu, Wang)
   - Link: https://arxiv.org/abs/2511.12439
   - Year: 2025 (v2 Dec 2025)
   - What it does: An LLM "decision agent" reads patients' free-text answers to yes/no questions in 100 AMA triage flowcharts. Code moves to the next step only on a confident Yes or No; uncertain or off-topic answers keep the patient at the same question. The evaluation uses 37,200 synthetic replies in set styles (brief, e.g. "Nope"; descriptive; weak or hedged; uncertain; off-topic), with 5 Yes and 5 No replies per question. Errors are broken down by style, and a "certain and incorrect" reading is the unacceptable outcome. Its failure analysis names the same polarity trap we test: a sentence that opens with "No" but means yes gets misread.
   - How it differs: This is general symptom triage, not an allergy that someone else is trying to cancel. There is no staff-versus-guest authority and no comparison of who may lift a constraint. The yes/no question is part of the flowchart, not something code sends because a third party said "it's fine". It has no "scope" answers (another person at the table), uses one way of reading per model, and does not measure how long a decision waits. **It is the closest prior work to how this test reads the guest's answers, including the answer styles.**

2. **CURATe: Benchmarking Personalised Alignment of Conversational AI Assistants** (Alberts, Lupu, Ellis, Foerster)
   - Link: https://arxiv.org/abs/2410.21159
   - Year: 2024 (revised 2025)
   - What it does: The user states a safety-critical constraint, such as "I am severely allergic to dairy". Later, one to three other people state strong preferences that conflict with it. The benchmark measures whether the LLM's recommendation still respects the user's constraint.
   - How it differs: The LLM itself decides; no code rule is applied. The third parties never claim the constraint was a mistake. Models were told not to ask questions, so there is no ask-the-user step. No yes/no replies are read.

3. **Will My Assistant Remember My Allergy? What Personal LLM Assistants Forget When Conversation Memory Is Compressed** (Zhu, Lin, Wang, Liu, Li, Chen; Duke)
   - Link: https://arxiv.org/abs/2609.05767
   - Year: 2026
   - What it does: Shows that an allergy mentioned in passing almost never survives memory compression (0-1%). It recommends an auditable store for safety-critical facts and "an interface that asks rather than invents". Its design notes suggest read-back confirmation ("noted, allergic to penicillin") and asking when memory is missing.
   - How it differs: Facts are lost, never retracted by someone else. The ask-the-user idea is a recommendation the paper does not test. It compares no who-may-cancel rules and reads no replies.

4. **Medication counseling with large language models: balancing flexibility and rigidity** (Sabel, Wingren, Lundell, ... Andtfolk; Åbo Akademi)
   - Link: https://arxiv.org/abs/2601.11544
   - Year: 2025/2026
   - What it does: A multi-agent counseling system for emergency contraception at the pharmacy. A YAML spec and tools supply the rigid parts. The agent asks the customer about allergies and contraindications, confirms answers, and re-confirms them if the customer changes them.
   - How it differs: No third party cancels anything and no rules are compared. It has no systematic test of yes/no reply styles and no outcome metrics like ours.

5. **Building an allergy reconciliation module to eliminate allergy discrepancies in electronic health records** (Blackley, Lo, ... Blumenthal, Goss, Zhou; Mass General Brigham)
   - Link: https://academic.oup.com/jamia/article/32/4/648/8024251
   - Year: 2025
   - What it does: An EHR module finds allergy discrepancies across sources in five ways (F1 0.86-1.0) and suggests fixes such as removals. Primary care physicians accept or reject the suggestions.
   - How it differs: It uses rules and NLP, not an LLM. The clinician decides; the patient is never asked as a gate. It compares no who-may-remove rules and simulates no replies.

6. **Reconciling Allergy Information in the EHR After a Drug Challenge Using NLP** (Lo et al.)
   - Link: https://www.frontiersin.org/articles/10.3389/falgy.2022.904923/full
   - Year: 2022
   - What it does: NLP finds allergy-list entries that negative drug-challenge results contradict and flags them for reconciliation (de-labeling).
   - How it differs: Removal rests on an objective test result, not on what anyone says. It uses no LLM, asks no question, and compares no authority rules.

7. **Auditable Emergency Triage for Maternal and Newborn Care in India** (Jagga, Dalmia, ... Arora)
   - Link: https://arxiv.org/abs/2609.09356
   - Year: 2026
   - What it does: The LLM pulls standard symptoms and context out of a message, and a fixed rule engine in code decides whether it is an emergency. This is the same "AI reads, code decides" split we use.
   - How it differs: It has no constraint for anyone to cancel, no question sent back, no authority rule, and no reply-style test.

8. **Lilac Labs (YC S24) drive-thru voice AI tested with Hamming AI** (customer spotlight)
   - Link: https://hamming.ai/blog/lilac-labs-customer-spotlight
   - Year: 2025
   - What it does: A commercial drive-thru ordering agent tested continuously with about 5,000 simulated call scenarios, including allergies and dietary restrictions. The post says allergy bugs caught before launch were the most important result.
   - How it differs: This is product QA, not a study. It has no staff override, no confirmation rule, and no published comparison of unsafe sends against needless holds.

9. **Google Cloud Food AI: Evaluate ordering agents using the evaluation framework** (product docs)
   - Link: https://docs.cloud.google.com/food-ai/evaluation
   - Year: 2025-2026
   - What it does: Simulates customer sessions, either scripted or with an LLM playing the customer, then checks the final cart and uses LLM-judge checks such as "agent confirmed X before finalizing". Its examples include a peanut-oil question.
   - How it differs: It is a general test harness with no allergy-cancel policy, no staff role, and no comparison of rules.

10. **When Memory Becomes Authority: Benchmarking Authority Collapse at the Memory Consolidation Boundary** (Zhan, Zhang, Guo, Zhao, Liu)
    - Link: https://arxiv.org/abs/2608.01679
    - Year: 2026
    - What it does: Keeps a claim fixed and changes only who it came from, then tests whether agents let low-authority sources become user facts or standing instructions.
    - How it differs: It covers general agent memory, not allergies. It sends no question back to the authoritative person, and the model labels authority rather than a fixed code rule.

11. **SycoEval-EM: Sycophancy Evaluation of LLMs in Simulated Clinical Encounters for Emergency Care** (Peng, Wang, ... Rose)
    - Link: https://arxiv.org/abs/2601.16529
    - Year: 2026
    - What it does: A simulated patient pushes a doctor agent to drop guideline constraints (CT, antibiotics, opioids). Across 19 LLMs, models gave in anywhere from 0% to 100% of the time.
    - How it differs: The LLM decides with no code rule. The pressure comes from the patient, not staff, and there is no ask-back step.

12. **Value of Information: A Framework for Human-Agent Communication** (Dong, Hu, Hui, Zhang, Vulić, Bobu, Collier)
    - Link: https://arxiv.org/abs/2601.06407
    - Year: 2026 (ACL 2026)
    - What it does: A decision-theoretic rule for when an agent should ask a clarifying question and when it should commit, weighing what is at stake against the cost to the user. Tested in four domains, including medical diagnosis.
    - How it differs: The question is triggered by uncertainty, not by a third party cancelling. It has no allergy setting, no fixed readings, and no who-may-cancel comparison.

13. **Cooking Up Risks: Benchmarking and Reducing Food Safety Risks in LLMs (FoodGuardBench)** (Luo, Wen, ... Gligorić, Chen)
    - Link: https://arxiv.org/abs/2604.01444
    - Year: 2026
    - What it does: 3,339 food-safety queries based on FDA guidelines, plus jailbreak tests and a guardrail model (FoodGuard-4B).
    - How it differs: Single-turn questions and jailbreaks only. No ordering, no allergy cancellation, no confirmation.

14. **Large language models are not zero-shot communicators** (Ruis et al.)
    - Link: https://arxiv.org/abs/2210.14986
    - Year: 2022/2023 (NeurIPS 2023)
    - What it does: Tests whether LLMs resolve implicature in indirect answers to yes/no questions, close to Circa in style.
    - How it differs: General everyday domain with no safety stakes, no scope or polarity-trap categories, and no downstream rule.

15. **Conversations about food allergy risk with restaurant staff when eating out: a customer perspective** (Barnett, Vasileiou, Lucas; Food Control)
    - Link: https://researchportal.bath.ac.uk/en/publications/conversations-about-food-allergy-risk-with-restaurant-staff-when-/
    - Year: 2020
    - What it does: An interview study of 39 adults with severe food allergies. They avoid allergy conversations with staff for fear of seeming "fussy" or "a nuisance", and trust depends on staff knowledge and care.
    - How it differs: There is no AI. It is relevant background on whether a fixed question sent back to the guest is socially acceptable.

Also seen but less close:

- US patent 12340358: AI order-taking in which human agents correct the cart or transcript through the POS and can type a clarifying question that the AI then speaks.
- Thawinwisan et al. 2026, JMIR Med Inform e94614: a history-taking chatbot compared with a rule-based symptom checker on 66 simulated patients. No allergy content.
- Lu et al. 2026, arXiv 2607.22954: an LLM finds inconsistencies, including allergy ones, in MIMIC discharge summaries. It detects them but does not resolve them.
- MemRiskBench, arXiv 2609.14976: lists "constraint decay" and "conflicting updates" as risks, with no allergy specifics.
- SafePlate (dev.to): an in-browser allergy checker with a deterministic keyword layer.
- Guardian Engine (kaimeilabs): a deterministic recipe checker that never auto-fixes allergen findings.
- CHARM-A (EAHP 2025): patient self-reported allergy histories versus pharmacy technicians' records; many discrepancies, most of low clinical relevance.

## Verdict

I found nothing that already does this experiment. No study, repo, dataset or product page I found has code apply a fixed rule that, when a staff member says an allergen is fine, sends a fixed question to the guest and lifts the allergy only on the guest's answer. None compares that rule with "anyone can cancel" and "only the guest can cancel" on the same fixed AI readings of varied yes/no replies, and none measures unsafe sends, needless holds and waiting time.

The pieces exist separately, and some are close:

- **Reading the replies:** the closest prior work is Liu et al. 2025 (arXiv 2511.12439). It has an LLM read synthetic yes/no replies in set styles (brief, hedged, uncertain, off-topic), balances yes and no, holds on uncertainty, and reports a leading-"No" polarity misreading. Anyone reviewing our reply-reading design will see the overlap. It has no allergy, no third-party cancellation, no comparison of authority rules, and no scope answers.
- **Third parties versus an allergy:** CURATe (arXiv 2410.21159) is close in spirit, since third parties' wishes conflict with a user's stated severe allergy. But the LLM decides, and asking the user is ruled out by its instructions.
- **"AI reads, code decides":** this pattern already exists (Jagga et al. 2026; Liu et al. 2025), so it is not new on its own.
- **Restaurant allergy tests on simulated orders:** these exist commercially (Lilac Labs with Hamming; Google Food AI eval), but they publish no comparison of rules.
- **Hospital allergy reconciliation:** the work found keeps a clinician or an objective test as the decider. I found no LLM study that compares who may remove an allergy or that gates removal on the patient's answer.

Our new elements appear to be:

- The "staff says fine → code asks the guest" gate.
- A head-to-head of three authority rules on the same fixed readings.
- Scope answers ("only my sister, not here") alongside polarity traps in an allergy setting.
- Measuring waiting time as a cost of asking.
- Comparing three ways of reading the same replies.

Limits of this search:

- Some PMC pages were blocked by a captcha, and a few PDFs had no extractable text.
- GitHub was searched only through web search.
- Industry product logic, such as how a POS or voice agent handles a staff "it's fine", is rarely published, so an unpublished commercial version cannot be ruled out.
