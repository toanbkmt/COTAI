# -*- coding: utf-8 -*-
"""Home Credit Default Risk.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1AINDam9ipV-byA1fVJ8h08pJBeHk6Zkc
"""

from google.colab import drive
drive.mount("/content/drive")

import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn import metrics
from sklearn.metrics import f1_score, roc_auc_score
import tensorflow as tf

from sklearn.model_selection import GridSearchCV

from imblearn.pipeline import make_pipeline as make_pipeline_imb
from imblearn.over_sampling import SMOTE
from imblearn.metrics import classification_report_imbalanced
import xgboost as xgb
from xgboost import XGBClassifier

application = pd.read_csv("/content/drive/My Drive/hoc bai/Home Credit/application_train.csv")
# bureau = pd.read_csv("/content/drive/My Drive/hoc bai/Home Credit/bureau.csv")
# bureau_balance = pd.read_csv("/content/drive/My Drive/hoc bai/Home Credit/bureau_balance.csv")
# credit_card_balance = pd.read_csv("/content/drive/My Drive/hoc bai/Home Credit/credit_card_balance.csv")
# instalments_payment = pd.read_csv("/content/drive/My Drive/hoc bai/Home Credit/installments_payments.csv")
# previous_application = pd.read_csv("/content/drive/My Drive/hoc bai/Home Credit/previous_application.csv")

def one_hot(data):
  categorical_feats = [
      f for f in data.columns if data[f].dtype == 'object'
  ]
  categorical_feats
  for f_ in categorical_feats:
      data[f_] = pd.get_dummies(data[f_])
  return data, categorical_feats

def get_feature_importances(data, shuffle, seed=None):
    _ , categorical_feats = one_hot(data)
    # Gather real features
    train_features = [f for f in data if f not in ['TARGET', 'SK_ID_CURR']]
    # Go over fold and keep track of CV score (train and valid) and feature importances
    
    # Shuffle target if required
    y = data['TARGET'].copy()
    if shuffle:
        # Here you could as well use a binomial distribution
        y = data['TARGET'].copy().sample(frac=1.0)
    
    # Fit LightGBM in RF mode, yes it's quicker than sklearn RandomForest
    dtrain = lgb.Dataset(data[train_features], y, free_raw_data=False, silent=True)
    lgb_params = {
        'objective': 'binary',
        'boosting_type': 'rf',
        'subsample': 0.623,
        'colsample_bytree': 0.7,
        'num_leaves': 127,
        'max_depth': 8,
        'seed': seed,
        'bagging_freq': 1,
        'n_jobs': 4
    }
    
    # Fit the model
    clf = lgb.train(params=lgb_params, train_set=dtrain, num_boost_round=200, categorical_feature=categorical_feats)

    # Get feature importances
    imp_df = pd.DataFrame()
    imp_df["feature"] = list(train_features)
    imp_df["importance_gain"] = clf.feature_importance(importance_type='gain')
    imp_df["importance_split"] = clf.feature_importance(importance_type='split')
    imp_df['trn_score'] = roc_auc_score(y, clf.predict(data[train_features]))
    
    return imp_df

application_importance = get_feature_importances(application,1,seed=None)
# bureau_importance = get_feature_importances(bureau,1,seed=None)
# bureau_importance = get_feature_importances(bureau_balance,1,seed=None)
# creditcard_balance_importance = get_feature_importances(credit_card_balance,1,seed=None)
# instalment_payment_importance = get_feature_importances(instalments_payment,1,seed=None)
# data_previous_application = get_feature_importances(previous_application,1,seed=None)

display(application_importance)

def remove_no_use(df,importance,epsilon):
  no_use = []
  #Listing no_use columns
  print("No of columns before dropping:",df.shape[1])
  for i in range(len(importance)):
    if importance["importance_gain"][i] < epsilon*np.mean(importance["importance_gain"],axis = 0):
      no_use.append(importance['feature'][i])
  print(no_use)
  #Dropping them!
  for i in no_use:
    df = df.drop(columns = i, axis = 1)
    print(i," dropped, ", df.shape[1], " cols remaining")
  print("No of columns after dropping:",df.shape[1])
  return df

#DATA PROCESSING
#1 - REMOVE NO USE COLUMNS
test = application
droppedapplication = remove_no_use(test, application_importance,0.8)
droppedapplication.shape

def prepare_dataset(data):
  y = data['TARGET']
  X = data.drop(columns = 'TARGET', axis = 1)
  #Train-test split
  X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.30, random_state=0)
  #Train-validation split
  X_train, X_valid, y_train, y_valid = train_test_split(X_train, y_train, test_size=0.30, random_state=0)
  return X_train, X_test, X_valid, y_train, y_test, y_valid

X_train, X_test, X_valid, y_train, y_test, y_valid = prepare_dataset(droppedapplication)

def xgb_classifier(X_train, X_test, y_train, y_test, useTrainCV=True, cv_folds=5, early_stopping_rounds=50):
  alg = XGBClassifier(learning_rate=0.1, n_estimators=140, max_depth=5,
                        min_child_weight=3, gamma=0.2, subsample=0.6, colsample_bytree=1.0,
                        objective='binary:logistic', nthread=4, scale_pos_weight=1, seed=27)
  if useTrainCV:
        print("Start Feeding Data")
        xgb_param = alg.get_xgb_params()
        xgtrain = xgb.DMatrix(X_train.values, label=y_train.values)
        cvresult = xgb.cv(xgb_param, xgtrain, num_boost_round=alg.get_params()['n_estimators'], nfold=cv_folds,
                          early_stopping_rounds=early_stopping_rounds)
        display(cvresult)
        alg.set_params(n_estimators=cvresult.shape[0])

    
  print('Start Training')
  alg.fit(X_train, y_train, eval_metric='auc')
  print("Start Predicting")
  predictions = alg.predict(X_test)
  pred_proba = alg.predict_proba(X_test)[:, 1]

    # Model performance
  print("\nModel statistic")
  print("Accuracy : %.4g" % metrics.accuracy_score(y_test, predictions))
  print("AUC score (test set): %f" % metrics.roc_auc_score(y_test, pred_proba))
  print("F1 Score (test set): %f" % metrics.f1_score(y_test, predictions))

  feat_imp = alg.feature_importances_
  feat = X_train.columns.tolist()
  res_df = pd.DataFrame({'Features': feat, 'Importance': feat_imp}).sort_values(by='Importance', ascending=False)
  res_df.plot('Features', 'Importance', kind='bar', title='Feature Importances')
  plt.ylabel('Feature Importance Score')
  plt.show()
  print(res_df)
  print(res_df["Features"].tolist())
  return cvresult, alg

cvresult, model_xgb = xgb_classifier(X_train, X_valid, y_train, y_valid, useTrainCV=True, cv_folds=5, early_stopping_rounds=50)

fig = plt.figure(figsize=(40 , 10))
ax1 = plt.subplot(1, 4, 1)
ax1.plot(cvresult.index, cvresult['train-error-mean'])
plt.title('train-error-mean')
ax2 = plt.subplot(1, 4, 2)
ax2.plot(cvresult.index, cvresult['train-error-std'])
plt.title('train-error-std')
ax3 = plt.subplot(1, 4, 3)
ax3.plot(cvresult.index, cvresult['test-error-mean'])
plt.title('test-error-mean')
ax4 = plt.subplot(1,4, 4)
ax4.plot(cvresult.index, cvresult['test-error-std'])
plt.title('test-error-std',)
plt.show()

from keras.layers import *
from keras.models import Model

application_mlp,_ = one_hot(application)

MLP_X_train, MLP_X_test, MLP_X_valid, MLP_y_train, MLP_y_test, MLP_y_valid = prepare_dataset(application_mlp)

input_layer = Input(shape=(121,)) 
emb_layer = Embedding(121,300)(input_layer) 
conv_layer = Conv1D(50,3, activation="tanh")(emb_layer)  
pool_layer = GlobalMaxPooling1D()(conv_layer)

hidden_dense_layer = Dense(50,activation="tanh")(pool_layer)
dense_layer = Dense(1,activation="sigmoid")(hidden_dense_layer)

model_mlp = Model(inputs=input_layer, outputs=dense_layer)
model_mlp.compile(loss='binary_crossentropy', optimizer="adam",metrics=["accuracy"])
print (model.summary())

model_mlp.fit(MLP_X_train,MLP_y_train,validation_data=(MLP_X_valid,MLP_y_valid), epochs= 5, batch_size=128)

#MODEL COMPARISON
#XGBOOST
xgb_predictions = model_xgb.predict_proba(X_test)[:, 1]
xgb_auc = roc_auc_score(y_test, xgb_predictions)

#MLP
mlp_predictions = model_mlp.predict(MLP_X_test)
mlp_auc = roc_auc_score(MLP_y_test,mlp_predictions)

print('XGB auc score %.3f' % (xgb_auc))
print('MLP auc score %.3f' % (mlp_auc))