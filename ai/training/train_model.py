"""
Earth Sentinel
AI Model Training

Model:
    XGBoost Classifier
"""

from pathlib import Path
import json

import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score
)
from xgboost import XGBClassifier


DATASET = Path("data/processed/training_dataset.csv")
MODEL_DIR = Path("models")

MODEL_DIR.mkdir(parents=True, exist_ok=True)


FEATURES = [
    "elevation",
    "slope",
    "aspect",
    "rainfall_1h",
    "rainfall_3h",
    "rainfall_6h",
    "rainfall_24h",
    "rainfall_3d",
    "rainfall_7d",
    "soil_moisture",
    "historical_landslide_density"
]

TARGET = "label"


def main():

    if not DATASET.exists():
        print("Training dataset not found.")
        print()
        print(f"Expected: {DATASET}")
        print()
        print("We will create it before running model training.")
        return

    df = pd.read_csv(DATASET)

    missing = [
        feature
        for feature in FEATURES + [TARGET]
        if feature not in df.columns
    ]

    if missing:
        print("Missing required columns:")
        for column in missing:
            print(" -", column)
        return

    df = df.dropna(subset=FEATURES + [TARGET])

    X = df[FEATURES]
    y = df[TARGET]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y
    )

    model = XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        eval_metric="logloss"
    )

    print("Training XGBoost model...")

    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    probabilities = model.predict_proba(X_test)[:, 1]

    print()
    print("MODEL RESULTS")
    print("=" * 50)

    print(classification_report(y_test, predictions))

    print("Confusion Matrix:")
    print(confusion_matrix(y_test, predictions))

    try:
        print(
            "ROC-AUC:",
            roc_auc_score(y_test, probabilities)
        )
    except ValueError:
        print("ROC-AUC could not be calculated.")

    model_file = MODEL_DIR / "landslide_model.pkl"

    joblib.dump(model, model_file)

    features_file = MODEL_DIR / "features.json"

    with open(features_file, "w") as file:
        json.dump(FEATURES, file, indent=2)

    print()
    print("Model saved to:")
    print(model_file)

    print()
    print("Feature configuration saved to:")
    print(features_file)


if __name__ == "__main__":
    main()