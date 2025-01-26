import torch
import pandas as pd
import numpy as np
import os
import seaborn as sns
import sys
repo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
if repo_path not in sys.path:
    sys.path.append(repo_path)
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay, classification_report
from torch.utils.data import DataLoader
from torchvision.transforms import Compose, Normalize, ToTensor
from src.preprocessing import CustomDataset, normalize_columns, load_data, c_transform
from src.training import collate_fn
from src.models.genre_model import CRNN

# Define las transformaciones
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Usando dispositivo: {device}")
base_path = "/content/drive/MyDrive/TFG/data/"
model_path = "/content/drive/MyDrive/TFG/models/best_crnn_genre.pth"
csv_path = "/content/drive/MyDrive/TFG/data/espectrogramas_salida_test/dataset_genero_test.csv"
mean = [0.676956295967102, 0.2529653012752533, 0.4388839304447174]
std = [0.21755781769752502, 0.15407244861125946, 0.07557372003793716]
columns = ["Spectral Centroid", "Spectral Bandwidth", "Spectral Roll-off"]
hidden_size = 256
additional_features_dim = 12
num_classes = 6

model = CRNN(num_classes=num_classes, additional_features_dim=12, hidden_size=256)
model.load_state_dict(torch.load(model_path, map_location=device))
model.to(device)
model.eval()

data = load_data(csv_path)
data["Ruta"] = data["Ruta"].str.replace("\\", "/")
data["Ruta"] = base_path + data["Ruta"]
normalize_columns(data, columns)

class_counts = data[["Afro House", "Ambient", "Deep House", "Techno", "Trance","Progressive House"]].sum()


# Mostrar el conteo por clase
print("Distribución de clases en el conjunto de datos:")
print(class_counts)


# Verificar rutas
for img_path in data["Ruta"]:
    if not os.path.exists(img_path):
        print(f"Ruta no encontrada: {img_path}")

# Definir transformaciones
test_transform = c_transform(mean, std)

# Crear dataset y DataLoader
test_dataset = CustomDataset(data, base_path, transform=test_transform)
test_loader = DataLoader(
    test_dataset, batch_size=128, collate_fn=collate_fn, shuffle=False, num_workers=2, pin_memory=True
)

# Realizar predicciones
all_preds = []
all_labels = []

with torch.no_grad():
    for images, additional_features, labels in test_loader:
        images = images.to(device)
        additional_features = additional_features.to(device)
        labels = labels.to(device)  # Etiquetas en formato one-hot

        # Obtener predicciones del modelo
        outputs = model(images, additional_features)  # Salida: (batch_size, 3, num_classes)
        preds = torch.argmax(outputs, dim=1)  # Predicciones por fragmento

        # Procesar etiquetas reales
        labels_grouped = torch.argmax(labels, dim=1)  # Convertir etiquetas a índices de clase
        labels_final = labels_grouped[:, 0]  # Seleccionar la etiqueta del primer fragmento

        # Procesar predicciones
        preds_final = preds[:, 0]  # Seleccionar la predicción del primer fragmento

        # Verificar consistencia de los grupos
        for label_group in labels_grouped:
            if not torch.all(label_group == label_group[0]):
                print(f"Advertencia: Grupo inconsistente encontrado: {label_group}")

        # Almacenar etiquetas y predicciones finales
        all_preds.extend(preds_final.cpu().numpy())
        all_labels.extend(labels_final.cpu().numpy())

# Generar matriz de confusión
conf_matrix = confusion_matrix(all_labels, all_preds)
print("Matriz de confusión:")
print(conf_matrix)

# Reporte de clasificación
print("Reporte de clasificación:")
print(classification_report(all_labels, all_preds))

# Visualizar matriz de confusión
plt.figure(figsize=(10, 8))
sns.heatmap(conf_matrix, annot=True, fmt="d", cmap="Blues", xticklabels=range(num_classes), yticklabels=range(num_classes))
plt.xlabel("Predicciones")
plt.ylabel("Etiquetas Reales")
plt.title("Matriz de Confusión")
plt.show()
