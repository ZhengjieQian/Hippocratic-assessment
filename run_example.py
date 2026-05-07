"""
Non-interactive demo: runs the full pipeline with fixed inputs.
Shows the system working end-to-end without requiring user prompts.

Usage:  python run_example.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import main

DEMO_REQUEST = {
    "culture_code": "JP",
    "culture_name": "Japanese (日本)",
    "age_range": "8-10",
    "bedtime_state": "sleepy",
    "protagonist_name": "Hana",
    "protagonist_gender": "girl",
    "theme": "friendship",
}

DEMO_OUTLINE = """1. Setup: Hana lives near an old shrine and often hears soft rustling in the bamboo at dusk.
2. Spark: One evening she discovers a tiny fox cub with an injured paw, shivering beside the stone lantern.
3. Challenge: Hana must sneak past the shrine keeper each night to bring the cub food, risking discovery.
4. Turn: The keeper catches her — but instead of scolding her, he reveals he too has been leaving rice for the cub, and together they nurse it back to health.
5. Resolution: The cub is released into the forest; Hana watches it disappear into the mist, feeling both the joy of its freedom and the quiet ache of goodbye."""


def run_demo():
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: set OPENAI_API_KEY first.")
        return

    template = main.CULTURAL_TEMPLATES[DEMO_REQUEST["culture_code"]]

    print("\n" + "═" * 52)
    print("  DEMO — BEDTIME STORY GENERATOR")
    print("═" * 52)
    print(f"  Culture:    {DEMO_REQUEST['culture_name']}")
    print(f"  Age range:  {DEMO_REQUEST['age_range']}")
    print(f"  Mood:       {DEMO_REQUEST['bedtime_state']}")
    print(f"  Protagonist:{DEMO_REQUEST['protagonist_name']} ({DEMO_REQUEST['protagonist_gender']})")
    print(f"  Theme:      {DEMO_REQUEST['theme']}")
    print("═" * 52)

    print("\n  [Using pre-approved outline]\n")
    print(DEMO_OUTLINE)

    story, judge_result, rounds = main.run_story_pipeline(
        template, DEMO_REQUEST, DEMO_OUTLINE, max_refinement_rounds=2
    )

    quality_report = main.format_quality_report(judge_result, rounds)
    main.display_final_output(story, quality_report)


if __name__ == "__main__":
    run_demo()
