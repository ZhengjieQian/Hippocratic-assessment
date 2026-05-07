"""
Unit tests for main.py — all LLM calls are mocked.
Tests cover: prompt builders, JSON parsing, score bar, quality report, pipeline orchestration.

Run with:  python -m pytest test_main.py -v
       or: python test_main.py
"""

import sys
import os
import json
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import main


# ─────────────────────────────────────────────────────────────────────────────
# parse_judge_response  — most failure-prone function, most thoroughly tested
# ─────────────────────────────────────────────────────────────────────────────

SAMPLE_JUDGE = {
    "analysis": "The story arc resolution is rushed.",
    "scores": {
        "age_appropriateness": 8,
        "story_arc": 6,
        "cultural_authenticity": 7,
        "engagement": 7,
        "moral_lesson": 8,
    },
    "justifications": {
        "age_appropriateness": "Vocabulary suits 8-10 year olds.",
        "story_arc": "Resolution arrives too quickly.",
        "cultural_authenticity": "Good bamboo imagery.",
        "engagement": "Engaging but lacks sensory depth.",
        "moral_lesson": "Moral is clear and age-appropriate.",
    },
    "improvement_suggestions": {
        "age_appropriateness": "No improvement needed",
        "story_arc": "Expand the resolution by two sentences.",
        "cultural_authenticity": "No improvement needed",
        "engagement": "Add a sound or smell to the forest scene.",
        "moral_lesson": "No improvement needed",
    },
    "average_score": 7.2,
    "overall_feedback": "Solid story; needs a more developed resolution.",
}


class TestParseJudgeResponse(unittest.TestCase):

    def test_valid_json(self):
        result = main.parse_judge_response(json.dumps(SAMPLE_JUDGE))
        self.assertEqual(result["average_score"], 7.2)
        self.assertEqual(result["scores"]["story_arc"], 6)

    def test_json_with_leading_whitespace(self):
        result = main.parse_judge_response("  \n" + json.dumps(SAMPLE_JUDGE))
        self.assertEqual(result["average_score"], 7.2)

    def test_markdown_fenced_with_lang_tag(self):
        text = f"```json\n{json.dumps(SAMPLE_JUDGE)}\n```"
        result = main.parse_judge_response(text)
        self.assertEqual(result["average_score"], 7.2)

    def test_markdown_fenced_without_lang_tag(self):
        text = f"```\n{json.dumps(SAMPLE_JUDGE)}\n```"
        result = main.parse_judge_response(text)
        self.assertEqual(result["average_score"], 7.2)

    def test_malformed_json_extracts_score_via_regex(self):
        text = 'Analysis text... "average_score": 6.4, more text'
        result = main.parse_judge_response(text)
        self.assertEqual(result["average_score"], 6.4)

    def test_completely_malformed_falls_back_to_5(self):
        result = main.parse_judge_response("total garbage response from model")
        self.assertEqual(result["average_score"], 5.0)

    def test_fallback_still_has_required_keys(self):
        result = main.parse_judge_response("garbage")
        for key in ["scores", "justifications", "improvement_suggestions", "overall_feedback"]:
            self.assertIn(key, result)

    def test_fallback_scores_are_all_5(self):
        result = main.parse_judge_response("garbage")
        for v in result["scores"].values():
            self.assertEqual(v, 5)


# ─────────────────────────────────────────────────────────────────────────────
# _score_bar
# ─────────────────────────────────────────────────────────────────────────────

class TestScoreBar(unittest.TestCase):

    def test_very_low(self):
        for s in [1, 2, 3, 4]:
            self.assertEqual(main._score_bar(s), "[....]")

    def test_mid(self):
        for s in [5, 6]:
            self.assertEqual(main._score_bar(s), "[##..]")

    def test_good(self):
        for s in [7, 8]:
            self.assertEqual(main._score_bar(s), "[###.]")

    def test_excellent(self):
        for s in [9, 10]:
            self.assertEqual(main._score_bar(s), "[####]")


# ─────────────────────────────────────────────────────────────────────────────
# build_outline_prompt
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildOutlinePrompt(unittest.TestCase):

    def _make_request(self, age="5-7", state="sleepy"):
        return {
            "culture_code": "CN",
            "culture_name": "Chinese (中国)",
            "age_range": age,
            "bedtime_state": state,
            "protagonist_name": "Mei",
            "protagonist_gender": "girl",
            "theme": "friendship",
        }

    def test_protagonist_name_in_prompt(self):
        p = main.build_outline_prompt(main.CULTURAL_TEMPLATES["CN"], self._make_request())
        self.assertIn("Mei", p)

    def test_culture_name_in_prompt(self):
        p = main.build_outline_prompt(main.CULTURAL_TEMPLATES["CN"], self._make_request())
        self.assertIn("Chinese (中国)", p)

    def test_theme_in_prompt(self):
        p = main.build_outline_prompt(main.CULTURAL_TEMPLATES["CN"], self._make_request())
        self.assertIn("friendship", p)

    def test_age_5_7_uses_simple_language_note(self):
        p = main.build_outline_prompt(main.CULTURAL_TEMPLATES["CN"], self._make_request(age="5-7"))
        self.assertIn("simple", p.lower())

    def test_age_8_10_uses_plot_twist_note(self):
        p = main.build_outline_prompt(main.CULTURAL_TEMPLATES["CN"], self._make_request(age="8-10"))
        self.assertIn("plot twist", p.lower())

    def test_sleepy_pace_note(self):
        p = main.build_outline_prompt(main.CULTURAL_TEMPLATES["CN"], self._make_request(state="sleepy"))
        self.assertIn("calm", p.lower())

    def test_energetic_pace_note(self):
        p = main.build_outline_prompt(main.CULTURAL_TEMPLATES["CN"], self._make_request(state="energetic"))
        self.assertIn("adventurous", p.lower())

    def test_all_five_cultures_build_without_error(self):
        req = self._make_request()
        for code, template in main.CULTURAL_TEMPLATES.items():
            req_c = {**req, "culture_code": code, "culture_name": template["name"]}
            p = main.build_outline_prompt(template, req_c)
            self.assertIsInstance(p, str)
            self.assertGreater(len(p), 100)


# ─────────────────────────────────────────────────────────────────────────────
# build_storyteller_prompt
# ─────────────────────────────────────────────────────────────────────────────

OUTLINE = "1. Setup: Jack lives in a village.\n2. Spark: A door appears.\n3. Challenge: A maze.\n4. Turn: Kindness wins.\n5. Resolution: Home safely."


class TestBuildStorytellerPrompt(unittest.TestCase):

    def _make_request(self, age="8-10", state="energetic"):
        return {
            "culture_code": "WE",
            "culture_name": "Western (西方)",
            "age_range": age,
            "bedtime_state": state,
            "protagonist_name": "Jack",
            "protagonist_gender": "boy",
            "theme": "courage",
        }

    def test_protagonist_in_prompt(self):
        p = main.build_storyteller_prompt(main.CULTURAL_TEMPLATES["WE"], self._make_request(), OUTLINE)
        self.assertIn("Jack", p)

    def test_outline_in_prompt(self):
        p = main.build_storyteller_prompt(main.CULTURAL_TEMPLATES["WE"], self._make_request(), OUTLINE)
        self.assertIn("kindness wins", p.lower())

    def test_culture_name_in_prompt(self):
        p = main.build_storyteller_prompt(main.CULTURAL_TEMPLATES["WE"], self._make_request(), OUTLINE)
        self.assertIn("Western (西方)", p)

    def test_age_8_10_word_count_target(self):
        p = main.build_storyteller_prompt(main.CULTURAL_TEMPLATES["WE"], self._make_request(age="8-10"), OUTLINE)
        self.assertIn("500", p)

    def test_age_5_7_word_count_target(self):
        p = main.build_storyteller_prompt(main.CULTURAL_TEMPLATES["WE"], self._make_request(age="5-7"), OUTLINE)
        self.assertIn("400", p)

    def test_energetic_pacing_in_prompt(self):
        p = main.build_storyteller_prompt(main.CULTURAL_TEMPLATES["WE"], self._make_request(state="energetic"), OUTLINE)
        self.assertIn("Energetic", p)

    def test_sleepy_pacing_in_prompt(self):
        p = main.build_storyteller_prompt(main.CULTURAL_TEMPLATES["WE"], self._make_request(state="sleepy"), OUTLINE)
        self.assertIn("soothing", p.lower())

    def test_mandatory_dialogue_rule_present(self):
        p = main.build_storyteller_prompt(main.CULTURAL_TEMPLATES["WE"], self._make_request(), OUTLINE)
        self.assertIn("dialogue", p.lower())

    def test_mandatory_sensory_rule_present(self):
        p = main.build_storyteller_prompt(main.CULTURAL_TEMPLATES["WE"], self._make_request(), OUTLINE)
        self.assertIn("sensory", p.lower())

    def test_output_format_instruction_present(self):
        p = main.build_storyteller_prompt(main.CULTURAL_TEMPLATES["WE"], self._make_request(), OUTLINE)
        self.assertIn("TITLE:", p)


# ─────────────────────────────────────────────────────────────────────────────
# build_judge_prompt
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildJudgePrompt(unittest.TestCase):

    STORY = "Once upon a time there was a brave girl named Alice."

    def test_story_in_prompt(self):
        p = main.build_judge_prompt(self.STORY, "Western (西方)", "8-10")
        self.assertIn(self.STORY, p)

    def test_culture_name_in_prompt(self):
        p = main.build_judge_prompt(self.STORY, "Japanese (日本)", "5-7")
        self.assertIn("Japanese (日本)", p)

    def test_age_range_in_prompt(self):
        p = main.build_judge_prompt(self.STORY, "African (非洲)", "5-7")
        self.assertIn("5-7", p)

    def test_cot_steps_present(self):
        p = main.build_judge_prompt(self.STORY, "Chinese (中国)", "8-10")
        self.assertIn("STEP 1", p)
        self.assertIn("STEP 2", p)

    def test_all_five_dimensions_present(self):
        p = main.build_judge_prompt(self.STORY, "Arabian (阿拉伯)", "5-7")
        for dim in ["age_appropriateness", "story_arc", "cultural_authenticity",
                    "engagement", "moral_lesson"]:
            self.assertIn(dim, p)

    def test_json_output_instruction_present(self):
        p = main.build_judge_prompt(self.STORY, "Western (西方)", "8-10")
        self.assertIn("average_score", p)


# ─────────────────────────────────────────────────────────────────────────────
# build_refinement_prompt
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildRefinementPrompt(unittest.TestCase):

    def setUp(self):
        self.template = main.CULTURAL_TEMPLATES["JP"]
        self.request = {
            "culture_code": "JP",
            "culture_name": "Japanese (日本)",
            "age_range": "5-7",
            "bedtime_state": "sleepy",
            "protagonist_name": "Hana",
            "protagonist_gender": "girl",
            "theme": "curiosity",
        }
        self.story = "TITLE: The Lantern\n---\nOnce there was a girl named Hana."
        self.judge = {
            "scores": {"age_appropriateness": 9, "story_arc": 5, "cultural_authenticity": 8,
                       "engagement": 6, "moral_lesson": 7},
            "justifications": {k: "OK." for k in ["age_appropriateness", "story_arc",
                                                   "cultural_authenticity", "engagement", "moral_lesson"]},
            "improvement_suggestions": {"age_appropriateness": "No improvement needed",
                                        "story_arc": "Add more resolution detail.",
                                        "cultural_authenticity": "No improvement needed",
                                        "engagement": "Add sensory details.",
                                        "moral_lesson": "No improvement needed"},
            "average_score": 7.0,
            "overall_feedback": "Good story; arc needs work.",
        }

    def test_original_story_in_prompt(self):
        p = main.build_refinement_prompt(self.story, self.judge, self.template, self.request)
        self.assertIn("The Lantern", p)

    def test_protagonist_preservation_noted(self):
        p = main.build_refinement_prompt(self.story, self.judge, self.template, self.request)
        self.assertIn("Hana", p)

    def test_culture_preservation_noted(self):
        p = main.build_refinement_prompt(self.story, self.judge, self.template, self.request)
        self.assertIn("Japanese (日本)", p)

    def test_low_score_suggestion_included(self):
        p = main.build_refinement_prompt(self.story, self.judge, self.template, self.request)
        self.assertIn("Add more resolution detail", p)

    def test_word_range_5_7(self):
        p = main.build_refinement_prompt(self.story, self.judge, self.template, self.request)
        self.assertIn("400", p)

    def test_word_range_8_10(self):
        req_older = {**self.request, "age_range": "8-10"}
        p = main.build_refinement_prompt(self.story, self.judge, self.template, req_older)
        self.assertIn("500", p)


# ─────────────────────────────────────────────────────────────────────────────
# format_quality_report
# ─────────────────────────────────────────────────────────────────────────────

class TestFormatQualityReport(unittest.TestCase):

    def _make_judge(self, avg):
        dims = ["age_appropriateness", "story_arc", "cultural_authenticity",
                "engagement", "moral_lesson"]
        return {
            "analysis": "Analysis here.",
            "scores": {d: round(avg) for d in dims},
            "justifications": {d: "Fine." for d in dims},
            "improvement_suggestions": {d: "No improvement needed" for d in dims},
            "average_score": avg,
            "overall_feedback": "Overall decent.",
        }

    def test_passed_label_above_threshold(self):
        r = main.format_quality_report(self._make_judge(7.0), 0)
        self.assertIn("passed", r)

    def test_below_threshold_label(self):
        r = main.format_quality_report(self._make_judge(6.9), 2)
        self.assertIn("below threshold", r)

    def test_rounds_shown(self):
        r = main.format_quality_report(self._make_judge(8.0), 2)
        self.assertIn("2", r)

    def test_average_score_shown(self):
        r = main.format_quality_report(self._make_judge(7.4), 0)
        self.assertIn("7.4", r)

    def test_all_dimension_labels_shown(self):
        r = main.format_quality_report(self._make_judge(8.0), 0)
        self.assertIn("Story Arc", r)
        self.assertIn("Engagement", r)
        self.assertIn("Moral Lesson", r)

    def test_analysis_shown(self):
        r = main.format_quality_report(self._make_judge(8.0), 0)
        self.assertIn("Analysis here.", r)


# ─────────────────────────────────────────────────────────────────────────────
# run_story_pipeline  — mocked call_model, tests orchestration logic only
# ─────────────────────────────────────────────────────────────────────────────

class TestRunStoryPipelineMocked(unittest.TestCase):

    def _judge_json(self, avg):
        dims = ["age_appropriateness", "story_arc", "cultural_authenticity",
                "engagement", "moral_lesson"]
        score = round(avg)
        return json.dumps({
            "analysis": "Analysis.",
            "scores": {d: score for d in dims},
            "justifications": {d: "Fine." for d in dims},
            "improvement_suggestions": {d: "No improvement needed" for d in dims},
            "average_score": avg,
            "overall_feedback": "Overall feedback.",
        })

    def setUp(self):
        self.template = main.CULTURAL_TEMPLATES["WE"]
        self.request = {
            "culture_code": "WE",
            "culture_name": "Western (西方)",
            "age_range": "8-10",
            "bedtime_state": "energetic",
            "protagonist_name": "Alice",
            "protagonist_gender": "girl",
            "theme": "friendship",
        }
        self.outline = "1. Setup\n2. Spark\n3. Challenge\n4. Turn\n5. Resolution"

    @patch("main.call_model")
    def test_no_refinement_when_first_score_passes(self, mock_call):
        mock_call.side_effect = [
            "TITLE: Good Story\n---\nOnce upon a time...",
            self._judge_json(8.0),
        ]
        story, judge, rounds = main.run_story_pipeline(self.template, self.request, self.outline)
        self.assertEqual(rounds, 0)
        self.assertEqual(judge["average_score"], 8.0)
        self.assertEqual(mock_call.call_count, 2)  # storyteller + 1 judge

    @patch("main.call_model")
    def test_one_refinement_round_when_first_fails(self, mock_call):
        mock_call.side_effect = [
            "TITLE: Draft\n---\nFirst draft.",
            self._judge_json(6.0),           # fail
            "TITLE: Refined\n---\nBetter.",
            self._judge_json(7.5),           # pass
        ]
        story, judge, rounds = main.run_story_pipeline(self.template, self.request, self.outline)
        self.assertEqual(rounds, 1)
        self.assertEqual(judge["average_score"], 7.5)
        self.assertIn("Refined", story)
        self.assertEqual(mock_call.call_count, 4)

    @patch("main.call_model")
    def test_stops_at_max_two_rounds(self, mock_call):
        mock_call.side_effect = [
            "TITLE: V1\n---\nFirst.",
            self._judge_json(5.0),
            "TITLE: V2\n---\nSecond.",
            self._judge_json(5.5),
            "TITLE: V3\n---\nThird.",
            self._judge_json(6.0),
        ]
        story, judge, rounds = main.run_story_pipeline(
            self.template, self.request, self.outline, max_refinement_rounds=2
        )
        self.assertEqual(rounds, 2)
        self.assertIn("V3", story)
        self.assertEqual(mock_call.call_count, 6)

    @patch("main.call_model")
    def test_returns_latest_story(self, mock_call):
        mock_call.side_effect = [
            "TITLE: Original\n---\nOriginal story.",
            self._judge_json(6.0),
            "TITLE: Refined\n---\nRefined story.",
            self._judge_json(8.0),
        ]
        story, _, _ = main.run_story_pipeline(self.template, self.request, self.outline)
        self.assertIn("Refined", story)
        self.assertNotIn("Original", story)

    @patch("main.call_model")
    def test_zero_max_rounds_never_refines(self, mock_call):
        mock_call.side_effect = [
            "TITLE: Story\n---\nContent.",
            self._judge_json(3.0),   # very low, but max_refinement_rounds=0
        ]
        story, judge, rounds = main.run_story_pipeline(
            self.template, self.request, self.outline, max_refinement_rounds=0
        )
        self.assertEqual(rounds, 0)
        self.assertEqual(mock_call.call_count, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
