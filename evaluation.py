# evaluation.py - Simple Evaluation Metrics for Murder Mystery Quality
from typing import Dict, List
import re
from llm_pipeline.llm_client import chat


class SimpleEvaluator:
    """Evaluates murder mystery quality with automated and LLM-based metrics"""

    def evaluate_mystery(
        self, menu, case_data, characters, last_day_data, clues, solution
    ):
        """Run all evaluation metrics and return scores"""

        print("\n" + "=" * 60)
        print(" EVALUATING MYSTERY QUALITY...")
        print("=" * 60)

        results = {"scores": {}, "details": {}}

        # 1. Character Consistency: Are all characters mentioned in solution?
        print("\n Checking character consistency...")
        char_names = [c["name"] for c in characters]
        solution_text = str(solution).lower()

        mentioned = sum(1 for name in char_names if name.lower() in solution_text)
        char_score = (mentioned / len(char_names)) * 10
        results["scores"]["character_consistency"] = round(char_score, 1)
        results["details"]["characters_mentioned"] = f"{mentioned}/{len(char_names)}"
        print(
            f"   ✓ Character mentions: {mentioned}/{len(char_names)} ({char_score:.1f}/10)"
        )

        # 2. Timeline Completeness: At least 5 events in timeline
        print("\n Checking timeline completeness...")
        timeline = last_day_data.get("timeline", [])
        timeline_score = min(len(timeline) / 5, 1.0) * 10
        results["scores"]["timeline_completeness"] = round(timeline_score, 1)
        results["details"]["timeline_events"] = len(timeline)
        print(f"   ✓ Timeline events: {len(timeline)} ({timeline_score:.1f}/10)")

        # 3. Clue Quantity: At least 7 clues for full score
        print("\n Checking clue quantity...")
        total_clues = sum(len(c.get("clues", [])) for c in clues)
        clue_score = min(total_clues / 7, 1.0) * 7
        results["scores"]["clue_quantity"] = round(clue_score, 1)
        results["details"]["total_clues"] = total_clues
        print(f"   ✓ Total clues: {total_clues} ({clue_score:.1f}/7)")

        # 4. RAG Integration: Menu items mentioned in case
        print("\n Checking RAG integration...")
        case_text = str(case_data).lower()
        menu_mentioned = 0

        for course in ["starter", "main", "dessert"]:
            item = menu.get(course)
            if item and hasattr(item, "name"):
                # Check if first word of dish is in case text
                first_word = item.name.split()[0].lower()
                if first_word in case_text and len(first_word) > 3:
                    menu_mentioned += 1

        rag_score = (menu_mentioned / 3) * 10
        results["scores"]["rag_integration"] = round(rag_score, 1)
        results["details"]["menu_items_used"] = f"{menu_mentioned}/3"
        print(f"   ✓ Menu items integrated: {menu_mentioned}/3 ({rag_score:.1f}/10)")

        # 5. LLM Judge: Overall narrative quality (ONE call)
        print("\n5️ Running LLM quality assessment...")
        narrative_score = self._llm_judge_quality(case_data, characters[:2], solution)
        results["scores"]["narrative_quality"] = narrative_score
        print(f"   ✓ LLM narrative rating: {narrative_score:.1f}/10")

        # Calculate overall score
        avg = sum(results["scores"].values()) / len(results["scores"])
        results["overall_score"] = round(avg, 1)

        # Print summary
        self.print_report(results)

        return results

    def _llm_judge_quality(self, case_data, sample_characters, solution):
        """Single LLM call to judge overall quality"""

        prompt = f"""Rate this murder mystery on a scale of 0-10.
Consider: creativity, coherence, and interest level.

Case Summary: {case_data.get("summary", "")[:200]}
Characters: {", ".join([c["name"] for c in sample_characters])}
Killer: {solution.get("killer_name", "")}
Motive: {solution.get("motive", "")[:100]}

Respond with ONLY a number between 0 and 10."""

        try:
            response = chat(
                messages=[{"role": "user", "content": prompt}], temperature=0.3
            )
            # Extract number
            match = re.search(r"(\d+\.?\d*)", response)
            if match:
                score = float(match.group(1))
                return min(max(score, 0), 10)  # Clamp between 0-10
            return 5.0
        except Exception as e:
            print(f"   LLM judge error: {e}")
            return 5.0

    def print_report(self, results):
        """Print formatted evaluation report"""
        print("\n" + "=" * 60)
        print(" EVALUATION REPORT")
        print("=" * 60)

        for metric, score in results["scores"].items():
            # Create visual bar
            filled = int(score)
            empty = 10 - filled
            bar = "█" * filled + "░" * empty

            # Format metric name
            metric_name = metric.replace("_", " ").title()

            print(f"{metric_name:.<40} {score:>4.1f}/10 {bar}")

        print("-" * 60)
        print(f"{'OVERALL SCORE':.<40} {results['overall_score']:>4.1f}/10")
        print("=" * 60)

        print("\n Details:")
        for key, value in results["details"].items():
            detail_name = key.replace("_", " ").title()
            print(f"  • {detail_name}: {value}")
        print()

    def save_report(self, results, filename="outputs/evaluation_report.json"):
        """Save evaluation results to JSON"""
        import os
        import json

        os.makedirs(os.path.dirname(filename), exist_ok=True)

        with open(filename, "w") as f:
            json.dump(results, f, indent=2)

        print(f" Evaluation report saved: {filename}\n")
        return filename
