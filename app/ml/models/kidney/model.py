import torch
import torch.nn as nn


class KidneyDiseaseNN(nn.Module):
    """
    Deep Neural Network for Chronic Kidney Disease prediction.
    Input: 24 features (after encoding and imputation)
    Output: probability of CKD (0 = no CKD, 1 = CKD)
    """
    def __init__(self, input_size=24):
        super(KidneyDiseaseNN, self).__init__()

        self.network = nn.Sequential(
            # Layer 1
            nn.Linear(input_size, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(0.3),

            # Layer 2
            nn.Linear(128, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Dropout(0.3),

            # Layer 3
            nn.Linear(64, 32),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.Dropout(0.2),

            # Layer 4
            nn.Linear(32, 16),
            nn.ReLU(),

            # Output
            nn.Linear(16, 1),
            nn.Sigmoid()
        )

    def forward(self, x):
        return self.network(x)
