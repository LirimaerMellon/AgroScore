"""Measure response size: old SELECT * vs new lightweight SELECT."""
import sys, json
sys.path.insert(0, '.')
from app.database.connection import Database
from app.database.app_repository import ApplicationRepository

db = Database('data/agriscore.db')
repo = ApplicationRepository(db)

# Lightweight shortlist (current fix)
result = repo.get_shortlist(model_version='v_20260405_205231', strategy='more_applications')
payload = json.dumps(result, ensure_ascii=False, default=str)
print("Lightweight response size: %.2f MB" % (len(payload) / 1024 / 1024))
print("Apps returned:", len(result["selected"]))

# Check that apps don't contain shap_explanation
sample = result["selected"][0]
has_shap = "shap_explanation" in sample
has_warnings = "data_warnings" in sample
print("Contains shap_explanation:", has_shap)
print("Contains data_warnings:", has_warnings)
print("Keys in app:", sorted(sample.keys()))

