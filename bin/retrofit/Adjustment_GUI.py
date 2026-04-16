import sys
import yaml
import subprocess
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLineEdit, QMessageBox,
                             QComboBox, QFormLayout)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QRect

class SettingsWindow(QWidget):
    def __init__(self, yaml_file, script_to_run):
        super().__init__()
        self.yaml_file = yaml_file
        self.script_to_run = script_to_run
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Settings')

        # Load YAML settings
        with open(self.yaml_file, 'r') as file:
            self.settings = yaml.safe_load(file)

        # Assume the materials are under a specific key, e.g., 'materials'
        # self.materials_key = '3_SIM'
        # self.materials = self.settings.get(self.materials_key, {})
        self.materials = self.settings['3_SIM']['BaseMaterial']

        # Layout
        vbox = QVBoxLayout()

        # Add Company Logo
        # logo_label = QLabel(self)
        # pixmap = QPixmap('pic.png')  # Replace with your logo file
        # logo_label.setPixmap(pixmap)
        # logo_label.setAlignment(Qt.AlignCenter)
        # vbox.addWidget(logo_label)

        # Material Selection
        self.material_select = QComboBox(self)
        self.material_select.addItems(self.materials.keys())
        self.material_select.currentTextChanged.connect(self.update_form)

        vbox.addWidget(QLabel("Select Material:"))
        vbox.addWidget(self.material_select)

        # Form Layout for key-value pairs
        self.form_layout = QFormLayout()
        self.key_value_inputs = {}
        vbox.addLayout(self.form_layout)

        # Save Button
        save_button = QPushButton('Save Settings As new_yml.yml')
        save_button.clicked.connect(self.save_settings_as)
        vbox.addWidget(save_button)

        # Run Button
        run_button = QPushButton('Run Script')
        run_button.clicked.connect(self.run_script)
        vbox.addWidget(run_button)

        self.setLayout(vbox)
        self.update_form()

    def center(self):
        """ Center the window on the screen """
        frame_gm = self.frameGeometry()
        screen = QApplication.desktop().screenNumber(QApplication.desktop().cursor().pos())
        center_point = QApplication.desktop().screenGeometry(screen).center()
        frame_gm.moveCenter(center_point)
        self.move(frame_gm.topLeft())

    def update_form(self):
        # Clear the form layout
        while self.form_layout.count():
            item = self.form_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Get the selected material's keys and values
        selected_material = self.material_select.currentText()
        material_data = self.materials.get(selected_material, {})

        # Populate the form layout with the key-value pairs
        self.key_value_inputs.clear()
        max_label_length = 0
        for key, value in material_data.items():
            line_edit = QLineEdit(str(value))
            label = f'{key}:'
            max_label_length = max(max_label_length, len(label))
            self.form_layout.addRow(label, line_edit)
            self.key_value_inputs[key] = line_edit

        # Adjust the window size to fit the new content
        self.adjustSize()

        # Adjust width based on the longest label in the form
        self.setFixedWidth(max(300, 100 + max_label_length * 7))  # 7 is an estimate of character width in pixels

        # Center the window on the screen after resizing
        self.center()

    def save_settings_as(self):
        # Get the selected material
        selected_material = self.material_select.currentText()

        # Update the material's data with the current form inputs
        for key, line_edit in self.key_value_inputs.items():
            value = line_edit.text()
            # Check if the value is numeric and convert it to an integer or float
            if value.isdigit():
                self.materials[selected_material][key] = int(value)
            else:
                try:
                    # Convert to float if possible
                    self.materials[selected_material][key] = float(value)
                except ValueError:
                    # Keep it as a string if it can't be converted
                    self.materials[selected_material][key] = value

        # Save the settings to the new YAML file named 'new_yml.yml'
        self.settings['3_SIM']['BaseMaterial'] = self.materials
        with open('../default/config/ECM.yml', 'w') as file:
            yaml.safe_dump(self.settings, file)

        QMessageBox.information(self, 'Settings Saved', 'Settings have been saved to ECM.yml')

    def run_script(self):
        # Run the external script
        try:
            # subprocess.run(['python', self.script_to_run], check=True)
            QMessageBox.information(self, 'Script Run', 'Script has been run successfully.')
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, 'Error', f'Error running script: {e}')
        finally:
            self.close()  # Close the window after the script runs


def GUISet(app=None):
    app = QApplication(sys.argv)
    yaml_file = '../default/config/DefaultConfig.yml'  # Path to your original YAML file
    script_to_run = 'mubes_run.py'  # Script you want to run
    settings = SettingsWindow(yaml_file, script_to_run)
    settings.show()
    app.exec_()


if __name__ == '__main__':
    GUISet()
