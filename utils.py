import wfdb
import pywt
import seaborn
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix
from sklearn.model_selection import train_test_split

# wavelet denoise preprocess using mallat algorithm
# def denoise(data):
#     # wavelet decomposition
#     coeffs = pywt.wavedec(data=data, wavelet='db5', level=9)
#     cA9, cD9, cD8, cD7, cD6, cD5, cD4, cD3, cD2, cD1 = coeffs

#     # denoise using soft threshold
#     threshold = (np.median(np.abs(cD1)) / 0.6745) * (np.sqrt(2 * np.log(len(cD1))))
#     cD1.fill(0)
#     cD2.fill(0)
#     for i in range(1, len(coeffs) - 2):
#         coeffs[i] = pywt.threshold(coeffs[i], threshold)

#     # get the denoised signal by inverse wavelet transform
#     rdata = pywt.waverec(coeffs=coeffs, wavelet='db5')
#     return rdata

# from scipy.signal import savgol_filter

# def savgol_denoise(data, window_length=11, polyorder=5):
#     """
#     Denoise ECG signal using Savitzky-Golay filter.
    
#     Args:
#         data (array): Input ECG signal.
#         window_length (int): Length of the filter window (odd integer).
#         polyorder (int): Order of the polynomial used to fit the samples.
    
#     Returns:
#         array: Denoised ECG signal.
#     """
#     denoised_data = savgol_filter(data, window_length, polyorder)
#     return denoised_data

# from PyEMD import EMD
# # from pyemd import emd
# import numpy as np

# def denoise_emd(data, num_imfs=10):
#     """
#     Denoise ECG signal using Empirical Mode Decomposition (EMD).
    
#     Args:
#         data (array): Input ECG signal.
#         num_imfs (int): Number of IMFs to extract (default: 10).
    
#     Returns:
#         array: Denoised ECG signal.
#     """
#     # Perform EMD
#     emd = EMD()
#     imfs = emd.emd(data, num_imfs=num_imfs)
    
#     # Reconstruct the denoised signal
#     denoised_data = np.sum(imfs[-3:], axis=0)
    
#     return denoised_data

def kalman_filter_step(z, x_est_prev, P_prev, Q, R):
    """Perform a single step of the Kalman filter."""
    x_pred = x_est_prev
    P_pred = P_prev + Q

    K = P_pred / (P_pred + R)
    x_est = x_pred + K * (z - x_pred)
    P_est = (1 - K) * P_pred

    return x_est, P_est

def hierarchical_kalman_filter(ecg_signal, Q1, R1, Q2, R2):
    """Apply a two-level hierarchical Kalman filter for denoising ECG signals."""
    n = len(ecg_signal)
    x_est1 = np.zeros(n)
    P1 = np.full(n, 1.0)
    x_est2 = np.zeros(n)
    P2 = np.full(n, 1.0)

    x_est1[0], x_est2[0] = ecg_signal[0], ecg_signal[0]

    for i in range(1, n):
        x_est1[i], P1[i] = kalman_filter_step(ecg_signal[i], x_est1[i-1], P1[i-1], Q1, R1)
        x_est2[i], P2[i] = kalman_filter_step(x_est1[i], x_est2[i-1], P2[i-1], Q2, R2)

    return x_est2

# load the ecg data and the corresponding labels, then denoise the data using wavelet transform
# def get_data_set(number, X_data, Y_data):
#     ecgClassSet = ['N', 'A', 'V', 'L', 'R']

#     # load the ecg data record
#     print("loading the ecg data of No." + number)
#     record = wfdb.rdrecord('ecg_data/' + number, channel_names=['MLII'])
#     data = record.p_signal.flatten()
#     # rdata = denoise(data=data)
#     # rdata = denoise_emd(data)
#     rdata= savgol_denoise(data)

#     # get the positions of R-wave and the corresponding labels
#     annotation = wfdb.rdann('ecg_data/' + number, 'atr')
#     Rlocation = annotation.sample
#     Rclass = annotation.symbol

#     # remove the unstable data at the beginning and the end
#     start = 10
#     end = 5
#     i = start
#     j = len(annotation.symbol) - end

#     # the data with specific labels (N/A/V/L/R) required in this record are selected, and the others are discarded
#     # X_data: data points of length 300 around the R-wave
#     # Y_data: convert N/A/V/L/R to 0/1/2/3/4 in order
#     while i < j:
#         try:
#             lable = ecgClassSet.index(Rclass[i])
#             x_train = rdata[Rlocation[i] - 99:Rlocation[i] + 201]
#             X_data.append(x_train)
#             Y_data.append(lable)
#             i += 1
#         except ValueError:
#             i += 1
#     return

def get_data_set(number, X_data, Y_data):
    ecgClassSet = ['N', 'A', 'V', 'L', 'R']
    print("loading the ecg data of No." + number)
    record = wfdb.rdrecord('ecg_data/' + number, channel_names=['MLII'])
    data = record.p_signal.flatten()

    # Apply HKF denoising
    Q1, R1 = 0.001, 10  # Process and measurement noise covariances for the first level
    Q2, R2 = 0.001, 1   # Process and measurement noise covariances for the second level
    rdata = hierarchical_kalman_filter(data, Q1, R1, Q2, R2)

    annotation = wfdb.rdann('ecg_data/' + number, 'atr')
    Rlocation = annotation.sample
    Rclass = annotation.symbol

    start = 10
    end = 5
    i = start
    j = len(annotation.symbol) - end

    while i < j:
        try:
            label = ecgClassSet.index(Rclass[i])
            x_train = rdata[Rlocation[i] - 99:Rlocation[i] + 201]
            if len(x_train) == 300:  # Ensure the segment length is correct
                X_data.append(x_train)
                Y_data.append(label)
            i += 1
        except ValueError:
            i += 1
    return

# load dataset and preprocess
def load_data(ratio, random_seed):
    numberSet = ['100', '101', '103', '105', '106', '107', '108', '109', '111', '112', '113', '114', '115',
                 '116', '117', '119', '121', '122', '123', '124', '200', '201', '202', '203', '205', '208',
                 '210', '212', '213', '214', '215', '217', '219', '220', '221', '222', '223', '228', '230',
                 '231', '232', '233', '234']
    dataSet = []
    lableSet = []
    for n in numberSet:
        get_data_set(n, dataSet, lableSet)

    # reshape the data and split the dataset
    dataSet = np.array(dataSet).reshape(-1, 300)
    lableSet = np.array(lableSet).reshape(-1)
    X_train, X_test, y_train, y_test = train_test_split(dataSet, lableSet, test_size=ratio, random_state=random_seed)
    return X_train, X_test, y_train, y_test


# confusion matrix
def plot_heat_map(y_test, y_pred):
    con_mat = confusion_matrix(y_test, y_pred)
    # normalize
    # con_mat_norm = con_mat.astype('float') / con_mat.sum(axis=1)[:, np.newaxis]
    # con_mat_norm = np.around(con_mat_norm, decimals=2)

    # plot
    plt.figure(figsize=(8, 8))
    seaborn.heatmap(con_mat, annot=True, fmt='.20g', cmap='Blues')
    plt.ylim(0, 5)
    plt.xlabel('Predicted labels')
    plt.ylabel('True labels')
    plt.title('Confusion Matrix')
    plt.savefig('confusion_matrix.png')
    plt.show()


def plot_history_tf(history):
    plt.figure(figsize=(8, 8))
    plt.plot(history.history['accuracy'])
    plt.plot(history.history['val_accuracy'])
    plt.title('Model Accuracy')
    plt.ylabel('Accuracy')
    plt.xlabel('Epoch')
    plt.legend(['Train', 'Test'], loc='upper left')
    plt.savefig('accuracy.png')
    plt.show()

    plt.figure(figsize=(8, 8))
    plt.plot(history.history['loss'])
    plt.plot(history.history['val_loss'])
    plt.title('Model Loss')
    plt.ylabel('Loss')
    plt.xlabel('Epoch')
    plt.legend(['Train', 'Test'], loc='upper left')
    plt.savefig('loss.png')
    plt.show()


def plot_history_torch(history):
    plt.figure(figsize=(8, 8))
    plt.plot(history['train_acc'])
    plt.plot(history['test_acc'])
    plt.title('Model Accuracy')
    plt.ylabel('Accuracy')
    plt.xlabel('Epoch')
    plt.legend(['Train', 'Test'], loc='upper left')
    plt.savefig('accuracy.png')
    plt.show()

    plt.figure(figsize=(8, 8))
    plt.plot(history['train_loss'])
    plt.plot(history['test_loss'])
    plt.title('Model Loss')
    plt.ylabel('Loss')
    plt.xlabel('Epoch')
    plt.legend(['Train', 'Test'], loc='upper left')
    plt.savefig('loss.png')
    plt.show()

