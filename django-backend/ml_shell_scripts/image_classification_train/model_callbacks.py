import os

import torch
import matplotlib.pyplot as plt
from torch.utils.data import DataLoader
from torchvision.utils import make_grid
from lightning import Callback
from lightning.pytorch.callbacks import ModelCheckpoint, EarlyStopping
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay

def get_model_checkpoint_callback(save_dir):
    return ModelCheckpoint(
        dirpath=os.path.join(save_dir,"checkpoint"),
        filename="{epoch:02d}-{val_acc:.2f}",
        monitor="val_loss",
        mode="min",
        auto_insert_metric_name=False,
        save_last=True,
        save_top_k=1,
    )

def get_early_stopping_callback():
    return EarlyStopping("val_loss", patience=10)

class PredictionVisualizer(Callback):
    def __init__(self, val_dataloader: DataLoader, save_dir: str = "runs"):
        """
        Initializes the prediction visualizer callback.

        Args:
            val_dataloader (DataLoader): A DataLoader providing a batch of validation data.
            save_dir (str): Directory where the prediction images will be saved.
        """
        super().__init__()
        self.val_loader = val_dataloader
        self.save_dir = os.path.join(save_dir, "inference")
        os.makedirs(self.save_dir, exist_ok=True)

    def on_validation_end(self, trainer, pl_module):
        """
        Called at the end of the validation phase. Generates and saves a grid
        of images with model predictions and true labels.
        """
        val_imgs, val_labels = next(iter(self.val_loader))
        val_imgs, val_labels = val_imgs.to(pl_module.device), val_labels.to(
            pl_module.device
        )

        pl_module.eval()
        with torch.no_grad():
            logits = pl_module(val_imgs)
            preds = torch.argmax(logits, dim=-1)

        imgs = val_imgs.cpu()
        preds = preds.cpu()
        labels = val_labels.cpu()

        nrow = min(len(imgs), 8)
        grid = make_grid(imgs, nrow=nrow, normalize=True, pad_value=1)

        plt.figure(figsize=(nrow * 2, 8))
        plt.imshow(grid.permute(1, 2, 0))
        plt.axis("off")

        img_h, img_w = imgs.shape[2], imgs.shape[3]

        for idx, (pred, label) in enumerate(zip(preds, labels)):
            row = idx // nrow
            col = idx % nrow
            x = col * (img_w + 2) + 5
            y = row * (img_h + 2) + 15
            caption = f"P:{pred.item()} / L:{label.item()}"
            plt.text(
                x,
                y,
                caption,
                fontsize=9,
                color="white",
                bbox=dict(facecolor="black", alpha=0.6, edgecolor="none"),
            )

        save_path = os.path.join(self.save_dir, f"prediction_visual.png")
        plt.tight_layout()
        plt.savefig(save_path)
        plt.close()


class ConfusionMatrixVisualizer(Callback):
    def __init__(self, val_dataloader: DataLoader, save_dir: str = "runs"):
        """
        Initializes the confusion matrix visualizer callback.

        Args:
            val_dataloader (DataLoader): Validation dataloader used to evaluate the model.
            save_dir (str): Directory where the confusion matrix image will be saved.
        """
        super().__init__()
        self.val_loader = val_dataloader
        self.save_dir = os.path.join(save_dir, "inference")
        os.makedirs(self.save_dir, exist_ok=True)

    def on_validation_end(self, trainer, pl_module):
        """
        Called at the end of validation. Computes and saves the confusion matrix
        for the entire validation set.
        """
        all_preds = []
        all_labels = []

        pl_module.eval()
        with torch.no_grad():
            for i, batch in enumerate(self.val_loader):
                imgs, labels = batch
                imgs, labels = imgs.to(device=pl_module.device), labels.to(
                    device=pl_module.device
                )

                logits = pl_module(imgs)
                preds = torch.argmax(logits, dim=-1)

                all_preds.append(preds.cpu())
                all_labels.append(labels.cpu())

        all_preds = torch.cat(all_preds).numpy()
        all_labels = torch.cat(all_labels).numpy()

        cm = confusion_matrix(all_labels, all_preds)

        fig = plt.figure(figsize=(8, 6))
        ax = fig.gca()
        disp = ConfusionMatrixDisplay(confusion_matrix=cm)
        disp.plot(ax=ax, cmap="Blues", colorbar=False)
        plt.title("Confusion Matrix")
        plt.tight_layout()

        save_path = os.path.join(self.save_dir, "confusion_matrix.png")
        plt.savefig(save_path)
        plt.close(fig)


class ROCPlotter(Callback):
    def __init__(self, save_dir: str = "runs"):
        """
        Initializes the ROC curve plotter.

        Args:
            save_dir (str): Directory where the ROC curve plots will be saved.
        """
        super().__init__()
        self.save_dir = os.path.join(save_dir, "inference")
        os.makedirs(self.save_dir, exist_ok=True)

    def on_validation_epoch_end(self, trainer, pl_module):
        """
        Called at the end of the validation epoch. Plots and saves ROC curves
        for each class if `val_roc_metric` is defined on the model.
        """

        if not hasattr(pl_module, "val_roc_metric"):
            return

        fpr, tpr, thresholds = pl_module.val_roc_metric.compute()
        pl_module.val_roc_metric.reset()

        fpr = torch.stack([f.cpu() for f in fpr], dim=0)
        tpr = torch.stack([t.cpu() for t in tpr], dim=0)

        num_classes = fpr.shape[0]

        plt.figure(figsize=(10, 8))
        for i in range(num_classes):
            plt.plot(fpr[i], tpr[i], label=f"Class {pl_module.classes[i]}")

        plt.xlabel("False Positive Rate")
        plt.ylabel("True Positive Rate")
        plt.title("ROC Curve")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()

        save_path = os.path.join(self.save_dir, f"roc_curve.png")
        plt.savefig(save_path)
        plt.close()


class GraphPlotter(Callback):
    def __init__(self, save_dir: str = "runs"):
        """
        Callback to track and plot training/validation loss and accuracy over epochs.

        Args:
            save_dir (str): Directory where the curve plots will be saved.
        """
        super().__init__()
        self.save_dir = os.path.join(save_dir, "graphs")
        os.makedirs(self.save_dir, exist_ok=True)

        self.train_losses = []
        self.train_accuracies = []
        self.val_losses = []
        self.val_accuracies = []

    def on_train_epoch_end(self, trainer, pl_module):
        """
        Collects metrics at the end of each training epoch.
        """
        metrics = trainer.callback_metrics

        for key, store in [
            ("train_loss", self.train_losses),
            ("train_acc", self.train_accuracies),
            ("val_loss", self.val_losses),
            ("val_acc", self.val_accuracies),
        ]:
            value = metrics.get(key)
            if value is not None:
                store.append(value.cpu().item())

    def on_train_end(self, trainer, pl_module):
        """
        Plots the collected metrics once training ends.
        """
        epochs = list(range(len(self.train_losses)))

        def save_plot(values, title, ylabel, filename):
            plt.figure()
            plt.plot(epochs, values, label=title, marker="o")
            plt.xlabel("Epoch")
            plt.ylabel(ylabel)
            plt.title(title)
            plt.grid(True)
            plt.legend()
            plt.tight_layout()
            plt.savefig(os.path.join(self.save_dir, filename))
            plt.close()

        save_plot(self.train_losses, "Training Loss", "Loss", "train_loss.png")
        save_plot(self.train_accuracies, "Training Accuracy", "Accuracy", "train_accuracy.png")
        save_plot(self.val_losses, "Validation Loss", "Loss", "val_loss.png")
        save_plot(self.val_accuracies, "Validation Accuracy", "Accuracy", "val_accuracy.png")