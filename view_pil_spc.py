from datasets import load_dataset

ds = load_dataset("multilingual-medical-kg/pil-spc")
print(ds["train"][0]["name"])   # e.g. "celsentri"
print(ds["train"][0]["en"][:500])
print(ds["train"][0]["sk"][:500])
