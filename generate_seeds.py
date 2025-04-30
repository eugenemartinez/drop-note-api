# filepath: backend/generate_seeds.py
import json
import random
from faker import Faker

fake = Faker()

NUM_NOTES = 50
notes_data = []

# Predefined tags for variety
possible_tags = [
    "python", "javascript", "vue", "react", "flask", "database", "sql",
    "webdev", "tutorial", "guide", "tips", "tricks", "thoughts",
    "random", "idea", "project", "learning", "code", "snippet",
    "config", "setup", "docker", "cloud", "api", "testing", "css",
    "html", "typescript", "performance", "security"
]

for _ in range(NUM_NOTES):
    num_tags = random.randint(0, 5) # 0 to 5 tags per note
    tags = random.sample(possible_tags, num_tags) if num_tags > 0 else []
    visibility = random.choice(['public', 'public', 'public', 'private']) # ~75% public

    note = {
        "title": fake.sentence(nb_words=random.randint(3, 8)).rstrip('.'),
        "content": fake.text(max_nb_chars=random.randint(50, 500)),
        "username": fake.user_name(),
        "tags": tags,
        "visibility": visibility
    }
    notes_data.append(note)

# Define the output file path (e.g., in the same directory as the script)
output_file = 'sample_notes.json'

try:
    with open(output_file, 'w') as f:
        json.dump(notes_data, f, indent=2)
    print(f"Successfully generated {NUM_NOTES} sample notes in '{output_file}'")
except IOError as e:
    print(f"Error writing to file '{output_file}': {e}")
