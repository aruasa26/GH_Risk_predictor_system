# Gestational Hypertension Risk Prediction System – Technical Report
**Project Completion & Evaluation Report**  
**Date:** November 2025  
**Model:** TabNet 

---

## 1. Executive Summary

This project was successfully designed and developed as an end-to-end deep learning system for early prediction of Gestational Hypertension (GH) risk. The system integrates clinical data from two distinct sources—Mendeley Data Repository and Kathmandu Hospital—to generate accurate risk predictions.

Using the TabNet architecture, the model achieved a **Recall of ~90%**, meeting the safety-first requirement of minimizing false negatives. The completed system includes:

- A harmonized and fully cleaned data pipeline  
- A FastAPI inference engine  
- A React-based clinical dashboard  
- ANC(Antenatal Care) visits scheduling for patients  

---

## 2. Approach

### 2.1 Data Preprocessing & Harmonization

**Datasets Used:**

- Mendeley Dataset
- Kathmandu Dataset- Case study of about 300 patients  

**Harmonization Steps:**

#### Schema Alignment
- Standardized variable names (e.g., `systolic_bp` and `SBP` → `Systolic BP`)  

#### Features
- Identified **19 essential clinical features** common across both datasets  

#### Cleaning
- Median imputation for numerical features  
- Mode imputation for categorical features  

#### Encoding
- Applied **Label Encoding** (e.g., Low = 0, High = 1)  

#### Imbalance Handling
- High-risk cases ≈ 18% of data  
- Applied **SMOTE-NC** to generate balanced training samples  

**Final Dataset:**

- ~10,000 samples  
- 19 input features  
- Stratified split: Train 80%, Test 20%  

---

### 2.2 Model Architecture

**Model:** TabNet  

**Why TabNet?**  

Traditional MLPs struggle on tabular health data. TabNet provides:  

- Sequential attention mechanism  
- Sparse masks for critical clinical features  
- Built-in interpretability  

**Architecture Components:**

- **Feature Transformer:** Learns deep feature representations  
- **Attentive Transformer:** Generates sparsemask to select critical inputs, used 9 out of the 19
- **Sparse Masking:** Only a subset of features is used at each decision step.
  
**Training Configuration:**

- **Optimizer:** Adam (lr = 0.02)  
- **Loss:** Weighted Cross-Entropy (penalizes missed high-risk cases)  
- **Batch Size:** 1024 (Virtual batch: 128)  

---

### 2.3 Evaluation Metrics

Priority metrics for this medical classification task:

- **Recall (Sensitivity)** – critical to capture high-risk GH cases  
- **F1-Score** – balance between recall and precision  
- **AUC-ROC** – measures model separability  

---

## 3. Results Summary

### 3.1 Model Performance (Test Set)

| Metric      |Results | 
|-------------|--------|
| Recall      | 0.90   | 
| F1-Score    | 0.81   | 
| Precision   | 0.73   |
| AUC-ROC     | 0.896  | 

### 3.2 Key Clinical Findings

**Top Features Identified by TabNet Masks:**  

- Systolic BP  
- Diastolic BP  
- History of GH  

**Safety Margin:**  
- Correctly flagged 9 out of 10 high-risk patients  

---

## 4. Challenges Faced

### 4.1 Data-Related Challenges
- **Class Imbalance:** High-risk cases ~18%  
  
### 4.2 Model-Related Challenges
- **Overfitting:** Controlled using early stopping 
- **Interpretability:** Clinicians required reasoning; TabNet had **“Reasoning”** on dashboard  

---

## 5. API Design & Deployment

### 5.1 Production API Specification

**Endpoint:** `POST /predict`

**Request Body (JSON):**

```json
{
  "age": 32,
  "systolic_bp": 145,
  "diastolic_bp": 92,
  "bmi": 28.5,
  "gh_history": 1,
  "parity": 2
}
```
### Response Body (JSON)
```json
{
  "risk_classification": "High Risk",
  "probability_score": 0.88,
  "clinical_action": "Schedule ANC",
  "reasoning": [
    "Systolic BP > 140",
    "History of GH detected"
  ],
  "timestamp": "2025-11-23T14:30:00Z"
}
```
## 5.2 Logic Flow

1. **Clinician submits patient data** via React Dashboard  
2. **FastAPI backend**:  
   - Validates JSON schema  
   - Runs preprocessing  
   - Calls TabNet for inference  
3. **Decision Layer**: Determines High/Low Risk based on probability threshold  
4. **Save prediction** to PostgreSQL  
5. **Dashboard updates** with High/Low Risk and reasoning  

## 6. Conclusion

The project successfully delivered a **Gestational Hypertension Risk Prediction System** with:  

- High predictive performance  
- Clinical-grade recall (~90%)  
- Built-in interpretability  
- Full-stack pipeline integration (**React + FastAPI + PostgreSQL**)  
- ANC visit scheduling for actionable patient care  
