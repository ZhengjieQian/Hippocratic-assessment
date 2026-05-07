import os
import json
import re
import openai

"""
Before submitting the assignment, describe here in a few sentences what you would have built next if you spent 2 more hours on this project:

  1. STREAMING OUTPUT: Switch call_model() to stream=True and print tokens as they arrive
     using a generator — the story unfolds word-by-word like a real narration, masking the
     15-30s generation latency and creating the feeling of a story being spoken aloud.

  2. MULTI-TURN FEEDBACK LOOP: After displaying the final story, prompt the parent with
     "Would you like to change anything? (e.g., 'make it funnier', 'add a dragon')" and run
     one targeted refinement pass — turning a single-shot pipeline into a genuinely
     collaborative, interactive bedtime tool with true human-in-the-loop design.
"""

# ─────────────────────────────────────────────────────────────────────────────
# CULTURAL TEMPLATES
# Each culture provides: reference tales, a 4-stage story arc, typical elements,
# and a language/style guide. These are injected into every agent prompt so the
# story feels authentically rooted in its cultural tradition.
# ─────────────────────────────────────────────────────────────────────────────

CULTURAL_TEMPLATES = {
    "CN": {
        "name": "Chinese (中国)",
        "reference_tales": ["Journey to the West", "Hua Mulan"],
        "story_arc": {
            "起 (Qi – Beginning)": (
                "Introduce a child protagonist in a harmonious setting — a bamboo grove, "
                "a moonlit village, a family courtyard. A small disruption appears: a lost "
                "creature, a mysterious glowing object, or an elder's quiet request."
            ),
            "承 (Cheng – Development)": (
                "The child explores or helps, encountering one or two wondrous creatures or "
                "spirits. Obstacles arise from impatience or pride — qualities the child must "
                "learn to temper."
            ),
            "转 (Zhuan – Turn)": (
                "An unexpected reversal: the creature the child helped reveals a hidden gift, "
                "or a simple act of kindness ripples in a surprising and magical way."
            ),
            "合 (He – Resolution)": (
                "Harmony is restored. The child gains wisdom rather than treasure. "
                "End with one short, proverb-like sentence of moral closure."
            ),
        },
        "typical_elements": {
            "settings": ["moonlit rice paddy", "misty mountain path", "jade pavilion", "ancient plum tree", "bamboo grove"],
            "character_types": ["wise grandparent", "mischievous fox spirit", "jade rabbit", "small dragon", "celestial weaver"],
            "moral_themes": ["filial piety", "patience rewarded", "harmony with nature", "humility over pride", "kindness to animals"],
        },
        "language_style": (
            "Use gentle, lyrical prose with nature imagery — moonlight, mist, blossom. "
            "Sentences are measured, not too long. Weave in one proverb-like phrase. "
            "Tone is warm, quiet, and slightly formal — like a grandparent telling a story."
        ),
    },
    "WE": {
        "name": "Western (西方)",
        "reference_tales": ["Cinderella", "Jack and the Beanstalk"],
        "story_arc": {
            "Ordinary World": (
                "A child lives in a comfortable but imperfect situation — overlooked, "
                "timid, or wishing for something more."
            ),
            "Call to Adventure": (
                "A magical event — an enchanted object, a talking animal, a fairy "
                "godmother — invites the child toward a quest."
            ),
            "Trials": (
                "The child faces 2 escalating challenges that require cleverness or "
                "inner courage rather than brute strength."
            ),
            "Resolution": (
                "The child succeeds through their own virtue. They return home changed — "
                "braver, kinder, or wiser. Emotional closure, not just plot closure."
            ),
        },
        "typical_elements": {
            "settings": ["enchanted forest", "village marketplace", "crumbling castle", "cozy cottage", "silver cloud kingdom"],
            "character_types": ["fairy godmother", "talking animal companion", "kind-hearted witch", "bumbling giant", "lost prince or princess"],
            "moral_themes": ["courage over fear", "kindness rewarded", "inner beauty matters", "cleverness beats brute force", "home is where the heart is"],
        },
        "language_style": (
            "Warm, rhythmic storytelling voice. Adapt classic fairy-tale openings freshly "
            "('Long ago in a kingdom not unlike our own...'). Short declarative sentences "
            "for action; longer flowing ones for wonder. End with emotional warmth."
        ),
    },
    "JP": {
        "name": "Japanese (日本)",
        "reference_tales": ["Momotaro (Peach Boy)", "Tanabata"],
        "story_arc": {
            "間 (Ma – Stillness)": (
                "Open with a quiet, sensory scene. A child notices something others "
                "overlook — a tiny creature, a glowing stone, a gap in an old shrine gate."
            ),
            "縁 (En – Connection)": (
                "An unlikely bond forms slowly and carefully. The creature has a need; "
                "the child chooses to help despite personal risk."
            ),
            "頑張り (Gambari – Perseverance)": (
                "The child faces inner doubt and one external obstacle. They persist "
                "through gentle determination rather than power."
            ),
            "物の哀れ (Mono no Aware – Bittersweet Resolution)": (
                "The goal is achieved, but something is gently released — the creature "
                "must leave, seasons change. The child holds both joy and quiet sadness."
            ),
        },
        "typical_elements": {
            "settings": ["shrine steps at dusk", "cherry blossom lane", "quiet fishing village", "bamboo forest in rain", "paper lanterns on a river"],
            "character_types": ["tanuki (raccoon dog)", "kitsune (fox)", "tengu (mountain spirit)", "kodama (tree spirit)", "gentle sea turtle"],
            "moral_themes": ["respect for nature", "perseverance", "transience of beauty", "gratitude", "bonds across difference"],
        },
        "language_style": (
            "Sparse, contemplative prose. Short sentences with white space in meaning. "
            "Rich sensory detail — the sound of rain, the smell of cedar, cool stone underfoot. "
            "Avoid over-explanation. One or two Japanese words may appear with gentle context. "
            "Tone: quiet, wonder-filled, and slightly melancholic."
        ),
    },
    "AR": {
        "name": "Arabian (阿拉伯)",
        "reference_tales": ["One Thousand and One Nights", "Ali Baba"],
        "story_arc": {
            "Frame / Blessing": (
                "Open with warmth and wonder ('In a city of starlight and spices...'). "
                "Introduce a clever, warm-hearted child from a humble but loving household."
            ),
            "The Quest or Riddle": (
                "A djinn, wise merchant, or elder poses a riddle or task. "
                "The child must show wisdom, generosity, or honesty — not just cleverness."
            ),
            "Temptation": (
                "An easy but dishonest shortcut is offered. The child refuses. "
                "This refusal is the story's moral pivot."
            ),
            "Barakah (Blessing)": (
                "Because of their virtue, the child receives unexpected abundance. "
                "They share it generously. The story ends with communal warmth."
            ),
        },
        "typical_elements": {
            "settings": ["desert oasis under stars", "bustling souk", "tiled courtyard with fountain", "hidden cave behind a waterfall", "starlit rooftop"],
            "character_types": ["friendly djinn", "wise merchant", "mischievous jinn child", "generous baker", "old storyteller grandmother"],
            "moral_themes": ["generosity over greed", "honesty rewarded", "cleverness with heart", "community and sharing", "trust in goodness"],
        },
        "language_style": (
            "Lush, vivid, sensory-rich prose — 'the air smelled of cardamom and night-blooming jasmine'. "
            "Use the rhythm of oral storytelling: repetition for emphasis, lists of three. "
            "Every character has warmth and humanity. Light formal register, "
            "as if an elder narrates by firelight."
        ),
    },
    "AF": {
        "name": "African (非洲)",
        "reference_tales": ["Anansi the Spider (West African)", "The Hare and the Lion (Swahili)"],
        "story_arc": {
            "Community": (
                "Open in a vibrant village or savanna scene. The child is part of a "
                "community — their problem or gift is woven into the group's life."
            ),
            "Trickster Encounter": (
                "A clever animal — Anansi the spider, a hare, a chameleon — appears. "
                "It either needs help or offers a lesson disguised as mischief."
            ),
            "Ubuntu Test": (
                "The child faces a choice: act alone for personal gain, or act together "
                "for shared meaning. Ubuntu — 'I am because we are' — is the deciding force."
            ),
            "Celebration": (
                "Resolution is communal. The village celebrates, animals join in, "
                "and a proverb closes the story with collective joy."
            ),
        },
        "typical_elements": {
            "settings": ["acacia tree at sunset", "river crossing at dawn", "village fire circle", "savanna under stars", "baobab tree hollow"],
            "character_types": ["Anansi the spider", "wise tortoise", "boastful lion", "clever hare", "village elder grandmother"],
            "moral_themes": ["ubuntu (I am because we are)", "trickster wisdom", "sharing over hoarding", "elders' wisdom", "joy in community"],
        },
        "language_style": (
            "Rhythmic, musical prose — short punchy sentences alternate with longer flowing ones. "
            "Use call-and-response echoes. Vivid animal sounds and movement. "
            "Warmth, humor, and energy throughout. End with a proverb-style phrase. "
            "Tone: joyful, communal, and alive."
        ),
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# LAYER 0: Core model call (preserved from skeleton — model must stay gpt-3.5-turbo)
# ─────────────────────────────────────────────────────────────────────────────

def call_model(prompt: str, max_tokens=3000, temperature=0.1) -> str:
    openai.api_key = os.getenv("OPENAI_API_KEY")  # please use your own openai api key here.
    resp = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        stream=False,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return resp.choices[0].message["content"]  # type: ignore


# ─────────────────────────────────────────────────────────────────────────────
# LAYER 1: UserInput Agent
# Collects: culture, age range, bedtime state, protagonist, theme
# ─────────────────────────────────────────────────────────────────────────────

def select_culture() -> str:
    options = [
        ("CN", "Chinese      (中国)  — Journey to the West, Hua Mulan"),
        ("WE", "Western      (西方)  — Cinderella, Jack and the Beanstalk"),
        ("JP", "Japanese     (日本)  — Momotaro, Tanabata"),
        ("AR", "Arabian    (阿拉伯)  — One Thousand and One Nights"),
        ("AF", "African      (非洲)  — Anansi the Spider, The Hare and the Lion"),
    ]
    print("\nChoose a cultural setting:")
    for i, (_, label) in enumerate(options, 1):
        print(f"  {i}. {label}")
    while True:
        choice = input("Enter number (1-5): ").strip()
        if choice in {"1", "2", "3", "4", "5"}:
            return options[int(choice) - 1][0]
        print("  Please enter a number between 1 and 5.")


def select_age_range() -> str:
    print("\nHow old is the child?")
    print("  1. 5–7 years old   (simple words, shorter story, clear moral)")
    print("  2. 8–10 years old  (richer language, longer story, subtle moral)")
    while True:
        choice = input("Enter number (1-2): ").strip()
        if choice == "1":
            return "5-7"
        if choice == "2":
            return "8-10"
        print("  Please enter 1 or 2.")


def select_bedtime_state() -> str:
    print("\nWhat's the child's energy level right now?")
    print("  1. Energetic — wants an exciting adventure")
    print("  2. Sleepy    — needs something calm and soothing")
    while True:
        choice = input("Enter number (1-2): ").strip()
        if choice == "1":
            return "energetic"
        if choice == "2":
            return "sleepy"
        print("  Please enter 1 or 2.")


def collect_protagonist():
    print()
    name = ""
    while not name:
        name = input("Protagonist's name: ").strip()
        if not name:
            print("  Name cannot be empty.")
    print("Protagonist's gender:")
    print("  1. Boy   2. Girl   3. Leave unspecified")
    while True:
        g = input("Enter number (1-3): ").strip()
        if g == "1":
            return name, "boy"
        if g == "2":
            return name, "girl"
        if g == "3":
            return name, "child"
        print("  Please enter 1, 2, or 3.")


def collect_theme() -> str:
    themes = ["friendship", "courage", "curiosity", "kindness", "family", "custom"]
    print("\nChoose a theme:")
    for i, t in enumerate(themes, 1):
        print(f"  {i}. {t if t != 'custom' else 'custom (type your own)'}")
    while True:
        choice = input("Enter number (1-6): ").strip()
        if choice in {str(i) for i in range(1, 7)}:
            selected = themes[int(choice) - 1]
            if selected == "custom":
                custom = input("  Your theme: ").strip()
                return custom if custom else "adventure"
            return selected
        print("  Please enter a number between 1 and 6.")


def confirm_request(culture_name, age_range, bedtime_state, name, gender, theme) -> bool:
    print("\n" + "─" * 48)
    print("  Story settings")
    print("─" * 48)
    print(f"  Culture:       {culture_name}")
    print(f"  Age range:     {age_range} years old")
    print(f"  Child's mood:  {bedtime_state}")
    print(f"  Protagonist:   {name} ({gender})")
    print(f"  Theme:         {theme}")
    print("─" * 48)
    while True:
        answer = input("Proceed with these settings? (y/n): ").strip().lower()
        if answer == "y":
            return True
        if answer == "n":
            return False
        print("  Please enter y or n.")


def collect_user_input() -> dict:
    while True:
        culture_code = select_culture()
        age_range = select_age_range()
        bedtime_state = select_bedtime_state()
        name, gender = collect_protagonist()
        theme = collect_theme()
        template = CULTURAL_TEMPLATES[culture_code]
        if confirm_request(template["name"], age_range, bedtime_state, name, gender, theme):
            return {
                "culture_code": culture_code,
                "culture_name": template["name"],
                "age_range": age_range,
                "bedtime_state": bedtime_state,
                "protagonist_name": name,
                "protagonist_gender": gender,
                "theme": theme,
            }
        print("\nLet's start over.\n")


# ─────────────────────────────────────────────────────────────────────────────
# LAYER 2: Outline Agent  (human-in-the-loop)
# Generates a 5-point story outline, shows it to the user, and allows them to
# approve, request edits, or regenerate before any full story is written.
# ─────────────────────────────────────────────────────────────────────────────

def build_outline_prompt(template: dict, request: dict) -> str:
    arc_stages = "\n".join(
        f"  - {stage}: {desc[:90]}..."
        for stage, desc in template["story_arc"].items()
    )
    age_note = (
        "Use very simple concepts and clear cause-and-effect."
        if request["age_range"] == "5-7"
        else "You may include a light plot twist or a subtler moral."
    )
    pace_note = (
        "The story should feel adventurous and energetic."
        if request["bedtime_state"] == "energetic"
        else "The story should feel calm, soothing, and slow-paced."
    )
    return f"""You are a children's story planner. Create a 5-point outline for a bedtime story.

CULTURAL FRAMEWORK: {template["name"]}
Inspired by: {", ".join(template["reference_tales"])}
Story arc stages:
{arc_stages}

STORY PARAMETERS:
  Protagonist: {request["protagonist_name"]} ({request["protagonist_gender"]})
  Theme: {request["theme"]}
  Age range: {request["age_range"]} years — {age_note}
  Pacing: {pace_note}

Output EXACTLY 5 numbered bullet points, one sentence each:
1. Setup: [introduce the world and {request["protagonist_name"]}]
2. Spark: [the event that starts the adventure]
3. Challenge: [the main obstacle or quest]
4. Turn: [the key moment of growth or reversal]
5. Resolution: [how it ends peacefully]

Output only the 5 bullet points. No title. No extra text."""


def generate_outline(template: dict, request: dict) -> str:
    return call_model(build_outline_prompt(template, request), max_tokens=300, temperature=0.7)


def refine_outline_with_feedback(original: str, feedback: str, template: dict, request: dict) -> str:
    prompt = f"""You are a children's story planner revising a 5-point outline based on feedback.

ORIGINAL OUTLINE:
{original}

USER FEEDBACK: {feedback}

CULTURAL FRAMEWORK: {template["name"]}
Protagonist: {request["protagonist_name"]} ({request["protagonist_gender"]}), theme: {request["theme"]}

Output the revised 5 bullet points in the same format (1. Setup / 2. Spark / 3. Challenge / 4. Turn / 5. Resolution).
One sentence per point. No extra text."""
    return call_model(prompt, max_tokens=300, temperature=0.7)


def get_approved_outline(template: dict, request: dict) -> str:
    """Generate outline, show to user, loop until approved."""
    outline = generate_outline(template, request)
    while True:
        print("\n" + "═" * 48)
        print("  STORY OUTLINE  (your preview before the full story)")
        print("═" * 48)
        print(outline)
        print("═" * 48)
        print("\n  y — looks good, write the full story")
        print("  e — I want to suggest changes")
        print("  r — generate a different outline")
        while True:
            choice = input("Your choice (y/e/r): ").strip().lower()
            if choice in {"y", "e", "r"}:
                break
            print("  Please enter y, e, or r.")
        if choice == "y":
            return outline
        if choice == "r":
            print("\nGenerating a new outline...\n")
            outline = generate_outline(template, request)
        else:
            feedback = input("What would you like to change? ").strip()
            if feedback:
                print("\nRevising outline...\n")
                outline = refine_outline_with_feedback(outline, feedback, template, request)


# ─────────────────────────────────────────────────────────────────────────────
# LAYER 3: Storyteller Agent
# Expands the approved outline into a full story, injecting the cultural
# template, age guidance, pacing, and mandatory craft requirements.
# ─────────────────────────────────────────────────────────────────────────────

def build_storyteller_prompt(template: dict, request: dict, outline: str) -> str:
    arc_text = "\n".join(
        f"  {stage}:\n    {desc}"
        for stage, desc in template["story_arc"].items()
    )
    elements = template["typical_elements"]

    if request["age_range"] == "5-7":
        age_guidance = (
            "Vocabulary: words a 6-year-old knows. Sentences: short and direct. "
            "Target length: 400–450 words. Moral: state clearly near the end."
        )
    else:
        age_guidance = (
            "Vocabulary: rich but accessible to a 9-year-old. Sentences: varied in length. "
            "Target length: 500–600 words. Moral: woven subtly into the resolution."
        )

    if request["bedtime_state"] == "sleepy":
        pacing = (
            "PACING: Slow and soothing. Use long, rhythmic sentences in descriptive passages. "
            "Minimize sudden surprises. End with the protagonist settling into warmth or rest."
        )
    else:
        pacing = (
            "PACING: Energetic and engaging. Use short punchy lines during action. "
            "Include at least one exciting moment. End on satisfying accomplishment."
        )

    return f"""You are a master children's bedtime story author. Write an original story for children aged {request["age_range"]}.

RULES:
- {age_guidance}
- No violence, no frightening content, no romantic themes.
- Include AT LEAST ONE line of dialogue per major character interaction.
- Include AT LEAST ONE vivid sensory detail (sound, smell, or texture) per scene.
- End on a peaceful, sleep-friendly note.
- Output format exactly:
    TITLE: <story title>
    ---
    <story text>
- You are INSPIRED by the reference tales — create entirely original characters and plot.

CULTURAL FRAMEWORK: {template["name"]}
Inspired by: {", ".join(template["reference_tales"])}

STORY ARC:
{arc_text}

CULTURAL ELEMENTS (use what fits naturally — do not force all):
  Settings: {", ".join(elements["settings"])}
  Character types: {", ".join(elements["character_types"])}
  Moral themes: {", ".join(elements["moral_themes"])}

LANGUAGE & STYLE:
{template["language_style"]}

{pacing}

APPROVED OUTLINE (expand each point into a full scene):
{outline}

Protagonist: {request["protagonist_name"]} ({request["protagonist_gender"]})
Theme: {request["theme"]}

Write the full story now. Begin with the title."""


def generate_story(template: dict, request: dict, outline: str) -> str:
    prompt = build_storyteller_prompt(template, request, outline)
    return call_model(prompt, max_tokens=900, temperature=0.8)


# ─────────────────────────────────────────────────────────────────────────────
# LAYER 4: Judge Agent
# Uses chain-of-thought (Step 1: analyze weakest dimension; Step 2: score JSON)
# to improve scoring reliability on gpt-3.5-turbo.
# ─────────────────────────────────────────────────────────────────────────────

def build_judge_prompt(story_text: str, culture_name: str, age_range: str) -> str:
    return f"""You are a rigorous children's literature quality judge evaluating a bedtime story for ages {age_range}.

STEP 1 — Before scoring, write 2 sentences identifying the story's weakest dimension and why.

STEP 2 — Score on exactly these 5 dimensions (integer 1–10 each):
  1. age_appropriateness   — Vocabulary, themes, and length suitable for {age_range}-year-olds?
  2. story_arc             — Clear beginning, development, turn, and satisfying resolution?
  3. cultural_authenticity — Authentic {culture_name} settings, characters, language style? No stereotypes?
  4. engagement            — Imaginative, sensory-rich; would a child want to hear it again?
  5. moral_lesson          — Positive moral woven naturally (not preachy)?

STORY:
---
{story_text}
---

Output ONLY this JSON (no markdown fences, no extra text):
{{
  "analysis": "<your 2-sentence Step 1 analysis>",
  "scores": {{
    "age_appropriateness": <int>,
    "story_arc": <int>,
    "cultural_authenticity": <int>,
    "engagement": <int>,
    "moral_lesson": <int>
  }},
  "justifications": {{
    "age_appropriateness": "<one sentence>",
    "story_arc": "<one sentence>",
    "cultural_authenticity": "<one sentence>",
    "engagement": "<one sentence>",
    "moral_lesson": "<one sentence>"
  }},
  "improvement_suggestions": {{
    "age_appropriateness": "<specific suggestion or No improvement needed>",
    "story_arc": "<specific suggestion or No improvement needed>",
    "cultural_authenticity": "<specific suggestion or No improvement needed>",
    "engagement": "<specific suggestion or No improvement needed>",
    "moral_lesson": "<specific suggestion or No improvement needed>"
  }},
  "average_score": <float — mean of the 5 scores>,
  "overall_feedback": "<2–3 sentences: key strengths and single most important improvement>"
}}"""


def parse_judge_response(text: str) -> dict:
    cleaned = text.strip()
    # Strip markdown code fences if the model wrapped the JSON
    if cleaned.startswith("```"):
        for part in cleaned.split("```"):
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{"):
                cleaned = part
                break
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        avg_match = re.search(r'"average_score"\s*:\s*([0-9.]+)', text)
        avg = float(avg_match.group(1)) if avg_match else 5.0
        dims = ["age_appropriateness", "story_arc", "cultural_authenticity", "engagement", "moral_lesson"]
        return {
            "analysis": "Judge response could not be fully parsed.",
            "scores": {d: 5 for d in dims},
            "justifications": {d: "N/A" for d in dims},
            "improvement_suggestions": {d: "Improve overall quality." for d in dims},
            "average_score": avg,
            "overall_feedback": "Parse error — story queued for refinement as a precaution.",
        }


def evaluate_story(story_text: str, culture_name: str, age_range: str) -> dict:
    prompt = build_judge_prompt(story_text, culture_name, age_range)
    response = call_model(prompt, max_tokens=700, temperature=0.1)
    return parse_judge_response(response)


# ─────────────────────────────────────────────────────────────────────────────
# LAYER 5: Refinement Agent
# Receives the judge's dimension-level scores and suggestions and rewrites
# only the aspects that fell below threshold, preserving what worked.
# ─────────────────────────────────────────────────────────────────────────────

def build_refinement_prompt(original_story: str, judge_result: dict, template: dict, request: dict) -> str:
    scores = judge_result.get("scores", {})
    suggestions = judge_result.get("improvement_suggestions", {})
    justifications = judge_result.get("justifications", {})
    word_range = "400–450" if request["age_range"] == "5-7" else "500–600"

    dim_lines = []
    for key in ["age_appropriateness", "story_arc", "cultural_authenticity", "engagement", "moral_lesson"]:
        s = scores.get(key, "?")
        j = justifications.get(key, "")
        sg = suggestions.get(key, "")
        dim_lines.append(f"  {key.replace('_', ' ').title()}: {s}/10 — {j}\n    → Fix: {sg}")

    return f"""You are a master children's bedtime story author revising your own work based on editorial feedback.

ORIGINAL STORY:
---
{original_story}
---

EDITORIAL SCORES AND SUGGESTIONS:
{"".join(chr(10) + l for l in dim_lines)}

Overall: {judge_result.get("overall_feedback", "")}

REVISION RULES:
1. Address every suggestion where the score was below 8.
2. Keep what scored 8 or above — do not change those aspects.
3. Preserve: protagonist ({request["protagonist_name"]}), cultural framework ({template["name"]}), core plot.
4. Strengthen as needed: dialogue, sensory details, cultural language, moral clarity.
5. Output format:
    TITLE: <story title>
    ---
    <revised story text>
6. Target length: {word_range} words.

Write the revised story now."""


def refine_story(story_text: str, judge_result: dict, template: dict, request: dict) -> str:
    prompt = build_refinement_prompt(story_text, judge_result, template, request)
    return call_model(prompt, max_tokens=900, temperature=0.7)


# ─────────────────────────────────────────────────────────────────────────────
# LAYER 6: Pipeline Orchestrator
# Storyteller → Judge → (Refinement → Judge) × max_rounds
# ─────────────────────────────────────────────────────────────────────────────

def run_story_pipeline(template: dict, request: dict, outline: str, max_refinement_rounds: int = 2):
    print("\nWriting story draft...", end=" ", flush=True)
    story = generate_story(template, request, outline)
    print("done.")

    print("Judge evaluating (round 1)...", end=" ", flush=True)
    judge = evaluate_story(story, request["culture_name"], request["age_range"])
    print(f"score {judge['average_score']:.1f}/10")

    rounds = 0
    while judge["average_score"] < 7.0 and rounds < max_refinement_rounds:
        rounds += 1
        print(f"Refining story (round {rounds})...", end=" ", flush=True)
        story = refine_story(story, judge, template, request)
        print("done.")
        print(f"Judge re-evaluating...", end=" ", flush=True)
        judge = evaluate_story(story, request["culture_name"], request["age_range"])
        print(f"score {judge['average_score']:.1f}/10")

    return story, judge, rounds


# ─────────────────────────────────────────────────────────────────────────────
# LAYER 7: Output Formatting
# ─────────────────────────────────────────────────────────────────────────────

def _score_bar(score: int) -> str:
    if score <= 4:
        return "░░░░░"
    if score <= 6:
        return "███░░"
    if score <= 8:
        return "████░"
    return "█████"


def format_quality_report(judge_result: dict, rounds_used: int) -> str:
    scores = judge_result.get("scores", {})
    labels = {
        "age_appropriateness":  "Age Appropriateness ",
        "story_arc":            "Story Arc           ",
        "cultural_authenticity":"Cultural Authenticity",
        "engagement":           "Engagement          ",
        "moral_lesson":         "Moral Lesson        ",
    }
    avg = judge_result.get("average_score", 0.0)
    passed = avg >= 7.0

    lines = [
        "",
        "─" * 48,
        "  QUALITY REPORT  (LLM Judge)",
        "─" * 48,
    ]
    for key, label in labels.items():
        s = scores.get(key, 0)
        lines.append(f"  {label}  {_score_bar(s)}  {s}/10")
    lines += [
        "─" * 48,
        f"  Overall score:  {avg:.1f}/10  ({'passed' if passed else 'below threshold — refined'})",
        f"  Refinement rounds used: {rounds_used}",
    ]
    analysis = judge_result.get("analysis", "")
    overall = judge_result.get("overall_feedback", "")
    if analysis:
        lines.append(f"\n  Judge analysis:\n  {analysis}")
    if overall:
        lines.append(f"\n  Summary:\n  {overall}")
    lines.append("─" * 48)
    return "\n".join(lines)


def display_final_output(story: str, quality_report: str) -> None:
    print("\n" + "═" * 48)
    print("  YOUR BEDTIME STORY")
    print("═" * 48 + "\n")
    print(story)
    print(quality_report)


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

example_requests = "A story about a girl named Alice and her best friend Bob, who happens to be a cat."


def main():
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable is not set.")
        print("  Mac/Linux:   export OPENAI_API_KEY='your-key-here'")
        print("  PowerShell:  $env:OPENAI_API_KEY='your-key-here'")
        return

    print("\n" + "═" * 48)
    print("  BEDTIME STORY GENERATOR")
    print("  Multi-agent AI storytelling system")
    print("═" * 48)

    while True:
        request = collect_user_input()
        template = CULTURAL_TEMPLATES[request["culture_code"]]

        # Human-in-the-loop: review and approve the outline before full generation
        print("\nGenerating story outline...")
        outline = get_approved_outline(template, request)

        # Full pipeline: Storyteller → Judge → Refinement loop
        story, judge_result, rounds = run_story_pipeline(template, request, outline)

        quality_report = format_quality_report(judge_result, rounds)
        display_final_output(story, quality_report)

        print()
        again = input("Generate another story? (y/n): ").strip().lower()
        if again != "y":
            print("\nGoodnight! Sweet dreams.\n")
            break


if __name__ == "__main__":
    main()
