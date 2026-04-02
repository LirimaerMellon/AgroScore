"""Тестовый скрипт для проверки всех API."""
import urllib.request
import urllib.error
import json
import sys
import os
import glob
import mimetypes

# Переходим в корень проекта (чтобы пути data/raw/* работали)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(PROJECT_ROOT)

BASE = "http://127.0.0.1:8000"

passed = 0
failed = 0


def _report(ok: bool, label: str):
    global passed, failed
    if ok:
        passed += 1
    else:
        failed += 1


def get(path):
    try:
        resp = urllib.request.urlopen(f"{BASE}{path}")
        data = json.loads(resp.read())
        print(f"  OK {resp.status} {path}")
        _report(True, path)
        return data
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:500]
        print(f"  FAIL {path}: {e.code} {body}")
        _report(False, path)
        return None
    except Exception as e:
        print(f"  FAIL {path}: {e}")
        _report(False, path)
        return None


def get_raw(path):
    """GET запрос, возвращающий сырой ответ (для бинарных данных)."""
    try:
        resp = urllib.request.urlopen(f"{BASE}{path}")
        data = resp.read()
        print(f"  OK {resp.status} {path}, content-length: {len(data)} bytes")
        _report(True, path)
        return data
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:500]
        print(f"  FAIL {path}: {e.code} {body}")
        _report(False, path)
        return None
    except Exception as e:
        print(f"  FAIL {path}: {e}")
        _report(False, path)
        return None


def post_file(path, filepath):
    boundary = "----FormBoundary123456"
    filename = os.path.basename(filepath)
    ct = mimetypes.guess_type(filename)[0] or "application/octet-stream"

    with open(filepath, "rb") as f:
        file_data = f.read()

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: {ct}\r\n\r\n"
    ).encode("utf-8") + file_data + f"\r\n--{boundary}--\r\n".encode("utf-8")

    req = urllib.request.Request(
        f"{BASE}{path}",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        resp = urllib.request.urlopen(req)
        data = json.loads(resp.read())
        print(f"  OK {resp.status} {path}")
        _report(True, path)
        return data
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:500]
        print(f"  FAIL {path}: {e.code} {body}")
        _report(False, path)
        return None
    except Exception as e:
        print(f"  FAIL {path}: {e}")
        _report(False, path)
        return None


if __name__ == "__main__":
    print("=" * 60)
    print("AGRISCORE API TEST")
    print("=" * 60)

    # ── 1. Health ─────────────────────────────────────────────
    print("\n[1] Health check")
    h = get("/health")
    if h:
        print(f"      model_loaded: {h.get('model_loaded')}")

    # ── 2. Train ──────────────────────────────────────────────
    print("\n[2] Train model")
    xlsx_files = glob.glob("data/raw/*.xlsx")
    xlsx_files = [f for f in xlsx_files if not os.path.basename(f).startswith("~$")]

    if not xlsx_files:
        print("  No xlsx files found in data/raw/")
        sys.exit(1)

    print(f"      file: {xlsx_files[0]}")
    train_result = post_file("/api/train", xlsx_files[0])
    if train_result:
        print(f"      model_version: {train_result.get('model_version')}")
        print(f"      metrics.auc_mean: {train_result.get('metrics', {}).get('auc_mean')}")
        print(f"      trace_id: {train_result.get('trace_id')}")
    else:
        print("      ⚠ Training failed — remaining tests use existing model")

    # ── 3. Health after training ──────────────────────────────
    print("\n[3] Health after training")
    h = get("/health")
    if h:
        print(f"      model_loaded: {h.get('model_loaded')}")
        print(f"      active_model: {h.get('active_model')}")

    # ── 4. Models ─────────────────────────────────────────────
    print("\n[4] List models")
    m = get("/api/models")
    if m:
        print(f"      total models: {m.get('total')}")

    # ── 5. Score ──────────────────────────────────────────────
    print("\n[5] Score applications")
    score_result = post_file("/api/score", xlsx_files[0])
    if score_result:
        print(f"      total_scored: {score_result.get('total_scored')}")
        cats = score_result.get('categories', {})
        print(f"      categories: HIGH={cats.get('HIGH',0)}, "
              f"MEDIUM={cats.get('MEDIUM',0)}, LOW={cats.get('LOW',0)}")

    # ── 6. Applications ──────────────────────────────────────
    print("\n[6] Applications list")
    apps = get("/api/applications?limit=5")
    if apps:
        print(f"      total: {apps.get('total')}")
        items = apps.get("items", [])
        if items:
            first = items[0]
            print(f"      first app: id={first.get('id')}, score={first.get('score')}, "
                  f"category={first.get('category')}")

            # 6b. Application detail
            print("\n[6b] Application detail")
            app_detail = get(f"/api/applications/{first['id']}")
            if app_detail and "application" in app_detail:
                a = app_detail["application"]
                print(f"      score={a.get('score')}, region={a.get('region')}")

    # ── 7. Analytics: summary ─────────────────────────────────
    print("\n[7] Analytics summary")
    s = get("/api/analytics/summary")
    if s:
        print(f"      total_applications: {s.get('total_applications')}")

    # ── 8. Analytics: distribution ────────────────────────────
    print("\n[8] Analytics distribution")
    d = get("/api/analytics/distribution?bins=5")
    if d:
        print(f"      bins count: {len(d.get('bins', []))}")

    # ── 9. Analytics: features ────────────────────────────────
    print("\n[9] Feature importance")
    fi = get("/api/analytics/features")
    if fi:
        features = fi.get("features", [])
        print(f"      top-3: {[f['feature'] for f in features[:3]]}")

    # ── 10. Analytics: fairness ───────────────────────────────
    print("\n[10] Fairness report")
    fr = get("/api/analytics/fairness")
    if fr:
        print(f"      keys: {list(fr.keys())}")

    # ── 11. Template download ─────────────────────────────────
    print("\n[11] Template download")
    tpl = get_raw("/api/template")

    # ── 12. Errors ────────────────────────────────────────────
    print("\n[12] Errors log")
    e = get("/api/errors")
    if e:
        print(f"      total errors: {e.get('total')}")

    # ── 13. Errors summary ────────────────────────────────────
    print("\n[13] Errors summary")
    es = get("/api/errors/summary")
    if es:
        print(f"      keys: {list(es.keys())}")

    # ── 14. Errors traces ─────────────────────────────────────
    print("\n[14] Errors traces")
    et = get("/api/errors/traces")
    if et:
        print(f"      traces count: {len(et.get('traces', []))}")

    # ── 15. Export ────────────────────────────────────────────
    print("\n[15] Export")
    exp = get_raw("/api/export")

    # ── Summary ───────────────────────────────────────────────
    total = passed + failed
    print("\n" + "=" * 60)
    print(f"TEST COMPLETE: {passed}/{total} passed, {failed}/{total} failed")
    print("=" * 60)

    sys.exit(1 if failed else 0)

