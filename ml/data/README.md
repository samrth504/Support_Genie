# Dataset (not included in this repo)

The CSV files are kept out of Git. To reproduce training, download them yourself:

1. Download `Bitext_Sample_Customer_Support_Training_Dataset_27K_responses-v11.csv` from
   https://huggingface.co/datasets/bitext/Bitext-customer-support-llm-chatbot-training-dataset
   (Files and versions tab, ~19 MB).
2. Save it here as **`ml/data/bitext.csv`**.
3. Run the notebook `ml/notebooks/01_eda.ipynb`. It writes **`ml/data/bitext_clean.csv`**
   (columns `text`, `category`, `intent`; duplicates and empty rows removed, 23,990 rows).
4. Train: `python ml/train.py`

You do NOT need the dataset to run the app: the trained model is already in
`backend/ml_models/classifier.joblib`.

**Source:** Bitext - Customer Service Tagged Training Dataset for LLM-based Virtual Assistants,
(c) Bitext Innovations, licensed under CDLA-Sharing-1.0 (https://cdla.dev/sharing-1-0/).
