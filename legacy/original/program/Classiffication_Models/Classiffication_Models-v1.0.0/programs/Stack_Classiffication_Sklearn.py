import numpy as np
import pandas as pd

from sklearn.inspection import permutation_importance
from sklearn.metrics import accuracy_score,classification_report, confusion_matrix, precision_recall_fscore_support
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.ensemble import StackingClassifier

def stack(file,test_size=0.3,estimators=[(('mlp',MLPClassifier(hidden_layer_sizes=(60,30),activation='tanh')),
    ('stack', KNeighborsClassifier(n_neighbors=3)))],
    final_estimator=MLPClassifier(hidden_layer_sizes=(60,30),activation='tanh')):
    """
    ## file:
    path of the file
    
    ## test_size:
    a float in the range [0.0, inf)

    ## estimators:
    Sequence[tuple[str, BaseEstimator]

    ## final_estimator
    BaseEstimator

    """ 
    file = file
    test_size=test_size
    estimators=estimators
    final_estimator=final_estimator           
    # extract the data in each column of the dataframe, and stores it as separate lists
    df = pd.read_excel(file)
    f1 = df.iloc[:, 0].tolist()
    f2 = df.iloc[:, 1].tolist()
    f3 = df.iloc[:, 2].tolist()
    f4 = df.iloc[:, 3].tolist()
    f5 = df.iloc[:, 4].tolist()
    f6 = df.iloc[:, 5].tolist()
    f7 = df.iloc[:, 6].tolist()
    f8 = df.iloc[:, 7].tolist()
    f9 = df.iloc[:, 8].tolist()
    f10 = df.iloc[:, 9].tolist()
    f11 = df.iloc[:, 10].tolist()
    f12 = df.iloc[:, 11].tolist()
    f13 = df.iloc[:, 12].tolist()
    f14 = df.iloc[:, 13].tolist()
    f15 = df.iloc[:, 14].tolist()
    f16 = df.iloc[:, 15].tolist()
    f17 = df.iloc[:, 16].tolist()
    f18 = df.iloc[:, 17].tolist()
    f19 = df.iloc[:, 18].tolist()
    f20 = df.iloc[:, 19].tolist()
    f21 = df.iloc[:, 20].tolist()
    f22 = df.iloc[:, 21].tolist()
    f23 = df.iloc[:, 22].tolist()
    f24 = df.iloc[:, 23].tolist()
    f25 = df.iloc[:, 24].tolist()
    f26 = df.iloc[:, 25].tolist()
    f27 = df.iloc[:, 26].tolist()
    f28 = df.iloc[:, 27].tolist()
    f29 = df.iloc[:, 28].tolist()
    f30 = df.iloc[:, 29].tolist()
    f31 = df.iloc[:, 30].tolist()
    f32 = df.iloc[:, 31].tolist()
    f33 = df.iloc[:, 32].tolist()
    f34 = df.iloc[:, 33].tolist()
    f35 = df.iloc[:, 34].tolist()
    f36 = df.iloc[:, 35].tolist()
    f37 = df.iloc[:, 36].tolist()
    f38 = df.iloc[:, 37].tolist()


    labels = df.iloc[:, 38].tolist()

    # Concatenate feature columns into a numpy array
 
    X = np.c_[f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13,f14,f15,f16,f17,f18,f19,f20,f21,f22,f23,f24,f25,f26,
              f27,f28,f29,f30,f31,f32,f33,f34,f35,f36,f37,f38]
  
    
    # Convert the labels column into a numpy array
    y = np.c_[labels]
    def preprocess(X, y):
        """
        Preprocess the data
        """
        # Randomly shuffles the data
        m = len(X)
        np.random.seed(1846)
        order = np.random.permutation(m)
        X = X[order]
        y = y[order]

        # Normalize the feature
        X_min = np.min(X)
        X_max = np.max(X)
        X = (X - X_min)/(X_max - X_min)

        return X, y

    X,y = preprocess(X, y)

    # Split the dataset into training and testing data
    train_X, test_X, train_y, test_y = train_test_split(X, y, test_size=test_size, random_state=1846)

    # ---------------------------The above are data preprocessing operations-------------------------------------------
    # print parameters
    print('Stack_Classiffication_Sklearn','\nFileName:',file,'\nRunning the stack models with parameters:','\nEstimators:',estimators,
        '\nFinal_estimator:',final_estimator)
    
    # Create and train the model
    stack = StackingClassifier(estimators=estimators,final_estimator=final_estimator,n_jobs=-1)
    stack.fit(train_X,train_y.ravel())
  
    # Compute feature importance using Permutation Improtance method
    result = permutation_importance(stack, X, y, n_repeats=10, random_state=1624)
    
    # Print accuracy
    print('Training accuracy =',stack.score(train_X,train_y))
    print('Testing accuracy =',stack.score(test_X,test_y))

    # Calculate and output the confusion matrix and classification report for the training and testing sets separately
    print('Training confusion matrix:\n',confusion_matrix(train_y,stack.predict(train_X)))
    print('Testing confusion matrix:\n',confusion_matrix(test_y,stack.predict(test_X)))
    print('Training classification report:\n',classification_report(train_y,stack.predict(train_X),))
    print('Testing classification report:\n',classification_report(test_y,stack.predict(test_X)))

    # Sort features by importance score
    importance_scores = result.importances_mean
    features = range(X.shape[1])
    sorted_features = [x for _,x in sorted(zip(importance_scores, features), reverse=True)]

    # Print sorted features by importance score
    ranks = []
    for i, feature in enumerate(sorted_features):
        #print(f"Rank {i+1}: Feature {feature + 1} with importance score {importance_scores[feature]}")
        ranks.append(f"f{feature + 1},{importance_scores[feature]}")
    # Calculate and save the scores of train and test in mlp_result as a DataFrame
    train_pred_y = stack.predict(train_X)
    train_accuracy = accuracy_score(train_y,train_pred_y)
    train_precision, train_recall, train_f1_score, train_support = precision_recall_fscore_support(train_y,train_pred_y,average='weighted')
    train_support = len(train_y)
    test_pred_y = stack.predict(test_X)
    test_accuracy = accuracy_score(test_y,test_pred_y)
    test_precision, test_recall, test_f1_score, test_support = precision_recall_fscore_support(test_y,test_pred_y,average='weighted')
    test_support = len(test_y)
    stack_result = pd.DataFrame({'Test_size':[test_size],'Estimators':[estimators],
                                 'Final_estimator':[final_estimator],
                                'TrainAccuracy':[train_accuracy],
                                'TrainPrecision':[train_precision],
                                'TrainRecall':[train_recall],
                                'TrainF1Score':[train_f1_score],
                                'TrainSupport':[train_support],
                                'TestAccuracy':[test_accuracy],
                                'TestPrecision':[test_precision],
                                'TestRecall':[test_recall],
                                'TestF1Score':[test_f1_score],
                                'TestSupport':[test_support],
                                'Rank1ImportanceScore':[ranks[0]],
                                'Rank2ImportanceScore':[ranks[1]],
                                'Rank3ImportanceScore':[ranks[2]],
                                'Rank4ImportanceScore':[ranks[3]],
                                'Rank5ImportanceScore':[ranks[4]],
                                'Rank6ImportanceScore':[ranks[5]],
                                'Rank7ImportanceScore':[ranks[6]],
                                'Rank8ImportanceScore':[ranks[7]],
                                'Rank9ImportanceScore':[ranks[8]],
                                'Rank10ImportanceScore':[ranks[9]],
                                'Rank11ImportanceScore':[ranks[10]],
                                'Rank12ImportanceScore':[ranks[11]],
                                'Rank13ImportanceScore':[ranks[12]],
                                'Rank14ImportanceScore':[ranks[13]],
                                'Rank15ImportanceScore':[ranks[14]],
                                'Rank16ImportanceScore':[ranks[15]],
                                'Rank17ImportanceScore':[ranks[16]],
                                'Rank18ImportanceScore':[ranks[17]],
                                'Rank19ImportanceScore':[ranks[18]],
                                'Rank20ImportanceScore':[ranks[19]],
                                'Rank21ImportanceScore':[ranks[20]],
                                'Rank22ImportanceScore':[ranks[21]],
                                'Rank23ImportanceScore':[ranks[22]],
                                'Rank24ImportanceScore':[ranks[23]],
                                'Rank25ImportanceScore':[ranks[24]],
                                'Rank26ImportanceScore':[ranks[25]],
                                'Rank27ImportanceScore':[ranks[26]],
                                'Rank28ImportanceScore':[ranks[27]],
                                'Rank29ImportanceScore':[ranks[28]],
                                'Rank30ImportanceScore':[ranks[29]],
                                'Rank31ImportanceScore':[ranks[30]],
                                'Rank32ImportanceScore':[ranks[31]],
                                'Rank33ImportanceScore':[ranks[32]],
                                'Rank34ImportanceScore':[ranks[33]],
                                'Rank35ImportanceScore':[ranks[34]],
                                'Rank36ImportanceScore':[ranks[35]],
                                'Rank37ImportanceScore':[ranks[36]],
                                'Rank38ImportanceScore':[ranks[37]],
                                })
    return stack_result