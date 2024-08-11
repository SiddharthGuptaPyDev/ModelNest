import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, 
                             QLineEdit, QMessageBox, QDialog, QLabel, QDialogButtonBox,
                             QMenu, QTextEdit, QProgressBar)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QAction
import requests
from datetime import datetime

class ModelDetailsDialog(QDialog):
    def __init__(self, model_data):
        super().__init__()
        self.setWindowTitle(f"Model Details: {model_data['name']}")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        
        self.details_text = ""
        for key, value in model_data.items():
            if key == 'details':
                for detail_key, detail_value in value.items():
                    label = QLabel(f"<b>{detail_key.replace('_', ' ').title()}:</b> {detail_value}")
                    layout.addWidget(label)
                    self.details_text += f"{detail_key.replace('_', ' ').title()}: {detail_value}\n"
            else:
                label = QLabel(f"<b>{key.replace('_', ' ').title()}:</b> {value}")
                layout.addWidget(label)
                self.details_text += f"{key.replace('_', ' ').title()}: {value}\n"
        
        button_layout = QHBoxLayout()
        copy_button = QPushButton("Copy")
        copy_button.clicked.connect(self.copy_details)
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        button_layout.addWidget(copy_button)
        button_layout.addWidget(ok_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def copy_details(self):
        QApplication.clipboard().setText(self.details_text)

class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Help")
        
        self.setFixedSize(800, 370)
        
        layout = QVBoxLayout()
        
        help_text = """
        How to Use ModelNest:
        • Select a model by clicking on any value in the model's row.
        • Refresh the model table by clicking the 'Refresh' button at the bottom left.
        • To delete a model, first select it, then click the 'Delete Model' button at the middle bottom, and confirm your decision.
        • View comprehensive information about a model by selecting it and clicking the 'Model Details' button at the bottom right.
        • Search for models in real-time by typing in the search bar.
        • Copy a data value by right-clicking on it and selecting 'Copy'.
        • Copy the detailed information by clicking the 'Copy' button in the details window that appears when you click the 'Model Details' button.

        FAQs:
        > Is ModelNest open-source?
          - Yes, ModelNest is an open-source project. Please review the license on the GitHub repository before taking any action.
        > Are there any hidden charges for using ModelNest?
          - No, there are no hidden charges.
        """
        
        help_text_edit = QTextEdit()
        help_text_edit.setPlainText(help_text)
        help_text_edit.setReadOnly(True)
        layout.addWidget(help_text_edit)
        
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        layout.addWidget(ok_button)
        
        self.setLayout(layout)

class LoadModelsThread(QThread):
    models_loaded = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def run(self):
        try:
            response = requests.get("http://localhost:11434/api/tags")
            if response.status_code == 200:
                models = response.json()['models']
                self.models_loaded.emit(models)
            else:
                self.error_occurred.emit(f"Unable to fetch models. Status code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            self.error_occurred.emit(f"Unable to connect to Ollama. Make sure it's running. Details: {e}")

class ModelNest(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ModelNest")
        self.setGeometry(100, 100, 800, 600)
        self.setWindowIcon(QIcon(r'C:\modelnest\modelnest-gui\logo_pack\logo.ico'))
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        self.create_ui()
        self.models = []
        self.selected_model = None
        
        self.load_thread = LoadModelsThread()
        self.load_thread.models_loaded.connect(self.on_models_loaded)
        self.load_thread.error_occurred.connect(self.show_error)
        
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_models)
        self.refresh_timer.start(30000)
        
        self.showMaximized()
        self.refresh_models()
    
    def create_ui(self):
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search models...")
        self.search_input.textChanged.connect(self.filter_models)
        search_layout.addWidget(self.search_input)
        
        self.question_button = QPushButton("?")
        self.question_button.setFixedSize(30, 30)
        self.question_button.clicked.connect(self.show_help_message)
        search_layout.addWidget(self.question_button)
        
        self.layout.addLayout(search_layout)
        
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["Model", "Size", "Parameters", "Format", "Quantization", "Modified", "Family"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.table.itemSelectionChanged.connect(self.handle_selection_change)
        self.layout.addWidget(self.table)
        
        self.loading_widget = QWidget()
        loading_layout = QVBoxLayout()
        self.loading_bar = QProgressBar()
        self.loading_bar.setRange(0, 0)  # Indeterminate progress
        loading_layout.addWidget(self.loading_bar)
        self.loading_label = QLabel("Loading models...")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_layout.addWidget(self.loading_label)
        self.loading_widget.setLayout(loading_layout)
        self.layout.addWidget(self.loading_widget)
        self.loading_widget.hide()
        
        button_layout = QHBoxLayout()
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_models)
        self.delete_button = QPushButton("Delete Model")
        self.delete_button.clicked.connect(self.delete_model)
        self.details_button = QPushButton("Model Details")
        self.details_button.clicked.connect(self.show_model_details)
        
        button_layout.addWidget(self.refresh_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addWidget(self.details_button)
        self.layout.addLayout(button_layout)
    
    def show_loading(self):
        self.table.hide()
        self.loading_widget.show()
    
    def hide_loading(self):
        self.loading_widget.hide()
        self.table.show()
    
    def refresh_models(self):
        self.selected_model = None
        self.table.clearSelection()
        self.show_loading()
        self.load_thread.start()
    
    def on_models_loaded(self, models):
        self.models = models
        self.populate_table()
        self.hide_loading()
    
    def show_error(self, message):
        self.hide_loading()
        QMessageBox.warning(self, "Error", message)
    
    def populate_table(self):
        self.table.setRowCount(0)
        for index, model in enumerate(self.models):
            self.table.insertRow(index)
            for col, value in enumerate([
                model.get('name', 'N/A'),
                self.format_size(model.get('size', 0)),
                str(model.get('details', {}).get('parameter_size', 'N/A')),
                model.get('details', {}).get('format', 'N/A'),
                model.get('details', {}).get('quantization_level', 'N/A'),
                self.format_date(model.get('modified_at', 'N/A')),
                model.get('details', {}).get('family', 'N/A')
            ]):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(index, col, item)
    
    def filter_models(self):
        search_text = self.search_input.text().lower()
        for row in range(self.table.rowCount()):
            row_hidden = True
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item and search_text in item.text().lower():
                    row_hidden = False
                    break
            self.table.setRowHidden(row, row_hidden)
    
    def delete_model(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select a model to delete.")
            return
        
        model_name = self.table.item(selected_rows[0].row(), 0).text()
        reply = QMessageBox.question(self, "Confirm Deletion", f"Are you sure you want to delete the model '{model_name}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            QMessageBox.information(self, "Deletion", f"Model '{model_name}' has been deleted.")
            self.refresh_models()
    
    def show_model_details(self):
        selected_items = self.table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select a model to view details.")
            return
        
        model_name = self.table.item(selected_items[0].row(), 0).text()
        model_data = next((m for m in self.models if m['name'] == model_name), None)
        
        if model_data:
            dialog = ModelDetailsDialog(model_data)
            dialog.exec()
        else:
            QMessageBox.warning(self, "Error", f"Could not find details for model '{model_name}'.")
    
    def show_context_menu(self, position):
        item = self.table.itemAt(position)
        if item is not None:
            menu = QMenu()
            copy_action = QAction("Copy", self)
            copy_action.triggered.connect(lambda: self.copy_cell_content(item))
            menu.addAction(copy_action)
            menu.exec(self.table.viewport().mapToGlobal(position))

    def copy_cell_content(self, item):
        if item:
            QApplication.clipboard().setText(item.text())
    
    @staticmethod
    def format_size(size_in_bytes):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_in_bytes < 1024.0:
                return f"{size_in_bytes:.2f} {unit}"
            size_in_bytes /= 1024.0
    
    @staticmethod
    def format_date(date_string):
        try:
            date = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S.%fZ")
            return date.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            return date_string

    def show_help_message(self):
        dialog = HelpDialog(self)
        dialog.exec()

    def handle_selection_change(self):
        selected_items = self.table.selectedItems()
        if selected_items:
            self.selected_model = self.table.item(selected_items[0].row(), 0).text()
        else:
            self.selected_model = None

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = ModelNest()
    window.show()
    sys.exit(app.exec())