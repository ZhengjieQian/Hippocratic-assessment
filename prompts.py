"""
All prompt-building functions in one place.
Separating prompt text from agent logic makes prompts independently
testable, editable, and version-controllable without touching pipeline code.
"""


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
  Age range: {request["age_range"]} years -- {age_note}
  Pacing: {pace_note}

Output EXACTLY 5 numbered bullet points, one sentence each:
1. Setup: [introduce the world and {request["protagonist_name"]}]
2. Spark: [the event that starts the adventure]
3. Challenge: [the main obstacle or quest]
4. Turn: [the key moment of growth or reversal]
5. Resolution: [how it ends peacefully]

Output only the 5 bullet points. No title. No extra text."""


def build_outline_refinement_prompt(original: str, feedback: str, template: dict, request: dict) -> str:
    return f"""You are a children's story planner revising a 5-point outline based on feedback.

ORIGINAL OUTLINE:
{original}

USER FEEDBACK: {feedback}

CULTURAL FRAMEWORK: {template["name"]}
Protagonist: {request["protagonist_name"]} ({request["protagonist_gender"]}), theme: {request["theme"]}

Output the revised 5 bullet points in the same format (1. Setup / 2. Spark / 3. Challenge / 4. Turn / 5. Resolution).
One sentence per point. No extra text."""


def build_storyteller_prompt(template: dict, request: dict, outline: str) -> str:
    arc_text = "\n".join(
        f"  {stage}:\n    {desc}"
        for stage, desc in template["story_arc"].items()
    )
    elements = template["typical_elements"]

    if request["age_range"] == "5-7":
        age_guidance = (
            "Vocabulary: words a 6-year-old knows. Sentences: short and direct. "
            "Target length: 400-450 words. Moral: state clearly near the end."
        )
    else:
        age_guidance = (
            "Vocabulary: rich but accessible to a 9-year-old. Sentences: varied in length. "
            "Target length: 500-600 words. Moral: woven subtly into the resolution."
        )

    pacing = (
        "PACING: Slow and soothing. Use long, rhythmic sentences in descriptive passages. "
        "Minimize sudden surprises. End with the protagonist settling into warmth or rest."
        if request["bedtime_state"] == "sleepy"
        else
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
- You are INSPIRED by the reference tales -- create entirely original characters and plot.

CULTURAL FRAMEWORK: {template["name"]}
Inspired by: {", ".join(template["reference_tales"])}

STORY ARC:
{arc_text}

CULTURAL ELEMENTS (use what fits naturally -- do not force all):
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


def build_judge_prompt(story_text: str, culture_name: str, age_range: str) -> str:
    return f"""You are a rigorous children's literature quality judge evaluating a bedtime story for ages {age_range}.

STEP 1 -- Before scoring, write 2 sentences identifying the story's weakest dimension and why.

STEP 2 -- Score on exactly these 5 dimensions (integer 1-10 each):
  1. age_appropriateness   -- Vocabulary, themes, and length suitable for {age_range}-year-olds?
  2. story_arc             -- Clear beginning, development, turn, and satisfying resolution?
  3. cultural_authenticity -- Authentic {culture_name} settings, characters, language style? No stereotypes?
  4. engagement            -- Imaginative, sensory-rich; would a child want to hear it again?
  5. moral_lesson          -- Positive moral woven naturally (not preachy)?

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
  "average_score": <float -- mean of the 5 scores>,
  "overall_feedback": "<2-3 sentences: key strengths and single most important improvement>"
}}"""


def build_refinement_prompt(original_story: str, judge_result: dict, template: dict, request: dict) -> str:
    scores = judge_result.get("scores", {})
    suggestions = judge_result.get("improvement_suggestions", {})
    justifications = judge_result.get("justifications", {})
    word_range = "400-450" if request["age_range"] == "5-7" else "500-600"

    dim_lines = []
    for key in ["age_appropriateness", "story_arc", "cultural_authenticity", "engagement", "moral_lesson"]:
        s = scores.get(key, "?")
        j = justifications.get(key, "")
        sg = suggestions.get(key, "")
        dim_lines.append(f"  {key.replace('_', ' ').title()}: {s}/10 -- {j}\n    -> Fix: {sg}")

    return f"""You are a master children's bedtime story author revising your own work based on editorial feedback.

ORIGINAL STORY:
---
{original_story}
---

EDITORIAL SCORES AND SUGGESTIONS:
{"".join(chr(10) + line for line in dim_lines)}

Overall: {judge_result.get("overall_feedback", "")}

REVISION RULES:
1. Address every suggestion where the score was below 8.
2. Keep what scored 8 or above -- do not change those aspects.
3. Preserve: protagonist ({request["protagonist_name"]}), cultural framework ({template["name"]}), core plot.
4. Strengthen as needed: dialogue, sensory details, cultural language, moral clarity.
5. Output format:
    TITLE: <story title>
    ---
    <revised story text>
6. Target length: {word_range} words.

Write the revised story now."""
