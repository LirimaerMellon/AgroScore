import pandas as pd
import logging

logger = logging.getLogger(__name__)


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    initial_rows = len(df)

    df = df.dropna(how='all')

    if 'request_number' not in df.columns:
        raise ValueError("Не найден столбец: request_number")

    df = df.dropna(subset=['request_number'])

    df = df.drop_duplicates()

    if 'submission_date' in df.columns:
        df['submission_date'] = pd.to_datetime(df['submission_date'], errors='coerce')

    numeric_cols = ['amount', 'normative']

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            df[col] = df[col].fillna(0)
            df[col] = df[col].clip(lower=0)

    text_cols = [
        'region',
        'akimat',
        'direction',
        'subsidy_type',
        'status',
        'district'
    ]

    for col in text_cols:
        if col in df.columns:
            df[col] = (
                df[col]
                .fillna('Unknown')
                .astype(str)
                .str.strip()
                .replace('nan', 'Unknown')
            )

    if 'amount' in df.columns:
        df = df[df['amount'] > 0]

    if 'submission_date' in df.columns:
        df = df[df['submission_date'].notna()]

    removed = initial_rows - len(df)
    logger.info(f"Чистка завершена: {len(df):,} строк (удалено: {removed:,})")

    return df

def encode_status(status_value: str) -> int:
    status_lower = str(status_value).lower().strip()

    approved_statuses = [
        'исполнена',
        'одобрена'
    ]

    rejected_statuses = [
        'отклонена',
        'отозвано'
    ]

    if status_lower in approved_statuses:
        return 1

    if status_lower in rejected_statuses:
        return 0

    return -1

def add_target_variable(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    if 'status' not in df.columns:
        raise ValueError("Не найден столбец: status")

    df['status'] = (
        df['status']
        .astype(str)
        .str.lower()
        .str.strip()
    )

    final_statuses = [
        'исполнена',
        'одобрена',
        'отклонена',
        'отозвано'
    ]

    df = df[df['status'].isin(final_statuses)]

    df['is_approved'] = df['status'].apply(encode_status)

    before = len(df)
    df = df[df['is_approved'] != -1]

    approved = (df['is_approved'] == 1).sum()
    rejected = (df['is_approved'] == 0).sum()
    removed_unknown = before - len(df)

    logger.info("Заявки:")
    logger.info(f"  Одобрено: {approved:,}")
    logger.info(f"  Отклонено: {rejected:,}")
    logger.info(f"  Удалены: {removed_unknown:,}")

    return df