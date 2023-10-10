import json
import os
import pandas as pd

res = []
for file in os.listdir("../dataHAX/storage 2/"):

    with open("../dataHAX/storage 2/" + file) as f:
        data = json.load(f)
    res.append(data)

df = pd.DataFrame(res)
df.to_csv("../dataHAX/yes4x 28 sep 2023.csv", index=False)


