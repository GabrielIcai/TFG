import numpy as np
import torch
import torch.nn as nn
import torchvision.models as models
from torch.utils.data import DataLoader
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
import matplotlib.pyplot as plt
import joblib
import os
import sys
from sklearn.preprocessing import StandardScaler
repo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if repo_path not in sys.path:
    sys.path.append(repo_path)
from src.preprocessing import (
    load_data,
    split_dataset,
    c_transform,
)
from src.preprocessing.data_loader import load_data, split_dataset
from src.training import collate_fn_emotions
from torch.utils.data import DataLoader
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from src.preprocessing.custom_dataset import EmotionDataset_RF
import torch
import torch.nn as nn
import torchvision.models as models
import torchvision.transforms as transforms
from torch.utils.data import Dataset, DataLoader
from PIL import Image
import pandas as pd
import numpy as np
import os
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, r2_score
import matplotlib.pyplot as plt

import torch
import torch.nn as nn
import torchvision.models as models

import torch
import torch.nn as nn
import torchvision.models as models
import numpy as np
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from torch.utils.data import DataLoader

# Definir el modelo de ResNet18 como extractor de características
def get_resnet18_feature_extractor():
    model = models.resnet18(pretrained=True)
    model = nn.Sequential(*list(model.children())[:-1])
    model.eval()
    return model

# Extraer características con ResNet-18
def extract_features(model, dataloader, device):
    features, labels = [], []
    model.to(device)
    with torch.no_grad():
        for batch in dataloader:
            images, valence, arousal = batch
            images = images.to(device)
            feature_vector = model(images)
            feature_vector = feature_vector.view(feature_vector.size(0), -1).cpu().numpy()
            
            features.append(feature_vector)
            labels.append(np.column_stack((valence.numpy(), arousal.numpy())))
    
    return np.vstack(features), np.vstack(labels)

# Entrenar modelo de Random Forest
def train_random_forest(X_train, y_train):
    rf_valence = RandomForestRegressor(n_estimators=100, random_state=42)
    rf_arousal = RandomForestRegressor(n_estimators=100, random_state=42)
    
    rf_valence.fit(X_train, y_train[:, 0])
    rf_arousal.fit(X_train, y_train[:, 1])
    
    return rf_valence, rf_arousal

# Evaluar modelo
def evaluate_model(model, X_test, y_test, label):
    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    print(f'{label} - MAE: {mae:.4f}, R2: {r2:.4f}')
    return mae, r2

# Main
if __name__ == "__main__":
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    columns = ["Spectral Centroid", "Spectral Bandwidth", "Spectral Roll-off"]
    learning_rate = 0.001
    weight_decay = 1e-5
    data_path = "/content/drive/MyDrive/TFG/images/espectrogramas_normalizados_emociones_estructura/dataset_emociones_secciones.csv"
    base_path = "/content/drive/MyDrive/TFG/images/"
    mean=[0.676956295967102, 0.2529653012752533, 0.4388839304447174]
    std=[0.21755781769752502, 0.15407244861125946, 0.07557372003793716]

    data = load_data(data_path)
    data["Ruta"] = data["Ruta"].str.replace("\\", "/")
    data["Ruta"] = base_path + data["Ruta"]
    data["Ruta"] = data["Ruta"].str.replace("espectrogramas_salida_secciones_2", "espectrogramas_normalizados_emociones_estructura")
    train_data, test_data = split_dataset(data)
    
    # Transformaciones
    train_transform = c_transform(mean, std)
    test_transform = c_transform(mean, std)
    
    # Crear datasets
    train_dataset = EmotionDataset_RF(train_data, base_path, transform=train_transform)
    test_dataset = EmotionDataset_RF(test_data, base_path, transform=test_transform)
    
    # DataLoaders
    train_loader = DataLoader(train_dataset, batch_size=128, shuffle=True, collate_fn=collate_fn_emotions)
    test_loader = DataLoader(test_dataset, batch_size=128, shuffle=False, collate_fn=collate_fn_emotions) 
     
    
    resnet_model = get_resnet18_feature_extractor()
    
    print("Extrayendo características de entrenamiento...")
    X_train, y_train = extract_features(resnet_model, train_loader, device)
    
    print("Extrayendo características de prueba...")
    X_test, y_test = extract_features(resnet_model, test_loader, device)
    
    print("Entrenando modelos Random Forest...")
    rf_valence, rf_arousal = train_random_forest(X_train, y_train)
    
    print("Evaluando modelos...")
    evaluate_model(rf_valence, X_test, y_test[:, 0], "Valence")
    evaluate_model(rf_arousal, X_test, y_test[:, 1], "Arousal")
    
    # Guardar modelos
    joblib.dump(rf_valence, "random_forest_valence.pkl")
    joblib.dump(rf_arousal, "random_forest_arousal.pkl")
    print("Modelos guardados exitosamente.")


