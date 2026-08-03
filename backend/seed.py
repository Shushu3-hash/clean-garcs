"""
seed.py — Seeds the GARCS database with starter content: passages tagged
with a grade_band, and questions tagged with skill_tag (literal/inferential/
critical) and difficulty (easy/medium/hard), per Chapter 3.6.3.

Place this file in the same folder as your Phase 1 app.py and run:
    python seed.py

Grade-band convention used here (keep this consistent with your Chapter 3
write-up so it's documented somewhere):
    grade_band 1 -> Grades 5-6
    grade_band 2 -> Grades 7-8
    grade_band 3 -> Grades 9-10

Re-running this script is safe: it clears existing Passage/Question rows
first, so you won't get duplicates every time you re-seed during dev.

This gives you 6 passages x 3 questions = 18 questions, with at least one
question in every (skill_tag, difficulty) combination -- so
sequencing.pick_next_question() always has at least one candidate no
matter which skill/difficulty the engine targets. This is a STARTER set.
Your roadmap's target for a real pilot is 15-25 passages x 3-5 questions
each -- keep adding entries to PASSAGES below using the same structure.

Content note: these passages/questions were drafted for engineering
purposes (to give the adaptive engine real data to run against). Before
your pilot, it's worth having a reading/curriculum-literate reviewer (your
adviser, a co-author, or a teacher) sanity-check wording and grade-level
appropriateness -- content validity matters for a reading comprehension
thesis in a way that's hard for me to fully verify from here.
"""

from app import app, db, Passage, Question  # adjust if your Phase 1 file has a different name


PASSAGES = [
    {
        "title": "The School Garden",
        "grade_band": 1,
        "body": (
            "Every Friday afternoon, the Grade 5 students at Mabuhay Elementary School "
            "take turns watering the plants in their small school garden. Ms. Reyes, their "
            "teacher, started the garden last year so students could learn where vegetables "
            "come from. The garden now has tomatoes, eggplants, and pechay. Some students did "
            "not want to help at first because they thought gardening was messy. But after "
            "harvesting their first batch of pechay and cooking it for lunch, many students "
            "asked if they could plant more vegetables next term."
        ),
        "questions": [
            {
                "prompt": "Who started the school garden?",
                "choices": ["Ms. Reyes", "The principal", "The Grade 5 students", "A parent volunteer"],
                "correct_index": 0,
                "skill_tag": "literal",
                "difficulty": "easy",
            },
            {
                "prompt": "Why did some students change their minds about gardening?",
                "choices": [
                    "They were graded on it",
                    "They enjoyed eating what they grew",
                    "Ms. Reyes gave them prizes",
                    "The garden was moved indoors",
                ],
                "correct_index": 1,
                "skill_tag": "inferential",
                "difficulty": "easy",
            },
            {
                "prompt": "What is the best lesson the passage is teaching?",
                "choices": [
                    "Gardening is always messy",
                    "Trying something new can change how you feel about it",
                    "Only teachers should start gardens",
                    "Vegetables taste better than fruits",
                ],
                "correct_index": 1,
                "skill_tag": "critical",
                "difficulty": "easy",
            },
        ],
    },
    {
    "title": "RACE Passage (high10024.txt)",
            "grade_band": 3,
            "grade_level_estimate": 10.8,
            "body": "One thinks of princes and presidents as some of the most powerful people in the world; however, governments, elected or otherwise, sometimes have had to struggle with the financial powerhouses called tycoons. The word tycoon is relatively new to the English language. It is Chinese in origin but was given as a title to some Japanese generals. The term was brought to the United States, in the late nineteenth century, where it eventually was used to refer to magnates who acquired immense fortunes from sugar and cattle, coal and oil, rubber and steel, and railroads. Some people called these tycoons \"capitals of industry\" and praised them for their contributions to U.S. wealth and international reputation. Others criticized them as cruel \"robber barons\", who would stop at nothing in pursuit of personal wealth.\nThe early tycoons built successful businesses, often taking over smaller companies to eliminate competition. A single company that came to control an entire market was called a monopoly. Monopolies made a few families very wealthy, but they also placed a heavy financial burden on consumers and the economy at large.\nAs the country expanded and railroads linked the East Coast to the West Coast, local monopolies turned into national corporations called trusts. A trust is a group of companies that join together under the control of a board of trustees. Railroad trusts are an excellent example. Railroads were privately owned and operated and often monopolized various routes, setting rates as high as they desired. The financial burden this placed on passengers and businesses increased when railroads formed trusts. Farmers, for example, had no choice but to pay, as railroads were the only means they could use to get their grain to buyers. Exorbitant   goods rates put some farmers out of business.\nThere were even accusations that the trusts controlled government itself by buying votes and manipulating elected officials. In 1890 Congress passed the Sherman Antitrust. Act, legislation aimed at breaking the power of such trusts. The Sherman Antitrust Act focused on two main issues. First of all, it made illegal any effort to interfere with the normal conduct of interstate trade. It also made it illegal to monopolize any part of business that operates across state lines.\nOver the next 60 years or so, Congress passed other antitrust laws in an effort to encourage competition and restrict the power of larger corporations.",
            "source": "RACE (Lai et al., 2017) - non-commercial research use only - https://arxiv.org/abs/1704.04683",
            "questions": [
                {
                    "prompt": "The Sherman Antitrust Act  _  .",
                    "choices": [
                        "affected only the companies doing business within state lines",
                        "sought to eliminate monopolies in favor of competition in the market-place",
                        "promoted trade with a large number of nations",
                        "provides a financial advantage to the buyer"
                    ],
                    "correct_index": 1,
                    "skill_tag": "inferential",
                    "difficulty": "medium",
                    "needs_review": True
                },
                {
                    "prompt": "One might infer from this passage that lower prices   _  .",
                    "choices": [
                        "are more likely to exist in a competitive market economy",
                        "usually can be found only in an economy based on monopolies",
                        "matter only to people who are poor and living below the poverty level",
                        "are regulated by the government"
                    ],
                    "correct_index": 0,
                    "skill_tag": "inferential",
                    "difficulty": "medium",
                    "needs_review": True
                },
                {
                    "prompt": "It seems likely that many Americans  _  .",
                    "choices": [
                        "believed that the trusts had little influence over government",
                        "expected the wealthy magnates to share money with the poor",
                        "did little to build up American business",
                        "were worried that trusts might manipulate the government"
                    ],
                    "correct_index": 3,
                    "skill_tag": "inferential",
                    "difficulty": "medium",
                    "needs_review": True
                }
            ]
        },
    {
        "title": "Ana's First Bike Ride",
        "grade_band": 1,
        "body": (
            "Ana had been asking her parents for a bicycle for months. On her tenth birthday, "
            "she finally got one. At first, she was scared to ride it because she kept falling "
            "down. Her older brother, Miguel, held the back of the bike and ran beside her every "
            "afternoon after school. After a week of practice, Ana was able to ride around the "
            "block by herself. She was so proud that she invited her whole class to watch her "
            "ride during recess the next day."
        ),
        "questions": [
            {
                "prompt": "What did Ana receive for her birthday?",
                "choices": ["A skateboard", "A bicycle", "A scooter", "A new bag"],
                "correct_index": 1,
                "skill_tag": "literal",
                "difficulty": "easy",
            },
            {
                "prompt": "Why did Miguel run beside Ana's bike every afternoon?",
                "choices": [
                    "He wanted exercise",
                    "He was helping her learn to balance",
                    "He was racing her",
                    "He was going to school",
                ],
                "correct_index": 1,
                "skill_tag": "inferential",
                "difficulty": "medium",
            },
            {
                "prompt": "What does Ana's decision to invite her classmates show about how she felt?",
                "choices": [
                    "She felt embarrassed",
                    "She felt proud of what she achieved",
                    "She felt nervous about falling again",
                    "She felt bored with biking",
                ],
                "correct_index": 1,
                "skill_tag": "critical",
                "difficulty": "medium",
            },
        ],
    },
    {
        "title": "The Water Cycle in Our Barangay",
        "grade_band": 2,
        "body": (
            "Water in our barangay does not disappear -- it simply moves in a cycle. The sun "
            "heats up water from rivers, lakes, and even puddles, turning it into vapor that "
            "rises into the sky. This process is called evaporation. High in the sky, the vapor "
            "cools down and forms clouds through condensation. When the clouds become heavy with "
            "water, rain falls back to the ground, a process known as precipitation. Some of this "
            "rainwater seeps into the soil and refills the groundwater that many households pump "
            "for drinking and washing, while the rest flows into rivers and streams, continuing "
            "the cycle all over again."
        ),
        "questions": [
            {
                "prompt": "What is the process called when water vapor cools and forms clouds?",
                "choices": ["Evaporation", "Condensation", "Precipitation", "Groundwater flow"],
                "correct_index": 1,
                "skill_tag": "literal",
                "difficulty": "medium",
            },
            {
                "prompt": (
                    "Based on the passage, what would most likely happen if there were far fewer "
                    "trees and open soil in a barangay?"
                ),
                "choices": [
                    "Evaporation would stop completely",
                    "Less rainwater could seep into the ground to refill groundwater",
                    "Clouds would form faster",
                    "Rivers would disappear immediately",
                ],
                "correct_index": 1,
                "skill_tag": "inferential",
                "difficulty": "medium",
            },
            {
                "prompt": "Why might understanding the water cycle be useful for a barangay planning its water supply?",
                "choices": [
                    "It has nothing to do with water supply",
                    "It helps explain where drinking water ultimately comes from and how it might run out",
                    "It only matters for weather forecasters",
                    "It explains why rain is dangerous",
                ],
                "correct_index": 1,
                "skill_tag": "critical",
                "difficulty": "medium",
            },
        ],
    },
    {
        "title": "The Jeepney Driver's Day",
        "grade_band": 2,
        "body": (
            "Mang Tonyo has been driving a jeepney on the same route for eighteen years. He "
            "wakes up at four in the morning to check his vehicle before his first trip. During "
            "rush hour, he sometimes waits nearly an hour in traffic just to travel a few "
            "kilometers. Despite the long hours and low pay, Mang Tonyo says he stays in the job "
            "because he has come to know many of his regular passengers by name, and some of them "
            "buy him coffee or ask about his family. He jokes that his jeepney is like a rolling "
            "barangay, where everyone eventually becomes a familiar face."
        ),
        "questions": [
            {
                "prompt": "How long has Mang Tonyo been driving his jeepney route?",
                "choices": ["Eight years", "Eighteen years", "Twenty-eight years", "One year"],
                "correct_index": 1,
                "skill_tag": "literal",
                "difficulty": "medium",
            },
            {
                "prompt": "What can be inferred about why Mang Tonyo continues driving despite the difficulties?",
                "choices": [
                    "He has no other job options at all",
                    "The relationships he has built with passengers matter more to him than the pay",
                    "He is required to by the government",
                    "He does not notice the traffic anymore",
                ],
                "correct_index": 1,
                "skill_tag": "inferential",
                "difficulty": "hard",
            },
            {
                "prompt": "What does comparing the jeepney to 'a rolling barangay' suggest about Mang Tonyo's view of his job?",
                "choices": [
                    "He sees his work only as a way to earn money",
                    "He views his passengers as a community rather than just customers",
                    "He dislikes his passengers",
                    "He wants to become a barangay official",
                ],
                "correct_index": 1,
                "skill_tag": "critical",
                "difficulty": "hard",
            },
        ],
    },
    {
        "title": "Coral Reefs Under Threat",
        "grade_band": 3,
        "body": (
            "The Philippines sits at the heart of the Coral Triangle, home to some of the most "
            "biodiverse coral reefs on Earth. These reefs shelter thousands of fish species and "
            "protect coastlines from strong waves, yet they are increasingly under threat. Rising "
            "sea temperatures cause coral bleaching, a process in which corals expel the colorful "
            "algae living in their tissues and turn white, often leading to death if conditions do "
            "not improve quickly. Pollution, destructive fishing methods, and unsustainable "
            "tourism practices compound the stress on already weakened reef systems. Marine "
            "scientists warn that without significant intervention, some reef ecosystems may not "
            "recover within our lifetimes, a loss that would ripple through both marine "
            "biodiversity and the coastal communities that depend on healthy reefs for their "
            "livelihoods."
        ),
        "questions": [
            {
                "prompt": "According to the passage, what happens to corals during bleaching?",
                "choices": [
                    "They grow faster than usual",
                    "They expel algae living in their tissues and turn white",
                    "They multiply and spread to new areas",
                    "They become more colorful",
                ],
                "correct_index": 1,
                "skill_tag": "literal",
                "difficulty": "hard",
            },
            {
                "prompt": "What does the passage suggest about the relationship between coral reefs and coastal communities?",
                "choices": [
                    "Coastal communities have no connection to reef health",
                    "Coastal communities' livelihoods are tied to the health of nearby reefs",
                    "Reefs harm coastal communities by causing strong waves",
                    "Coastal communities only value reefs for tourism",
                ],
                "correct_index": 1,
                "skill_tag": "inferential",
                "difficulty": "hard",
            },
            {
                "prompt": (
                    "Why might the author have chosen to end the passage by mentioning the impact "
                    "on coastal communities rather than stopping at the description of coral "
                    "bleaching?"
                ),
                "choices": [
                    "To make the passage longer",
                    "To show that reef damage is not only an environmental issue but also a human one",
                    "To criticize marine scientists",
                    "To argue that coastal communities are the main cause of the damage",
                ],
                "correct_index": 1,
                "skill_tag": "critical",
                "difficulty": "hard",
            },
        ],
    },
    {
        "title": "The Debate on School Uniforms",
        "grade_band": 3,
        "body": (
            "Some students at Bagong Pag-asa National High School have started asking the "
            "administration to make school uniforms optional. Those in favor of the change argue "
            "that uniforms are uncomfortable in hot weather and limit students' ability to "
            "express their personal identity. Those against the change argue that uniforms reduce "
            "visible economic differences between students and make it easier to identify "
            "outsiders on campus for safety reasons. The school principal has not yet made a "
            "decision, saying she wants to hear more student and parent feedback before the next "
            "school year begins."
        ),
        "questions": [
            {
                "prompt": "What reason do uniform supporters give for keeping the policy, according to the passage?",
                "choices": [
                    "Uniforms are cheaper than regular clothes",
                    "Uniforms reduce visible economic differences and help with campus safety",
                    "Uniforms are more comfortable in hot weather",
                    "Uniforms were required by a new national law",
                ],
                "correct_index": 1,
                "skill_tag": "literal",
                "difficulty": "hard",
            },
            {
                "prompt": "What can be inferred about the principal's approach to this decision?",
                "choices": [
                    "She has already decided to remove uniforms",
                    "She is dismissing student opinions entirely",
                    "She wants to gather more input before deciding",
                    "She plans to let each student choose without any discussion",
                ],
                "correct_index": 2,
                "skill_tag": "inferential",
                "difficulty": "medium",
            },
            {
                "prompt": "Which side of the argument does the passage support?",
                "choices": [
                    "It clearly supports removing uniforms",
                    "It clearly supports keeping uniforms",
                    "It presents both sides without taking a position",
                    "It only discusses the principal's opinion",
                ],
                "correct_index": 2,
                "skill_tag": "critical",
                "difficulty": "easy",
            },
        ],
    },
]


def seed():
    with app.app_context():
        # Clear existing content so re-running this script during dev
        # doesn't pile up duplicate passages/questions.
        db.session.query(Question).delete()
        db.session.query(Passage).delete()
        db.session.commit()

        total_questions = 0
        for p in PASSAGES:
            passage = Passage(title=p["title"], body=p["body"], grade_band=p["grade_band"])
            db.session.add(passage)
            db.session.flush()  # assigns passage.id before we attach questions to it

            for q in p["questions"]:
                db.session.add(
                    Question(
                        passage_id=passage.id,
                        prompt=q["prompt"],
                        choices=q["choices"],
                        correct_index=q["correct_index"],
                        skill_tag=q["skill_tag"],
                        difficulty=q["difficulty"],
                    )
                )
                total_questions += 1

        db.session.commit()
        print(f"Seeded {len(PASSAGES)} passages and {total_questions} questions.")

        # Quick sanity check: confirm every (skill, difficulty) combo has
        # at least one question, since the adaptive engine assumes this.
        skills = ("literal", "inferential", "critical")
        difficulties = ("easy", "medium", "hard")
        missing = []
        for s in skills:
            for d in difficulties:
                count = Question.query.filter_by(skill_tag=s, difficulty=d).count()
                if count == 0:
                    missing.append((s, d))
        if missing:
            print(f"WARNING: no questions found for these (skill, difficulty) combos: {missing}")
        else:
            print("All 9 (skill, difficulty) combinations have at least one question.")


if __name__ == "__main__":
    seed()
