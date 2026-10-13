import os
import joblib
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(
    BASE_DIR, "models", "random_forest_model.pkl"
)

model = joblib.load(MODEL_PATH)


def predict_status(vin, vout, iout):
    readings = pd.DataFrame(
        [[vin, vout, iout]],
        columns=["Vin", "Vout", "Iout"]
    )

    prediction = model.predict(readings)[0]
    probabilities = model.predict_proba(readings)[0]

    confidence = float(max(probabilities))

    return {
        "status": prediction,
        "confidence": round(confidence, 4),
        "readings": {
            "Vin": vin,
            "Vout": vout,
            "Iout": iout
        }
    }


if __name__ == "__main__":
    result = predict_status(12.0, 5.0, 0.5)
    print(result)