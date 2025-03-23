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

# 🔹 Cargar ResNet18 preentrenada
class ResNetFeatureExtractor(nn.Module):
    def __init__(self, additional_features_dim=10):
        super(ResNetFeatureExtractor, self).__init__()
        resnet = models.resnet18(weights=models.ResNet18_Weights.IMAGENET1K_V1)
        self.resnet = nn.Sequential(*list(resnet.children())[:-1])
        self.feature_dim = resnet.fc.in_features + additional_features_dim  

    def forward(self, x, additional_features):
        x = self.resnet(x)
        x = x.view(x.size(0), -1)
        x = torch.cat((x, additional_features), dim=-1)
        return x
    
def collate_fn(batch):
    batch = [item for item in batch if item is not None]  # Filtra `None`
    if len(batch) == 0:
        return None  
    return torch.utils.data.dataloader.default_collate(batch)

# 🔹 Función para extraer características con ResNet18
def extract_features(data_loader, model, device):
    model.eval()
    features, labels_ar, labels_va = [], [], []
    
    with torch.no_grad():
        for images, additional_features, arousal, valence in data_loader:
            images = images.to(device)
            additional_features = additional_features.to(device)

            # Extraer características
            feats = model(images, additional_features).cpu().numpy()
            features.extend(feats)
            labels_ar.extend(arousal.numpy())
            labels_va.extend(valence.numpy())

    
    return np.array(features), np.array(labels_ar), np.array(labels_va)


mean=[0.676956295967102, 0.2529653012752533, 0.4388839304447174]
std=[0.21755781769752502, 0.15407244861125946, 0.07557372003793716]

# Cargar datos
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
columns = ["Spectral Centroid", "Spectral Bandwidth", "Spectral Roll-off"]
learning_rate = 0.001
weight_decay = 1e-5
data_path = "/content/drive/MyDrive/TFG/images/espectrogramas_normalizados_emociones_estructura/dataset_emociones_secciones.csv"
base_path = "/content/drive/MyDrive/TFG/images/"
epochs = 50
patience = 5
best_val_loss = float("inf")
early_stop_counter = 0
epochs_list = []
train_losses, val_losses = [], []
val_maes_va,val_maes_ar = [], []
rmse_arousal, rmse_valence = [], []
r2_valence, r2_arousal = [], []
data = load_data(data_path)
data["Ruta"] = data["Ruta"].str.replace("\\", "/")
data["Ruta"] = base_path + data["Ruta"]
data["Ruta"] = data["Ruta"].str.replace("espectrogramas_salida_secciones_2", "espectrogramas_normalizados_emociones_estructura")


# Cargar dataset
data = pd.read_csv(data_path)
train_data, test_data = split_dataset(data)

# Transformaciones
train_transform = c_transform(mean, std)
test_transform = c_transform(mean, std)

# Cargar datasets
train_dataset = EmotionDataset_RF(train_data, base_path, transform=train_transform)
test_dataset = EmotionDataset_RF(test_data, base_path, transform=test_transform)

train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True, collate_fn=collate_fn)
test_loader = DataLoader(test_dataset, batch_size=32, shuffle=False, collate_fn=collate_fn)

# Extraer características
extractor = ResNetFeatureExtractor().to(device)
train_features, train_labels_ar, train_labels_va = extract_features(train_loader, extractor, device)
test_features, test_labels_ar, test_labels_va = extract_features(test_loader, extractor, device)

# Normalizar características
scaler = StandardScaler()
train_features = scaler.fit_transform(train_features)
test_features = scaler.transform(test_features)

# Guardar el scaler
joblib.dump(scaler, "scaler.pkl")

# Entrenar Random Forest
rf_arousal = RandomForestRegressor(n_estimators=100, random_state=42)
rf_valence = RandomForestRegressor(n_estimators=100, random_state=42)

rf_arousal.fit(train_features, train_labels_ar)
rf_valence.fit(train_features, train_labels_va)

# Guardar modelos
joblib.dump(rf_arousal, "random_forest_arousal.pkl")
joblib.dump(rf_valence, "random_forest_valence.pkl")


# Predicciones
test_preds_ar = rf_arousal.predict(test_features)
test_preds_va = rf_valence.predict(test_features)

# Métricas de Evaluación
mae_ar = mean_absolute_error(test_labels_ar, test_preds_ar)
mae_va = mean_absolute_error(test_labels_va, test_preds_va)
r2_ar = r2_score(test_labels_ar, test_preds_ar)
r2_va = r2_score(test_labels_va, test_preds_va)

print(f"MAE Arousal: {mae_ar:.4f}, R2 Arousal: {r2_ar:.4f}")
print(f"MAE Valence: {mae_va:.4f}, R2 Valence: {r2_va:.4f}")

#Graficar resultados
fig, axs = plt.subplots(1, 2, figsize=(12, 5))

axs[0].scatter(test_labels_ar, test_preds_ar, alpha=0.5)
axs[0].set_xlabel("Real Arousal")
axs[0].set_ylabel("Predicted Arousal")
axs[0].set_title("Predicción Arousal")
axs[0].plot([0, 1], [0, 1], '--r')

axs[1].scatter(test_labels_va, test_preds_va, alpha=0.5)
axs[1].set_xlabel("Real Valence")
axs[1].set_ylabel("Predicted Valence")
axs[1].set_title("Predicción Valence")
axs[1].plot([0, 1], [0, 1], '--r')

plt.savefig("predicciones_arousal_valence_reg.png")
plt.show()
