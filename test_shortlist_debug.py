import sys; sys.path.insert(0, '.')
from app.database.connection import Database
from app.database.app_repository import ApplicationRepository

db = Database('data/agriscore.db')
repo = ApplicationRepository(db)

# Test shortlist with model_version (the active second model)
result = repo.get_shortlist(model_version='v_20260405_205231', strategy='more_applications')
print("=== With model_version=v_20260405_205231 ===")
print("selected_count:", result["selected_count"])
print("total_candidates:", result["total_candidates"])
print("total_in_db:", result["total_in_db"])
print("len(selected):", len(result["selected"]))
if result['selected']:
    app = result["selected"][0]
    print("First app: score=%s, model=%s, amount=%s" % (app["score"], app["model_version"], app["amount"]))

# Test shortlist without model_version
result2 = repo.get_shortlist(strategy='more_applications')
print("\n=== Without model_version ===")
print("selected_count:", result2["selected_count"])
print("total_candidates:", result2["total_candidates"])
print("total_in_db:", result2["total_in_db"])
print("len(selected):", len(result2["selected"]))

# Test shortlist with first model
result3 = repo.get_shortlist(model_version='v_20260405_202217', strategy='more_applications')
print("\n=== With model_version=v_20260405_202217 (first model) ===")
print("selected_count:", result3["selected_count"])
print("total_candidates:", result3["total_candidates"])

