import os
import torch
import lightning as L
from timm import create_model
from PIL import Image, ImageDraw
from torch.nn import BCEWithLogitsLoss, CrossEntropyLoss
from torchvision import transforms
from torchmetrics import Accuracy, F1Score, AUROC
from torchmetrics.classification import BinaryROC, MulticlassROC

# TODO: Provide model specific transforms

class LitClassification(L.LightningModule):
    """
    PyTorch Lightning module for image classification tasks.
    Supports binary and multiclass classification, using models from `timm`.
    Includes training, validation, testing, and inference capabilities.
    """
    def __init__(self, model: str, classes: list[str], save_dir: str = "runs"):
        """
        Initializes the classification module.

        Args:
            model (str): Name of the model architecture to use from `timm`.
            classes (list[str]): A list of class names.
            save_dir (str, optional): Directory to save inference results. Defaults to "runs".
        """
        super().__init__()
        self.save_dir = os.path.join(save_dir, "inference")
        os.makedirs(self.save_dir, exist_ok=True)

        self.classes = classes
        self.num_classes = len(classes)
        self.model = create_model(model, num_classes=self.num_classes, pretrained=True)

        self.is_binary = self.num_classes == 2
        self.task_type = "binary" if self.is_binary else "multiclass"
        self.loss_fn = CrossEntropyLoss()
        self._init_metrics()

    def _init_metrics(self):
        """Initializes all torchmetrics for training, validation, and testing."""
        # --- Training metrics ---
        self.train_acc = Accuracy(task=self.task_type, num_classes=self.num_classes)

        # --- Validation metrics ---
        self.val_acc = Accuracy(task=self.task_type, num_classes=self.num_classes)
        self.val_f1 = F1Score(task=self.task_type, num_classes=self.num_classes, average="macro")
        self.val_auroc = AUROC(task=self.task_type, num_classes=self.num_classes, average="macro")
        self.val_roc_metric = BinaryROC() if self.is_binary else MulticlassROC(self.num_classes, thresholds=None)

        # --- Test metrics ---
        self.test_acc = Accuracy(task=self.task_type, num_classes=self.num_classes)
        self.test_f1 = F1Score(task=self.task_type, num_classes=self.num_classes, average="macro")
        self.test_auroc = AUROC(task=self.task_type, num_classes=self.num_classes, average="macro")

    def forward(self, x):
        """
        Defines the forward pass of the model.

        Args:
            x (torch.Tensor): Input tensor (batch of images).

        Returns:
            torch.Tensor: Output logits from the model.
        """
        return self.model(x)

    def _step(self, images, targets):
        """
        Common step for processing a batch of data during training, validation, or testing.

        Args:
            images (torch.Tensor): Batch of input images.
            targets (torch.Tensor): Batch of target labels.

        Returns:
            tuple[torch.Tensor, torch.Tensor, torch.Tensor]: Loss, logits, and predictions.
        """
        logits = self.model(images)
        loss = self.loss_fn(logits, targets)
        preds = torch.argmax(logits, dim=1)
        return loss, logits, preds

    def training_step(self, batch, batch_idx):
        images, targets = batch
        loss, _, preds = self._step(images, targets)
        
        accuracy = self.train_acc(preds, targets)
        self.log("train_loss", loss, on_step=False, on_epoch=True, prog_bar=True)
        self.log("train_acc", accuracy, on_step=False, on_epoch=True, prog_bar=True)
        
        return loss

    def validation_step(self, batch, batch_idx):
        images, targets = batch
        loss, logits, preds = self._step(images, targets)
        
        accuracy = self.val_acc(preds, targets)
        self.val_f1.update(preds, targets)
        self.val_auroc.update(logits, targets)
        self.val_roc_metric.update(logits, targets)
        
        self.log("val_loss", loss, on_step=False, on_epoch=True, prog_bar=True)
        self.log("val_acc", accuracy, on_step=False, on_epoch=True, prog_bar=True)
        return {"val_loss": loss, "val_acc": accuracy}

    def on_validation_epoch_end(self):
        self.log("val_f1", self.val_f1.compute(), prog_bar=True)
        self.log("val_auroc", self.val_auroc.compute(), prog_bar=True)
        self.val_f1.reset()
        self.val_auroc.reset()

    def test_step(self, batch, batch_idx):
        images, targets = batch
        loss, logits, preds = self._step(images, targets)

        accuracy = self.test_acc(preds, targets)
        self.test_f1.update(preds, targets)
        self.test_auroc.update(logits, targets)

        self.log("test_loss", loss, on_step=False, on_epoch=True, prog_bar=True)
        self.log("test_acc", accuracy, on_step=False, on_epoch=True, prog_bar=True)
        return {"test_loss": loss, "test_acc": accuracy}

    def on_test_epoch_end(self):
        self.log("test_f1", self.test_f1.compute(), prog_bar=True)
        self.log("test_auroc", self.test_auroc.compute(), prog_bar=True)
        self.test_f1.reset()
        self.test_auroc.reset()

    def configure_optimizers(self):
        optimizer = torch.optim.Adam(self.parameters(), lr=1e-3)
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="min", factor=0.1, patience=3)

        return {
            "optimizer": optimizer,
            "lr_scheduler": {
                "scheduler": scheduler,
                "monitor": "val_loss",
                "interval": "epoch",
                "frequency": 1,
            },
        }

    def infer_image(self, image_path: str, transform = None, save_image: bool = False):
        """
        Performs inference on a single image.

        Args:
            image_path (str): Path to the input image.
            transform (transforms.Compose, optional): torchvision transforms to apply.
                If None, a basic ToTensor transform is used.
            save_image (bool, optional): Whether to save the image with the predicted label. Defaults to False.

        Returns:
            str: The predicted class label.
        """
        allowed_exts = (".jpg", ".jpeg", ".png", ".bmp")
        if not image_path.lower().endswith(allowed_exts):
            raise ValueError(f"File {image_path} is not a valid image format.")

        if transform is None:
            transform = transforms.ToTensor()

        image = Image.open(image_path).convert("RGB")
        tensor = transform(image).unsqueeze(0).to(self.device)

        self.eval()
        with torch.no_grad():
            logits = self.model(tensor)
            pred_idx = torch.argmax(logits, dim=1).item()
            pred_label = self.classes[pred_idx]

        if save_image:
            image_name = os.path.basename(image_path)
            draw = ImageDraw.Draw(image)
            draw.text((10, 10), f"Predicted : {str(pred_label)}", fill="red")
            image.save(os.path.join(self.save_dir, image_name))

        return pred_label

    def infer_directory(self, folder_path: str, transform = None, save_images: bool = False):
        """
        Performs inference on all valid images in a directory.

        Args:
            folder_path (str): Path to the directory containing images.
            transform (transforms.Compose, optional): torchvision transforms to apply to each image.
            save_images (bool, optional): Whether to save images with predicted labels. Defaults to False.
        """
        if not os.path.exists(folder_path):
            raise ValueError(f"Folder {folder_path} doesn't exist.")

        allowed_exts = (".jpg", ".jpeg", ".png", ".bmp")

        for filename in os.listdir(folder_path):
            if filename.lower().endswith(allowed_exts):
                full_path = os.path.join(folder_path, filename)
                try:
                    prediction = self.infer_image(
                        full_path,
                        transform=transform,
                        save_image=save_images
                    )
                    print(f"Processed: {full_path} -> Predicted: {prediction}")
                except Exception as e:
                    print(f"Error processing {full_path}: {str(e)}")
                    continue
