"""
Enterprise-тест: сбалансированное оценивание.
Новые фермеры не должны наказываться. Мусор должен получать низкий, но честный балл.
"""
import pandas as pd
from app.pipeline.model import ScoringModel
from app.pipeline.features import FeatureEngineer

model = ScoringModel()
fe = model.load('data/models/v_20260402_184022.pkl')

# Обратная совместимость
if not getattr(fe, '_known_categories', None):
    fe._known_categories = {}
    for col, le in model.label_encoders.items():
        fe._known_categories[col] = set(le.classes_)
if not getattr(fe, '_fill_q25', None):
    fe._fill_q25 = {}

known_vals = {}
for col, vals in fe._known_categories.items():
    if col in ['region', 'akimat', 'direction', 'subsidy_type', 'district']:
        known_vals[col] = list(vals)[0]


def score_one(label, data):
    df = pd.DataFrame([data])
    enriched = fe.transform(df, is_training=False)
    scored = model.score(enriched)
    r = scored.iloc[0]
    ur = enriched['unknown_ratio'].values[0]
    print(f'\n  {label}:')
    print(f'    unknown_ratio={ur:.2f}  confidence={r["confidence"]:.2f}  '
          f'data_quality={r["data_quality"]}  review={r["review_required"]}')
    print(f'    raw_proba={r["raw_probability"]:.4f}  score={r["score"]:.1f}  category={r["category"]}')
    return r


# ============================================================
print('=' * 60)
print('ENTERPRISE ТЕСТ: СПРАВЕДЛИВОЕ ОЦЕНИВАНИЕ')
print('=' * 60)

# 1. Полные данные — без дисконта
print('\n[1] ПОЛНЫЕ ДАННЫЕ (0 неизвестных)')
r1 = score_one('Все данные известны', {**known_vals, 'normative': 1000000, 'amount': 1000000})
assert r1['confidence'] == 1.0, 'Полные данные должны иметь confidence=1.0'
assert r1['data_quality'] == 'complete'
assert not r1['review_required']
print('  ✓ PASS')

# 2. Новый фермер (1 неизвестное поле) — должен получить справедливую оценку
print('\n[2] НОВЫЙ ФЕРМЕР (1 неизвестное поле — новый район)')
r2 = score_one('Новый район', {**known_vals, 'district': 'Новый Район', 'normative': 1000000, 'amount': 1000000})
assert r2['confidence'] == 0.9, f'1 unknown -> confidence=0.90, got {r2["confidence"]}'
assert r2['data_quality'] == 'high', f'Expected high, got {r2["data_quality"]}'
assert not r2['review_required'], '1 unknown field should NOT require review'
assert r2['score'] >= 50, f'New farmer with good data should not be LOW: score={r2["score"]}'
print('  ✓ PASS: Новый фермер оценён справедливо')

# 3. Новый регион + район (2 unknown) — review рекомендуется
print('\n[3] НОВЫЙ РЕГИОН + РАЙОН (2 неизвестных)')
r3 = score_one('Новый регион+район', {
    **known_vals, 'region': 'Новая Область', 'district': 'Новый Район',
    'normative': 1000000, 'amount': 1000000
})
assert r3['confidence'] == 0.8
assert r3['data_quality'] == 'medium'
assert r3['review_required'], '2+ unknown -> review recommended'
print('  ✓ PASS: Review рекомендован, но балл не уничтожен')

# 4. Много неизвестных (4/5)
print('\n[4] ПОЧТИ ВСЁ НЕИЗВЕСТНО (4 из 5 полей)')
r4 = score_one('4 неизвестных', {
    'region': 'test', 'akimat': 'test', 'direction': 'test',
    'subsidy_type': 'test', **{k: v for k, v in known_vals.items() if k == 'district'},
    'normative': 1000000, 'amount': 1000000,
})
assert r4['confidence'] == 0.6
assert r4['data_quality'] == 'low'
assert r4['review_required']
print('  ✓ PASS: Модель оценила, review обязателен')

# 5. Полный мусор (5/5)
print('\n[5] ПОЛНЫЙ МУСОР (5/5 полей неизвестны)')
r5 = score_one('Всё test', {
    'region': 'test', 'akimat': 'test', 'direction': 'test',
    'subsidy_type': 'test', 'district': 'test',
    'normative': 1000000, 'amount': 1000000,
})
assert r5['confidence'] == 0.5
assert r5['data_quality'] == 'low'
assert r5['review_required']
assert r5['category'] != 'HIGH', f'Garbage must not be HIGH: {r5["category"]}'
print('  ✓ PASS: Мусор не получает HIGH, review обязателен')

# 6. Сравнение
print('\n[6] СРАВНЕНИЕ')
print(f'  Новый фермер (1 unknown):  score={r2["score"]:.1f} ({r2["category"]})')
print(f'  Полный мусор (5 unknown):  score={r5["score"]:.1f} ({r5["category"]})')
assert r2['score'] > r5['score'], 'New farmer must score higher than garbage'
print('  ✓ PASS: Справедливая иерархия')

print('\n' + '=' * 60)
print('ALL ENTERPRISE TESTS PASSED ✓')
print('=' * 60)
