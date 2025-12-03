# main.py
from llm_pipeline.case_generator import generate_case
from llm_pipeline.character_generator import generate_characters
from llm_pipeline.dialogue_generator import generate_dialogues
from llm_pipeline.last_day_victim import generate_last_day
from llm_pipeline.clue_generator import generate_clues
from llm_pipeline.solution_generator import generate_solution
from rag.retriever import RagRetriever
from image_tool.image_generator import generate_character_image

NUM_CHARACTERS = 7

def main():
    # 1. Optional: user input for theme / setting
    user_prompt = input("Enter a desired setting or theme (or leave empty): ").strip()
    if not user_prompt:
        user_prompt = "A small coastal town with a controversial political scandal"

    # 2. Initialize RAG retriever (stub for now)
    retriever = RagRetriever(index_path="data/index")  # adapt later

    # 3. Generate the case (victim + theme)
    case_data = generate_case(user_prompt=user_prompt)
    print("\n=== CASE ===")
    print(case_data)

    # 4. Generate characters (with RAG context)
    characters = generate_characters(
        case_data=case_data,
        num_characters=NUM_CHARACTERS,
        retriever=retriever
    )

    print("\n=== CHARACTERS ===")
    for c in characters:
        print(f"- {c['name']}: {c['occupation']} ({c['relation_to_victim']})")
        print(f"  Secret: {c['secret']}")
        print(f"  Appearance: {c['appearance']}")
        print(f"  Muder [Y/N]: {c['muderer_label']}")
        print()

    # 6. Reconstruct the victim's last day
    last_day_data = generate_last_day(case_data=case_data, characters=characters)

    print("\n=== VICTIM'S LAST DAY ===")
    print("Overview:", last_day_data.get("overview", ""))
    print("Timeline:")
    for event in last_day_data.get("timeline", []):
        print(f"- {event['time']} @ {event['location']}: {event['description']}")
        print(f"  Participants: {', '.join(event['participants'])}")
        print(f"  Suspicious: {event['suspicious']}")

    # 7. generate clues
    clues = generate_clues(
        case_data=case_data,
        characters=characters,
        last_day_data=last_day_data
    )

    print("\n=== CHARACTER CLUES ===")
    for entry in clues:
        print(f"\n{entry['character']} has clues:")
        for c in entry["clues"]:
            print(f"  -> About {c['target']}: {c['clue']}")

    # 8. Generate solution
    solution = generate_solution(
        case_data=case_data,
        characters=characters,
        last_day_data=last_day_data,
        clues=clues,
    )

    # keep murderer_label consistent with solution
    killer_name = solution.get("killer_name")
    if killer_name:
        for c in characters:
            c["murderer_label"] = (c["name"] == killer_name)

    print("\n=== FINAL SOLUTION ===")
    print(f"Killer: {solution.get('killer_name')}")
    print("\nMotive:")
    print(solution.get("motive", ""))

    print("\nMethod:")
    print(solution.get("method", ""))

    print("\nOpportunity:")
    print(solution.get("opportunity", ""))

    print("\nHow the clues fit together:")
    for align in solution.get("clue_alignment", []):
        print(
            f" - {align['character']}'s clue about {align['about']} "
            f"({align['clue_role']}): {align['explanation']}"
        )

    print("\nAlternative suspects:")
    for alt in solution.get("alternative_suspects", []):
        print(f" - {alt['name']}: {alt['why_they_looked_suspicious']}")

    print("\n=== FINAL REVEAL MONOLOGUE ===")
    print(solution.get("final_reveal_monologue", ""))
    
          
    # # 5. Generate one image per character (tool stub for now)
    # for c in characters:
    #     img_path_or_url = generate_character_image(
    #         name=c["name"],
    #         appearance=c["appearance"]
    #     )
    #     c["image"] = img_path_or_url

    # # 6. Generate dialogues (each character should talk at least once)
    # dialogues = generate_dialogues(characters=characters, case_data=case_data)

    # print("\n=== DIALOGUES ===")
    # for i, scene in enumerate(dialogues, start=1):
    #     print(f"\n--- Scene {i} ---")
    #     for turn in scene["turns"]:
    #         print(f"{turn['speaker']}: {turn['utterance']}")

if __name__ == "__main__":
    main()
