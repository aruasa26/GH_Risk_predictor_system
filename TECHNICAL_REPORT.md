Gestational Hypertension Prediction System – Technical Report
Project Completion & Evaluation Report

Date: November 2025
Model: TabNet 

1. Executive Summary

This project successfully designed and deployed an end-to-end deep learning system for early prediction of Gestational Hypertension (GH). The system integrates clinical data from two distinct sources—Mendeley Data Repository and Kathmandu Model Hospital—to generate accurate risk predictions.

Using the TabNet architecture, the model achieved a Recall of ~90%, meeting the safety-first requirement of minimizing false negatives. The completed system includes:

A harmonized and fully cleaned data pipeline

A FastAPI inference engine

A React-based clinical dashboard

Automated ANC (Antenatal Care) scheduling for high-risk patients

2. Approach
2.1 Data Preprocessing & Harmonization
Datasets Used

Mendeley Dataset: Acute physiological vitals (SBP, DBP, Heart Rate)

Kathmandu Dataset: Longitudinal obstetric history (Gravida, Parity, GH history)

Harmonization Steps

Schema Alignment

Standardized variable names (e.g., systolic_bp and SBP → Systolic BP)

Feature Selection

Identified 19 essential clinical features common across both datasets

Cleaning

Median imputation for numerical features

Mode imputation for categorical features

Encoding

Applied Label Encoding (e.g., Low = 0, High = 1)

Imbalance Handling

High-risk cases ≈ 18%

Applied SMOTE-NC to increase minority samples

Final Dataset

~10,000 samples

19 input features

Stratified split: Train 80%, Test 20%

2.2 Model Architecture

Model: TabNet

Why TabNet?

Traditional MLPs struggle on tabular health data

TabNet provides:

Sequential attention

Sparse masks for important clinical features

Built-in interpretability


Training Configuration

Optimizer: Adam (lr = 0.02)

Loss: Weighted Cross-Entropy (penalizes missed high-risk cases)

Batch Size: 1024 (Virtual batch: 128)

Epochs: 200

Early Stopping: patience = 85

2.3 Evaluation Metrics

Because this is a medical classification task, priority was given to:

Recall (Sensitivity) 

AUC-ROC – model separability

F1-Score – balance between recall and precision

AUC-ROC – model separability

3. Results Summary
3.1 Model Performance (Test Set)
Metric	TabNet	Logistic Regression	Winner
Recall	0.94	0.65	TabNet
F1-Score	0.85	0.58	TabNet
Accuracy	0.94	0.82	TabNet
AUC-ROC	0.896	0.85	TabNet
3.2 Key Clinical Findings

Top Features Identified by TabNet Masks

Systolic BP

Diastolic BP

History of GH

Safety Margin

Correctly flagged 9 out of 10 high-risk patients


4. Challenges Faced
4.1 Data-Related Challenges

Class Imbalance: High-risk ≈ 18%

4.2 Model-Related Challenges

Overfitting: Controlled using early stopping

Interpretability: TabNet masks as “Reasoning” on dashboard

5. API Design & Deployment
5.1 Production API Specification

Endpoint:
POST /predict

Request Body (JSON):

{
  "age": 32,
  "systolic_bp": 145,
  "diastolic_bp": 92,
  "bmi": 28.5,
  "gh_history": 1,
  "parity": 2
}


Response Body:

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

6.2 Logic Flow

Clinician submits patient data via React Dashboard

FastAPI:

Validates schema

Runs preprocessing

Calls TabNet inference

Decision Layer processes risk threshold

Save prediction to PostgreSQL

Dashboard displays High/Low Risk and reasoning

7. Conclusion

The project successfully delivered a complete Gestational Hypertension Prediction System with:

High predictive performance

Clinical-grade recall

Built-in interpretability via TabNet

A full-stack pipeline (React + FastAPI + PostgreSQL)

ANC scheduling for actionable care