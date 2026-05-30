import json
import os
import re
from datetime import datetime

MEMORY_FILE = "Data/memory.json"

def _ensure_file():
    os.makedirs("Data", exist_ok=True)
    if not os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "w") as f:
            json.dump([], f)

def _load():
    _ensure_file()
    try:
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def _save(data):
    _ensure_file()
    with open(MEMORY_FILE, "w") as f:
        json.dump(data, f, indent=2)

def save_memory(fact):
    data = _load()
    data.append({
        "fact": fact,
        "timestamp": datetime.now().isoformat()
    })
    _save(data)

def get_all_memories():
    return _load()

def get_memory_context():
    data = _load()
    if not data:
        return ""
    facts = [m["fact"] for m in data[-20:]]
    return "Remembered facts:\n- " + "\n- ".join(facts)

def search_memories(query):
    data = _load()
    words = query.lower().split()
    results = []
    for m in data:
        fact_lower = m["fact"].lower()
        if any(w in fact_lower for w in words):
            results.append(m["fact"])
    return results

def forget_memories(topic):
    data = _load()
    topic_lower = topic.lower()
    kept = [m for m in data if topic_lower not in m["fact"].lower()]
    _save(kept)
    return len(data) - len(kept)

def clear_all():
    _save([])
