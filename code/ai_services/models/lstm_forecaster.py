"""
AlphaFX AI Services - LSTM Price Direction Forecaster
Bidirectional LSTM with attention mechanism for short-horizon
FX direction prediction.  Predicts P(next N bars are up) for a
given currency pair.

Architecture:
  Input:  (batch, lookback, n_features)
  Layers: 2x BiLSTM -> Temporal Attention -> Dense -> Sigmoid
  Output: scalar probability in [0, 1]

Usage:
  from ai_services.models.lstm_forecaster import LSTMForecaster
  model = LSTMForecaster(n_features=40)
  model.fit(X_train, y_train)
  probs = model.predict(X_test)
"""

import json
import os

import numpy as np

try:
    import torch
    import torch.nn as nn

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


# ---------------------------------------------------------------------------
# PyTorch model definition
# ---------------------------------------------------------------------------

if TORCH_AVAILABLE:

    class _TemporalAttention(nn.Module):
        """Scaled dot-product temporal attention over LSTM hidden states."""

        def __init__(self, hidden_size: int):
            super().__init__()
            self.attn = nn.Linear(hidden_size * 2, 1)

        def forward(self, lstm_out: "torch.Tensor") -> "torch.Tensor":
            # lstm_out: (batch, seq, hidden*2)
            scores = self.attn(lstm_out).squeeze(-1)  # (batch, seq)
            weights = torch.softmax(scores, dim=-1)  # (batch, seq)
            context = (weights.unsqueeze(-1) * lstm_out).sum(dim=1)  # (batch, hidden*2)
            return context

    class _LSTMNet(nn.Module):
        def __init__(
            self,
            n_features: int,
            hidden_size: int = 64,
            num_layers: int = 2,
            dropout: float = 0.2,
        ):
            super().__init__()
            self.lstm = nn.LSTM(
                input_size=n_features,
                hidden_size=hidden_size,
                num_layers=num_layers,
                dropout=dropout if num_layers > 1 else 0.0,
                batch_first=True,
                bidirectional=True,
            )
            self.attention = _TemporalAttention(hidden_size)
            self.dropout = nn.Dropout(dropout)
            self.fc = nn.Sequential(
                nn.Linear(hidden_size * 2, 32),
                nn.ReLU(),
                nn.Dropout(dropout),
                nn.Linear(32, 1),
                nn.Sigmoid(),
            )

        def forward(self, x: "torch.Tensor") -> "torch.Tensor":
            lstm_out, _ = self.lstm(x)  # (batch, seq, hidden*2)
            context = self.attention(lstm_out)
            context = self.dropout(context)
            return self.fc(context).squeeze(-1)


# ---------------------------------------------------------------------------
# High-level forecaster wrapper
# ---------------------------------------------------------------------------


class LSTMForecaster:
    """
    High-level LSTM forecaster that handles training, evaluation,
    persistence, and inference with graceful numpy fallback when
    PyTorch is unavailable.
    """

    def __init__(
        self,
        n_features: int,
        hidden_size: int = 64,
        num_layers: int = 2,
        dropout: float = 0.2,
        lr: float = 1e-3,
        epochs: int = 50,
        batch_size: int = 32,
        device: str = "cpu",
    ):
        self.n_features = n_features
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.dropout = dropout
        self.lr = lr
        self.epochs = epochs
        self.batch_size = batch_size
        self.device = device
        self._net = None
        self.history_: list[dict] = []
        self._fallback_model = None  # sklearn fallback

    # ---- Training ----------------------------------------------------------

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        val_split: float = 0.15,
    ) -> "LSTMForecaster":
        """
        Train the model.

        Parameters
        ----------
        X   shape (N, lookback, n_features)
        y   shape (N,) -- binary direction labels
        """
        if not TORCH_AVAILABLE:
            return self._fit_fallback(X, y)

        import torch
        from torch.utils.data import DataLoader, TensorDataset

        n_val = int(len(X) * val_split)
        X_tr, X_val = X[:-n_val], X[-n_val:]
        y_tr, y_val = y[:-n_val], y[-n_val:]

        device = torch.device(self.device)
        net = _LSTMNet(
            self.n_features, self.hidden_size, self.num_layers, self.dropout
        ).to(device)

        opt = torch.optim.Adam(net.parameters(), lr=self.lr)
        schedule = torch.optim.lr_scheduler.ReduceLROnPlateau(opt, patience=5)
        loss_fn = nn.BCELoss()

        tr_ds = TensorDataset(torch.FloatTensor(X_tr), torch.FloatTensor(y_tr))
        tr_dl = DataLoader(tr_ds, batch_size=self.batch_size, shuffle=True)

        best_val_loss = float("inf")
        best_state = None

        for epoch in range(1, self.epochs + 1):
            net.train()
            tr_losses = []
            for xb, yb in tr_dl:
                xb, yb = xb.to(device), yb.to(device)
                opt.zero_grad()
                preds = net(xb)
                loss = loss_fn(preds, yb)
                loss.backward()
                nn.utils.clip_grad_norm_(net.parameters(), 1.0)
                opt.step()
                tr_losses.append(loss.item())

            # Validation
            net.eval()
            with torch.no_grad():
                xv = torch.FloatTensor(X_val).to(device)
                yv = torch.FloatTensor(y_val).to(device)
                val_preds = net(xv)
                val_loss = loss_fn(val_preds, yv).item()
                val_acc = ((val_preds > 0.5).float() == yv).float().mean().item()

            schedule.step(val_loss)
            self.history_.append(
                {
                    "epoch": epoch,
                    "train_loss": np.mean(tr_losses),
                    "val_loss": val_loss,
                    "val_acc": val_acc,
                }
            )

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                best_state = {k: v.cpu().clone() for k, v in net.state_dict().items()}

        net.load_state_dict(best_state)
        self._net = net
        return self

    def _fit_fallback(self, X: np.ndarray, y: np.ndarray) -> "LSTMForecaster":
        """Logistic regression fallback when PyTorch is absent."""
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler

        X_flat = X.reshape(len(X), -1)
        self._scaler_fb = StandardScaler().fit(X_flat)
        self._fallback_model = LogisticRegression(max_iter=1000).fit(
            self._scaler_fb.transform(X_flat), y
        )
        return self

    # ---- Inference ---------------------------------------------------------

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Return P(up) for each sample. Shape (N,)."""
        if not TORCH_AVAILABLE or self._net is None:
            if self._fallback_model is not None:
                X_flat = X.reshape(len(X), -1)
                return self._fallback_model.predict_proba(
                    self._scaler_fb.transform(X_flat)
                )[:, 1]
            return np.full(len(X), 0.5)

        import torch

        self._net.eval()
        with torch.no_grad():
            xb = torch.FloatTensor(X).to(torch.device(self.device))
            return self._net(xb).cpu().numpy()

    def predict(self, X: np.ndarray, threshold: float = 0.5) -> np.ndarray:
        """Return binary direction predictions (1=up, 0=down)."""
        return (self.predict_proba(X) >= threshold).astype(int)

    # ---- Persistence -------------------------------------------------------

    def save(self, path: str) -> None:
        """Save model weights + metadata to directory."""
        os.makedirs(path, exist_ok=True)
        meta = {
            "n_features": self.n_features,
            "hidden_size": self.hidden_size,
            "num_layers": self.num_layers,
            "dropout": self.dropout,
            "history": self.history_,
        }
        with open(os.path.join(path, "meta.json"), "w") as f:
            json.dump(meta, f, indent=2)

        if TORCH_AVAILABLE and self._net is not None:
            import torch

            torch.save(self._net.state_dict(), os.path.join(path, "weights.pt"))

    @classmethod
    def load(cls, path: str) -> "LSTMForecaster":
        """Load a previously saved forecaster."""
        with open(os.path.join(path, "meta.json")) as f:
            meta = json.load(f)

        m = cls(
            n_features=meta["n_features"],
            hidden_size=meta["hidden_size"],
            num_layers=meta["num_layers"],
            dropout=meta["dropout"],
        )
        m.history_ = meta.get("history", [])

        weights_path = os.path.join(path, "weights.pt")
        if TORCH_AVAILABLE and os.path.exists(weights_path):
            import torch

            net = _LSTMNet(m.n_features, m.hidden_size, m.num_layers, m.dropout)
            net.load_state_dict(torch.load(weights_path, map_location="cpu"))
            m._net = net

        return m
