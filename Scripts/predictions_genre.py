import torch
import pandas as pd
import numpy as np
import os
import sys
repo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
if repo_path not in sys.path:
    sys.path.append(repo_path)
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay, classification_report
from torch.utils.data import DataLoader
from torchvision.transforms import Compose, Normalize, ToTensor
from src.models.genre_model import CNN_LSTM_genre, CRNN
# Define las transformaciones
mean = [0.676956295967102, 0.2529653012752533, 0.4388839304447174]
std = [0.21755781769752502, 0.15407244861125946, 0.07557372003793716]
def c_transform(mean, std):
    return Compose([ToTensor(), Normalize(mean=mean, std=std)])

# Ruta de los datos y el modelo
base_path = "/content/drive/MyDrive/TFG/data/"
model_path = "/content/drive/MyDrive/TFG/models/best_crnn_genre.pth"
nuevo_csv_path = "/content/drive/MyDrive/TFG/data/espectrogramas_salida_test/dataset_genero_test.csv"

# Carga los datos
def load_data(csv_path):
    data = pd.read_csv(csv_path)
    data["Ruta"] = base_path + data["Ruta"].str.replace("\\", "/")
    return data

# Dataset personalizado
class CustomDataset(torch.utils.data.Dataset):
    def __init__(self, dataframe, base_path, transform=None):
        self.dataframe = dataframe
        self.base_path = base_path
        self.transform = transform

    def __len__(self):
        return len(self.dataframe)

    def __getitem__(self, idx):
        img_path = self.dataframe.iloc[idx]["Ruta"]
        features = self.dataframe.iloc[idx]["Spectral Centroid":"Spectral Roll-off"].values.astype(np.float32)
        label = self.dataframe.iloc[idx]["Label"]

        image = plt.imread(img_path)
        if self.transform:
            image = self.transform(image)

        return image, features, label

# Carga el modelo
def load_model(model_path, num_classes, additional_features_dim, hidden_size):
    model = CRNN(num_classes, additional_features_dim, hidden_size)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.load_state_dict(torch.load(model_path, map_location=device))
    return model

# Realiza predicciones
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

# Visualiza la matriz de confusión
def plot_confusion_matrix(y_true, y_pred, class_names):
    cm = confusion_matrix(y_true, y_pred)
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=class_names)
    disp.plot(cmap="viridis")
    plt.title("Matriz de Confusión")
    plt.show()

# Main
def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Usando dispositivo: {device}")

    # Carga de datos
    data = load_data(nuevo_csv_path)
    transform = c_transform(mean, std)
    dataset = CustomDataset(data, base_path, transform=transform)
    dataloader = DataLoader(dataset, batch_size=128, shuffle=False, num_workers=2)

    # Carga del modelo
    num_classes = 6
    additional_features_dim = 12
    hidden_size = 256
    model = load_model(model_path, num_classes, additional_features_dim, hidden_size).to(device)

    # Predicciones
    y_pred, y_true = predict(model, dataloader, device)

    # Reporte y matriz de confusión
    class_names = ["Clase 0", "Clase 1", "Clase 2", "Clase 3", "Clase 4", "Clase 5"]
    print(classification_report(y_true, y_pred, target_names=class_names))
    plot_confusion_matrix(y_true, y_pred, class_names)

if __name__ == "__main__":
    main()
