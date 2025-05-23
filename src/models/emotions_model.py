import torch
import torch.nn as nn
import torchvision.models as models

class ResNetCRNNEmotionModel(nn.Module):
    def __init__(self, num_valencia_classes=11, num_arousal_classes=11, hidden_size=256, num_layers=2,additional_features_dim=10):
        super(ResNetCRNNEmotionModel, self).__init__()
        
        #RESNET-18
        resnet = models.resnet18(pretrained=True)
        
        #Ultima capa de resnet no nos vale (ya que utilizamos LSTM al final)
        self.resnet = nn.Sequential(*list(resnet.children())[:-1])

        #LSTM
        self.lstm = nn.LSTM(
            input_size=resnet.fc.in_features + additional_features_dim,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=True
        )

        #Necesito dos salidas: valencia y arousal
        self.fc_valencia = nn.Linear(hidden_size * 2, 1)
        self.fc_arousal = nn.Linear(hidden_size * 2, 1)

    def forward(self, x, additional_features):
        x = self.resnet(x)
        x = x.view(x.size(0), 1, -1)
        additional_features = additional_features.unsqueeze(1)
        x = torch.cat((x, additional_features), dim=-1)  

        #LSTM
        lstm_out, _ = self.lstm(x)
        lstm_out = lstm_out[:, -1, :]
        valencia = (self.fc_valencia(lstm_out))
        arousal = (self.fc_arousal(lstm_out))

        valencia_output = torch.sigmoid(valencia)
        arousal_output= torch.sigmoid(arousal)

        return valencia_output, arousal_output
    
    def predict(self, image, additional_features):
        self.eval()

        with torch.no_grad():
            valencia_output, arousal_output = self.forward(image, additional_features)

        return valencia_output.item(), arousal_output.item()

