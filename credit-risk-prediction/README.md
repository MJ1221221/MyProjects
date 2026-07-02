# Credit Risk Prediction (Jupyter Notebook version)

## Setup

1. Download `cs-training.csv` from Kaggle:
   https://www.kaggle.com/c/GiveMeSomeCredit/data
   (or `kaggle competitions download -c GiveMeSomeCredit`)
2. Place it at `data/cs-training.csv`
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Launch:
   ```bash
   jupyter notebook credit_risk_prediction.ipynb
   ```
5. Run all cells top to bottom.

## What's inside

One notebook, run top to bottom:
1. Load + inspect raw data
2. Clean known data issues (garbage sentinel values, missing income/dependents, outliers)
3. EDA (distributions, correlation heatmap)
4. Feature engineering (raw 10 columns -> 30+ modeling features)
5. Baseline XGBoost -> pre-SMOTE recall
6. SMOTE oversampling -> post-SMOTE recall
7. 5-fold CV hyperparameter search (RandomizedSearchCV, scored on ROC-AUC)
8. Test-set evaluation (ROC-AUC, ROC curve)
9. Threshold tuning (recall/precision trade-off plot, target recall = 0.70)
10. SHAP global + local interpretability plots
11. Save model + `outputs/metrics.json`

Outputs land in `models/` (trained model) and `outputs/` (metrics.json).
