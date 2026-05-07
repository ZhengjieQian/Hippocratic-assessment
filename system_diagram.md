# System Block Diagram

## Mermaid Flowchart

```mermaid
flowchart TD
    USER([👤 User])

    subgraph INPUT["UserInput Agent"]
        I1[Select culture\nCN / WE / JP / AR / AF]
        I2[Select age range\n5-7 or 8-10 yrs]
        I3[Select bedtime state\nenergetic or sleepy]
        I4[Enter protagonist\nname + gender]
        I5[Choose theme]
        I1 --> I2 --> I3 --> I4 --> I5
    end

    subgraph TEMPLATES["Cultural Template DB"]
        T1["Reference tales\n(e.g. Cinderella, Anansi)"]
        T2["4-stage story arc\n(culture-specific structure)"]
        T3["Typical elements\n(settings, characters, themes)"]
        T4["Language & style guide"]
    end

    subgraph OUTLINE["Outline Agent  (human-in-the-loop)"]
        O1["Generate 5-point outline\ntemp=0.7, max_tokens=300"]
        O2{User reviews\noutline}
        O3["Refine outline\nwith user feedback"]
        O1 --> O2
        O2 -->|"e — edit"| O3 --> O1
        O2 -->|"r — regenerate"| O1
    end

    subgraph STORY["Storyteller Agent"]
        S1["Expand outline into full story\ntemp=0.8, max_tokens=900\n• ≥1 dialogue line per interaction\n• ≥1 sensory detail per scene\n• age-calibrated vocabulary\n• pacing adapted to bedtime state"]
    end

    subgraph JUDGE["Judge Agent  (Chain-of-Thought)"]
        J1["Step 1: Identify weakest dimension\n(2-sentence analysis)"]
        J2["Step 2: Score 5 dimensions\ntemp=0.1, max_tokens=700\n• age_appropriateness\n• story_arc\n• cultural_authenticity\n• engagement\n• moral_lesson"]
        J3{average_score\n≥ 7.0?}
        J1 --> J2 --> J3
    end

    subgraph REFINE["Refinement Agent"]
        R1["Revise story using\nJudge feedback\ntemp=0.7, max_tokens=900\nPreserve high-scoring aspects\nFix low-scoring ones"]
    end

    subgraph OUTPUT["Final Output"]
        OUT1["Story text\n(with title)"]
        OUT2["Quality report\n(scores + Judge analysis)"]
    end

    USER --> INPUT
    INPUT --> TEMPLATES
    TEMPLATES --> OUTLINE
    OUTLINE -->|"y — approved"| STORY
    STORY --> JUDGE
    J3 -->|"yes"| OUTPUT
    J3 -->|"no\n(max 2 rounds)"| REFINE
    REFINE --> JUDGE
    OUTPUT --> USER
```

---

## ASCII Block Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                     BEDTIME STORY GENERATOR                      │
└──────────────────────────────────────────────────────────────────┘

  ┌──────────┐
  │   USER   │
  └────┬─────┘
       │ culture / age range / bedtime state / protagonist / theme
       ▼
┌─────────────────────────────────────────────────────────────────┐
│  UserInput Agent                                                │
│  [culture menu] → [age 5-7/8-10] → [sleepy/energetic]          │
│  → [name + gender] → [theme] → [confirm]                       │
└─────────────────────────┬───────────────────────────────────────┘
                          │ story_request dict
                          ▼
               ┌─────────────────────┐
               │  Cultural Template  │  reference tales + story arc
               │        DB           │  + elements + language style
               └──────────┬──────────┘
                          │ template injected into all prompts
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  Outline Agent  (human-in-the-loop)                             │
│                                                                 │
│  generate_outline()  ──►  5-bullet story outline                │
│       ↓                                                         │
│  Show to user  ──►  y: approved  /  e: edit  /  r: regenerate  │
│       ↓ (y)                                                     │
│  approved_outline                                               │
└─────────────────────────┬───────────────────────────────────────┘
                          │ approved 5-point outline
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  Storyteller Agent                                              │
│                                                                 │
│  prompt = cultural_arc + elements + style + age guidance        │
│         + pacing (sleepy/energetic) + outline                   │
│  call_model(temperature=0.8)  ──►  draft_story                  │
└─────────────────────────┬───────────────────────────────────────┘
                          │ draft_story
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  Judge Agent  (Chain-of-Thought scoring)                        │
│                                                                 │
│  Step 1: Identify weakest dimension (2-sentence analysis)       │
│  Step 2: Score 5 dimensions (integer 1-10 each):                │
│     age_appropriateness │ story_arc │ cultural_authenticity     │
│     engagement          │ moral_lesson                          │
│                                                                 │
│  average_score = mean(5 scores)                                 │
│  output: scores + justifications + suggestions + feedback       │
└────────────┬──────────────────────────┬─────────────────────────┘
             │                          │
  avg ≥ 7.0  │                          │  avg < 7.0  (max 2 rounds)
             │                          ▼
             │          ┌───────────────────────────┐
             │          │  Refinement Agent         │
             │          │                           │
             │          │  prompt = original_story  │
             │          │    + per-dimension scores │
             │          │    + specific suggestions │
             │          │  call_model(temp=0.7)     │
             │          └─────────────┬─────────────┘
             │                        │ refined_story
             │                        ▼
             │          ┌─────────────────────────┐
             │          │  Judge Agent (re-score)  │◄── loop ≤2×
             │          └─────────────┬───────────┘
             │                        │
             │              avg ≥ 7.0 │  or max rounds reached
             │◄───────────────────────┘
             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Final Output                                                   │
│  • Story text (TITLE + body)                                    │
│  • Quality report (5-dimension scores + Judge analysis)         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Agent Roles Summary

| Agent | Role | Temperature | Key Prompt Strategy |
|---|---|---|---|
| UserInput | Collect preferences | — | Structured menus + validation |
| Outline | Plan story structure | 0.7 | Cultural arc injection; user editable |
| Storyteller | Write full story | 0.8 | Arc + template + mandatory craft rules |
| Judge | Evaluate quality | 0.1 | Chain-of-thought before scoring; JSON output |
| Refinement | Fix weak dimensions | 0.7 | Preserve strengths; target only low-scoring dims |
