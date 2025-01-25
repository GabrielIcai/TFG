import torch
import pandas as pd
import numpy as np
import os
import sys
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
nuevo_csv_path = "/content/drive/MyDrive/TFG/data/espectrogramas_salida_test/dataset_genero_test.csv"
mean = [0.676956295967102, 0.2529653012752533, 0.4388839304447174]
std = [0.21755781769752502, 0.15407244861125946, 0.07557372003793716]
columns = ["Spectral Centroid", "Spectral Bandwidth", "Spectral Roll-off"]
hidden_size = 256
additional_features_dim = 12
num_classes = 6

def c_transform(mean, std):
    return Compose([ToTensor(), Normalize(mean=mean, std=std)])

def load_data(csv_path):
    data = pd.read_csv(csv_path)
    data["Ruta"] = data["Ruta"].str.replace("\\", "/")
    data["Ruta"] = base_path + data["Ruta"]
    normalize_columns(data, columns)
    return data

def load_model(model_path, num_classes, additional_features_dim, hidden_size):
    model = CRNN(num_classes, additional_features_dim, hidden_size)
    model.load_state_dict(torch.load(model_path, map_location=device))
    return model

def predict(model, dataloader, device):
    all_preds = []
    all_labels = []

    with torch.no_grad():
        for images, features, labels in dataloader:
            images, features = images.to(device), features.to(device)
            outputs = model(images, features)
            preds = torch.argmax(outputs, dim=1)

            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())

    return np.array(all_preds), np.array(all_labels)

def plot_confusion_matrix(y_true, y_pred, class_names):
    cm = confusion_matrix(y_true, y_pred)
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=class_names)
    disp.plot(cmap="viridis")
    plt.title("Matriz de Confusión")
    plt.show()

def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Usando dispositivo: {device}")

    data = load_data(nuevo_csv_path)
    transform = c_transform(mean, std)
    dataset = CustomDataset(data, base_path, transform=transform)
    dataloader = DataLoader(dataset, batch_size=128, collate_fn=collate_fn, shuffle=False, num_workers=2)
    print(data.head(100))

    model = load_model(model_path, num_classes, additional_features_dim, hidden_size).to(device)

    y_pred, y_true = predict(model, dataloader, device)

    class_names = ["Clase 0", "Clase 1", "Clase 2", "Clase 3", "Clase 4", "Clase 5"]
    print(classification_report(y_true, y_pred, target_names=class_names))
    plot_confusion_matrix(y_true, y_pred, class_names)

if __name__ == "__main__":
    main()