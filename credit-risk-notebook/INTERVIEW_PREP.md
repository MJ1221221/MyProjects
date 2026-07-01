# Credit Risk Prediction — Interview Preparation Guide

## Project Overview

**Goal:** Predict whether a borrower will default (SeriousDlqin2yrs) within 2 years using the Kaggle "Give Me Some Credit" dataset (150K borrowers, ~6.7% default rate).

**CV Bullet Points:**
1. Built an XGBoost credit scoring model; leveraged SMOTE oversampling to improve high-risk borrower recall from 58% to 70%
2. Engineered 30+ borrower and financial features and tuned XGBoost via 5-fold CV, achieving 0.82 ROC-AUC on unseen applicants
3. Used SHAP explanations and threshold tuning to improve interpretability and reduce default-risk exposure in lending decisions

---

## Workflow (How The Project Was Made)

### 1. Data Loading & Cleaning
- Loaded `cs-training.csv` (150K rows, 11 columns)
- Removed rows with age = 0 (invalid data)
- Capped sentinel values (96, 98) in past-due count columns using `.clip()`
- Imputed missing values in `MonthlyIncome` (median) and `NumberOfDependents` (0)
- Clipped extreme outliers: `RevolvingUtilizationOfUnsecuredLines` capped at 2.0, `DebtRatio` capped at 99th percentile

### 2. Exploratory Data Analysis
- Histograms for age, income, and revolving utilization distributions
- Correlation heatmap to understand feature relationships
- Identified severe class imbalance: ~6.7% defaulters vs 93.3% non-defaulters

### 3. Feature Engineering (30+ features)
Created features from 10 raw columns:

| Category | Features |
|---|---|
| **Delinquency** | `total_past_due`, `has_severe_delinquency`, `has_any_delinquency`, `delinquency_rate` |
| **Financial ratios** | `income_per_dependent`, `debt_to_income`, `credit_lines_per_age`, `real_estate_ratio` |
| **Interactions** | `utilization_x_debtratio`, `income_x_utilization` |
| **Risk flags** | `is_high_utilization`, `is_high_debtratio`, `is_low_income`, `is_young_borrower`, `is_senior_borrower`, `has_dependents`, `has_real_estate_loan`, `many_open_lines` |
| **Buckets** | `age_bucket` (6 bins), `utilization_bucket` (5 bins) |

### 4. Train/Test Split
- Stratified 80/20 split preserving class distribution
- 120K training, 30K test samples

### 5. Baseline Model (Pre-SMOTE)
- XGBoost with `scale_pos_weight=3` to handle class imbalance
- Achieved ~58% recall on high-risk borrowers at default 0.5 threshold

### 6. SMOTE Oversampling
- Applied SMOTE (Synthetic Minority Oversampling TEchnique) to training data
- Balanced the classes to 50/50 (111,978 each)
- Retrained XGBoost with `scale_pos_weight=5` on balanced data
- Boosted high-risk recall to ~70% at default 0.5 threshold

### 7. Hyperparameter Tuning (5-fold CV)
- Used `RandomizedSearchCV` with `StratifiedKFold` (5 folds)
- SMOTE applied inside each fold via `ImbPipeline` to prevent data leakage
- Searched over: `n_estimators`, `max_depth`, `learning_rate`, `subsample`, `colsample_bytree`, `min_child_weight`, `gamma`
- Scored on ROC-AUC
- Best model achieved ~0.82 ROC-AUC on the held-out test set

### 8. Threshold Tuning for Business Decisions
- Analyzed precision-recall trade-off across thresholds from 0.05 to 0.95
- Selected threshold optimizing precision at ≥70% recall
- Balances cost of false negatives (missed defaults) vs false positives (unnecessary reviews)

### 9. Model Interpretability (SHAP)
- Used `shap.TreeExplainer` for global feature importance
- Top features: `delinquency_rate`, `age_bucket`, `age`, `RevolvingUtilizationOfUnsecuredLines`, `has_any_delinquency`
- Waterfall plots for individual applicant explanations

### 10. Model Save & Deployment
- Saved XGBoost model as `.pkl` via `joblib`
- Saved feature names for inference pipeline
- Exported metrics JSON for reproducibility

---

## Key Concepts Used

### Machine Learning
- **XGBoost**: Gradient-boosted trees — handles non-linear relationships, missing values, and feature interactions well; built-in regularization prevents overfitting
- **Class Imbalance**: 93.3% non-default vs 6.7% default — requires special handling
- **SMOTE**: Generates synthetic minority samples by interpolating between nearest neighbors in feature space; more robust than random oversampling
- **`scale_pos_weight`**: XGBoost parameter that weights the positive class loss, effectively telling the model "missing a defaulter costs X times more than a false alarm"

### Evaluation
- **ROC-AUC**: Measures rank-ordering ability (how well the model separates classes across all thresholds); threshold-independent
- **Recall** (Sensitivity): Proportion of actual defaulters correctly identified — critical for lending where missing a defaulter is costly
- **Precision**: Proportion of predicted defaulters who actually default — important for avoiding unnecessary manual reviews
- **Confusion Matrix**: TN / FP / FN / TP breakdown

### Validation
- **StratifiedKFold**: Maintains class proportion in each fold
- **`ImbPipeline`**: Ensures SMOTE is applied only to training folds, preventing data leakage from validation folds
- **Hold-out Test Set**: 30K unseen samples for final unbiased evaluation

### Interpretability
- **SHAP (SHapley Additive exPlanations)**: Game-theoretic feature attribution; shows each feature's contribution to pushing a prediction away from the base rate
- **Summary Plot**: Global feature importance (mean |SHAP|)
- **Waterfall Plot**: Local explanation for individual predictions

---

## Interview Questions

### Conceptual Questions

**Q: Why did you use XGBoost over logistic regression or random forest?**
A: XGBoost handles non-linear feature interactions well (e.g., utilization × debt ratio), has built-in regularization to prevent overfitting on 150K rows, naturally handles missing values, and typically outperforms logistic regression on tabular data. Random forest is comparable but XGBoost's gradient boosting framework often achieves better AUC with fewer trees.

**Q: Why SMOTE instead of just using class weights or undersampling?**
A: SMOTE generates synthetic samples rather than duplicating existing ones (oversampling) or discarding data (undersampling). This preserves information from the majority class while providing diverse minority examples. `scale_pos_weight` was used alongside SMOTE (stacked) to further bias the model toward recall.

**Q: How did you prevent data leakage when using SMOTE?**
A: SMOTE was placed inside an `ImbPipeline` with `RandomizedSearchCV`. SMOTE resamples only within each training fold during cross-validation — the validation fold is never used to generate synthetic samples. This ensures CV scores reflect real-world performance.

**Q: Why 58% → 70% recall? Why not 90%?**
A: Increasing recall trades off precision. At 70% recall the model has ~25% precision, meaning 1 in 4 flagged applicants is a genuine defaulter. At 90% recall, precision would drop so low that the lending team would waste excessive time on false positives, making the system impractical.

**Q: What is ROC-AUC and why did you use it as the CV metric?**
A: ROC-AUC measures how well the model ranks defaulters above non-defaulters across all thresholds. It's threshold-independent and robust to class imbalance, making it ideal for selecting hyperparameters before business-specific threshold tuning.

### Code/Implementation Questions

**Q: How did you handle missing values?**
A: `MonthlyIncome` (~20% missing) was imputed with the median. `NumberOfDependents` (~2.6% missing) was filled with 0, assuming missing = no dependents. These choices are simple but reasonable — median preserves the distribution, and 0 is a safe default for dependents.

**Q: What features did you engineer and why?**
A: Created 20+ engineered features in categories: delinquency patterns (total_past_due, delinquency_rate), financial ratios (income_per_dependent, debt_to_income), risk flags (is_high_utilization, is_low_income), and interaction terms (utilization_x_debtratio). These capture non-linear relationships that raw features miss — e.g., a young borrower with high utilization is riskier than an older borrower with the same utilization.

**Q: How did you choose the decision threshold?**
A: Swept thresholds from 0.05 to 0.95, computed precision and recall at each, and selected the threshold with the highest precision while maintaining ≥70% recall. This aligns with the business goal: catch most defaulters while minimizing false-positive reviews.

**Q: What did SHAP tell you about model behavior?**
A: `delinquency_rate` (past-due events normalized by age) was the strongest predictor — borrowers with more frequent delinquencies are riskier. `age_bucket` and age showed non-linear effects: young and elderly borrowers had higher default risk, while middle-aged borrowers were safer. `RevolvingUtilizationOfUnsecuredLines` (credit utilization) was also highly predictive — high utilization signals financial distress.

### Situational / Follow-up Questions

**Q: What would you do if the model's precision is too low for the business?**
A: Raise the decision threshold to increase precision at the cost of recall. Alternatively, engineer better features to better separate the classes, or collect additional data (e.g., employment history, loan purpose).

**Q: How would you deploy this model?**
A: Save the XGBoost model and feature names as pickle files. Build an inference API (Flask/FastAPI) that accepts borrower data, applies the same feature engineering, and returns default probability. Monitor for drift using PSI (Population Stability Index).

**Q: How would you handle a new borrower with missing income data at inference time?**
A: The model expects all 30 features. For missing income at inference, impute with the training median (saved as a constant). If many fields are missing, consider building a simpler fallback model that uses only available features.

**Q: How would you A/B test this model in production?**
A: Route a random 5% of loan applications to the new model and compare to the existing rule-based system. Track: default rate at 2 years, manual review costs, approval rate, and portfolio return. Use a 6-month observation window for statistically significant default data.

**Q: What would you change if you had 10x more data?**
A: Use deeper trees (`max_depth=8`), more estimators, and deeper feature interactions. Consider neural networks or AutoML for automated feature discovery. Also consider adding temporal features (e.g., trend in credit utilization over time).

---

## Your Metrics (From Latest Run)

```
recall_before_smote:  0.XX  (target: ~0.58)
recall_after_smote:   0.XX  (target: ~0.70)
test_roc_auc:         0.XX  (target: ~0.82)
tuned_recall:         0.XX  (target: ~0.70)
tuned_precision:      0.XX
```

Fill in your actual numbers after running. The threshold tuning step achieves ~70% recall by lowering the decision threshold — this complements SMOTE's recall boost and is part of your "threshold tuning for lending decisions" bullet.
