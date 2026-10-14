import pandas as pd
import random
import os

random.seed(42)
data = []

for _ in range(2000):
    vin = round(random.uniform(9, 15), 2)

    if random.random() < 0.7:
        vout = round(random.uniform(4.8, 5.2), 2)
        iout = round(random.uniform(0.1, 1.5), 2)
        status = "NORMAL"
    else:
        vout = round(random.choice([
            random.uniform(0, 3.5),
            random.uniform(5.8, 8.0)
        ]), 2)
        iout = round(random.uniform(0, 2.0), 2)
        status = "FAULTY"

    data.append([vin, vout, iout, status])

df = pd.DataFrame(data, columns=["Vin", "Vout", "Iout", "Status"])

output_path = os.path.join(
    os.path.dirname(__file__), "dataset", "lm2596_dataset.csv"
)

os.makedirs(os.path.dirname(output_path), exist_ok=True)
df.to_csv(output_path, index=False)

print("Dataset created successfully!")
print(df.head())
print(df["Status"].value_counts())
print("Saved to:", output_path)