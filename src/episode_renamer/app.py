"""
Episode Renamer Application
Optimized for fast startup - essential imports only
"""
import sys
import os
from pathlib import Path

# ===============================================================================
# PyQt6 Imports - All essential widgets loaded at startup
# Note: Lazy imports were removed as they caused crashes in signal handlers
# when running in PyInstaller bundles
# ===============================================================================
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QLineEdit, QPushButton, QTableWidget, 
                            QTableWidgetItem, QSpinBox, QHeaderView, QTabWidget,
                            QTextEdit, QComboBox, QCheckBox, QMenu,
                            QFileDialog, QMessageBox, QProgressDialog)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QAction


class RenameWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(dict, int, int)
    
    def __init__(self, preview_data, directory):
        super().__init__()
        self.preview_data = preview_data
        self.directory = directory
        
    def run(self):
        backup = {}
        success_count = 0
        error_count = 0
        
        for i, (original_file, new_name) in enumerate(self.preview_data):
            self.progress.emit(i)
            try:
                new_path = self.directory / new_name
                original_file.rename(new_path)
                backup[str(original_file)] = str(new_path)
                success_count += 1
            except Exception:
                error_count += 1
                
        try:
            with open(self.directory / "rename_backup.txt", "w") as f:
                for old, new in backup.items():
                    f.write(f"{old} -> {new}\n")
        except Exception:
            pass
            
        self.finished.emit(backup, success_count, error_count)


class EpisodeRenamerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Episode Manager")
        self.setMinimumSize(800, 600)
        
        # Instance variables
        self.directory_path = None
        self.preview_data = []
        self.recent_directories = []
        
        # Enable drag and drop
        self.setAcceptDrops(True)
        
        # Set up the UI
        self.setup_ui()
        
        # Initialize status bar
        self.statusBar().showMessage("Ready")
    
    def setup_ui(self):
        # Create central widget and main layout
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Create rename tab
        self.rename_tab = QWidget()
        self.setup_rename_tab()
        self.tab_widget.addTab(self.rename_tab, "Rename")
        
        # Create restore tab
        self.restore_tab = QWidget()
        self.setup_restore_tab()
        self.tab_widget.addTab(self.restore_tab, "Restore")
        
        # Add tab widget to main layout
        main_layout.addWidget(self.tab_widget)
        
        self.setCentralWidget(central_widget)
        
        # Set up the Recent Directories menu
        self.setup_recent_dirs_menu()
        
    def setup_recent_dirs_menu(self):
        # Create a menu bar if it doesn't exist
        menubar = self.menuBar()
        file_menu = menubar.addMenu('File')
        
        # Recent directories submenu
        self.recent_menu = QMenu('Recent Directories', self)
        file_menu.addMenu(self.recent_menu)
        
        # Separator and exit action
        file_menu.addSeparator()
        exit_action = QAction('Exit', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Update the recent directories menu
        self.update_recent_menu()
    
    def update_recent_menu(self):
        self.recent_menu.clear()
        for directory in self.recent_directories:
            action = QAction(directory, self)
            action.triggered.connect(lambda checked, d=directory: self.load_recent_directory(d))
            self.recent_menu.addAction(action)
        
        if not self.recent_directories:
            empty_action = QAction('(No recent directories)', self)
            empty_action.setEnabled(False)
            self.recent_menu.addAction(empty_action)
    
    def load_recent_directory(self, directory):
        # Handle loading recent directory based on active tab
        current_tab = self.tab_widget.currentIndex()
        if current_tab == 0:  # Rename tab
            self.directory_path = directory
            self.dir_edit.setText(directory)
        else:  # Restore tab
            self.restore_dir_edit.setText(directory)
            backup_file = Path(directory) / "rename_backup.txt"
            if backup_file.exists():
                self.load_backup_button.setEnabled(True)
            else:
                self.backup_text.setText("No backup file found in this directory.")
                self.load_backup_button.setEnabled(False)
                self.restore_button.setEnabled(False)
    
    def add_to_recent(self, directory):
        # Add directory to recent list
        if directory in self.recent_directories:
            self.recent_directories.remove(directory)
        self.recent_directories.insert(0, directory)
        
        # Keep only the last 5 directories
        if len(self.recent_directories) > 5:
            self.recent_directories = self.recent_directories[:5]
            
        # Update the menu
        self.update_recent_menu()
    
    def setup_rename_tab(self):
        # Set up the rename tab UI
        rename_layout = QVBoxLayout(self.rename_tab)
        
        # Directory selection
        dir_layout = QHBoxLayout()
        dir_label = QLabel("Directory:")
        self.dir_edit = QLineEdit()
        self.dir_edit.setReadOnly(True)
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self.browse_directory)
        
        dir_layout.addWidget(dir_label)
        dir_layout.addWidget(self.dir_edit)
        dir_layout.addWidget(browse_button)
        
        # Show name input
        show_layout = QHBoxLayout()
        show_label = QLabel("Show Name:")
        self.show_edit = QLineEdit()
        
        show_layout.addWidget(show_label)
        show_layout.addWidget(self.show_edit)
        
        # Season number input
        season_layout = QHBoxLayout()
        season_label = QLabel("Season (e.g. S1):")
        self.season_edit = QLineEdit()
        
        season_layout.addWidget(season_label)
        season_layout.addWidget(self.season_edit)
        
        # Starting episode input
        episode_layout = QHBoxLayout()
        episode_label = QLabel("Starting Episode:")
        self.episode_spin = QSpinBox()
        self.episode_spin.setMinimum(1)
        self.episode_spin.setMaximum(999)
        
        episode_layout.addWidget(episode_label)
        episode_layout.addWidget(self.episode_spin)
        
        # Naming pattern
        pattern_layout = QHBoxLayout()
        pattern_label = QLabel("Naming Pattern:")
        self.pattern_combo = QComboBox()
        self.pattern_combo.addItems([
            "{show} {season}E{episode}",
            "{show}.{season}x{episode}",
            "{show} - {season}{episode}",
            "Custom..."
        ])
        self.pattern_combo.currentIndexChanged.connect(self.on_pattern_changed)
        
        self.custom_pattern = QLineEdit()
        self.custom_pattern.setPlaceholderText("Custom pattern (use {show}, {season}, {episode})")
        self.custom_pattern.setEnabled(False)
        
        pattern_layout.addWidget(pattern_label)
        pattern_layout.addWidget(self.pattern_combo)
        
        custom_pattern_layout = QHBoxLayout()
        custom_pattern_layout.addWidget(self.custom_pattern)
        
        # Filter options
        filter_layout = QHBoxLayout()
        filter_label = QLabel("Include File Types:")
        self.video_filter = QCheckBox("Video (.mkv, .mp4, .avi)")
        self.video_filter.setChecked(True)
        self.subtitle_filter = QCheckBox("Subtitles (.ass, .srt, .sub)")
        self.subtitle_filter.setChecked(True)
        
        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(self.video_filter)
        filter_layout.addWidget(self.subtitle_filter)
        filter_layout.addStretch()
        
        # Preview button
        preview_layout = QHBoxLayout()
        self.preview_button = QPushButton("Preview Renaming")
        self.preview_button.clicked.connect(self.preview_renaming)
        preview_layout.addStretch()
        preview_layout.addWidget(self.preview_button)
        
        # Preview table
        self.preview_table = QTableWidget(0, 2)
        self.preview_table.setHorizontalHeaderLabels(["Original Filename", "New Filename"])
        self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        # Apply button
        apply_layout = QHBoxLayout()
        self.apply_button = QPushButton("Apply Renaming")
        self.apply_button.clicked.connect(self.apply_renaming)
        self.apply_button.setEnabled(False)
        apply_layout.addStretch()
        apply_layout.addWidget(self.apply_button)
        
        # Add all layouts to tab layout
        rename_layout.addLayout(dir_layout)
        rename_layout.addLayout(show_layout)
        rename_layout.addLayout(season_layout)
        rename_layout.addLayout(episode_layout)
        rename_layout.addLayout(pattern_layout)
        rename_layout.addLayout(custom_pattern_layout)
        rename_layout.addLayout(filter_layout)
        rename_layout.addLayout(preview_layout)
        rename_layout.addWidget(self.preview_table)
        rename_layout.addLayout(apply_layout)
    
    def on_pattern_changed(self, index):
        # Enable custom pattern field if "Custom..." is selected
        if self.pattern_combo.currentText() == "Custom...":
            self.custom_pattern.setEnabled(True)
        else:
            self.custom_pattern.setEnabled(False)
    
    def setup_restore_tab(self):
        # Set up the restore tab UI
        restore_layout = QVBoxLayout(self.restore_tab)
        
        # Directory selection for restoration
        dir_layout = QHBoxLayout()
        dir_label = QLabel("Directory with backup file:")
        self.restore_dir_edit = QLineEdit()
        self.restore_dir_edit.setReadOnly(True)
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self.browse_restore_directory)
        
        dir_layout.addWidget(dir_label)
        dir_layout.addWidget(self.restore_dir_edit)
        dir_layout.addWidget(browse_button)
        
        # Backup file display
        backup_layout = QVBoxLayout()
        backup_label = QLabel("Backup File Content:")
        self.backup_text = QTextEdit()
        self.backup_text.setReadOnly(True)
        
        backup_layout.addWidget(backup_label)
        backup_layout.addWidget(self.backup_text)
        
        # Restore button
        restore_button_layout = QHBoxLayout()
        self.load_backup_button = QPushButton("Load Backup File")
        self.load_backup_button.clicked.connect(self.load_backup_file)
        self.restore_button = QPushButton("Restore Original Filenames")
        self.restore_button.clicked.connect(self.restore_filenames)
        self.restore_button.setEnabled(False)
        
        restore_button_layout.addStretch()
        restore_button_layout.addWidget(self.load_backup_button)
        restore_button_layout.addWidget(self.restore_button)
        
        # Add layouts to restore tab
        restore_layout.addLayout(dir_layout)
        restore_layout.addLayout(backup_layout)
        restore_layout.addLayout(restore_button_layout)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls and urls[0].isLocalFile():
            directory = urls[0].toLocalFile()
            # Handle directory based on active tab
            current_tab = self.tab_widget.currentIndex()
            if current_tab == 0:  # Rename tab
                self.directory_path = directory
                self.dir_edit.setText(directory)
                self.statusBar().showMessage(f"Loaded directory: {directory}")
            else:  # Restore tab
                self.restore_dir_edit.setText(directory)
                backup_file = Path(directory) / "rename_backup.txt"
                if backup_file.exists():
                    self.load_backup_button.setEnabled(True)
                    self.statusBar().showMessage(f"Found backup file in: {directory}")
                else:
                    self.backup_text.setText("No backup file found in this directory.")
                    self.load_backup_button.setEnabled(False)
                    self.restore_button.setEnabled(False)
                    self.statusBar().showMessage(f"No backup file found in: {directory}")
            
            # Add to recent directories
            self.add_to_recent(directory)
    
    def browse_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Directory")
        if directory:
            self.directory_path = directory
            self.dir_edit.setText(directory)
            self.statusBar().showMessage(f"Selected directory: {directory}")
            self.add_to_recent(directory)
    
    def preview_renaming(self):
        
        if not self.validate_inputs():
            return
        
        # Get input values
        directory = Path(self.directory_path)
        show_name = self.show_edit.text()
        season_num = self.season_edit.text()
        start_episode = self.episode_spin.value()
        
        # Get pattern
        pattern = self.pattern_combo.currentText()
        if pattern == "Custom...":
            pattern = self.custom_pattern.text()
            if not pattern:
                QMessageBox.warning(self, "Missing Pattern", "Please enter a custom naming pattern.")
                return
        
        # Generate preview data
        self.preview_data = self.generate_preview(directory, show_name, season_num, start_episode, pattern)
        
        # Update table
        self.update_preview_table()
        
        # Enable apply button if we have preview data
        self.apply_button.setEnabled(len(self.preview_data) > 0)
        
        # Update status bar
        if len(self.preview_data) > 0:
            self.statusBar().showMessage(f"Preview generated: {len(self.preview_data)} files")
        else:
            self.statusBar().showMessage("No files found for renaming")
    
    def validate_inputs(self):
        
        if not self.directory_path:
            QMessageBox.warning(self, "Missing Directory", "Please select a directory.")
            return False
        
        if not self.show_edit.text():
            QMessageBox.warning(self, "Missing Show Name", "Please enter a show name.")
            return False
        
        if not self.season_edit.text():
            QMessageBox.warning(self, "Missing Season", "Please enter a season identifier (e.g. S1).")
            return False
        
        return True
    
    def generate_preview(self, directory, show_name, season_num, start_episode, pattern):
        preview_list = []
        
        try:
            # Get file lists based on filter checkboxes
            files = []
            if self.video_filter.isChecked():
                video_files = sorted([
                    f for f in directory.iterdir() 
                    if f.is_file() 
                    and not f.name.startswith('.')
                    and not f.name == 'rename_backup.txt'
                    and f.name.lower().endswith(('.mkv', '.mp4', '.avi'))
                ])
                files.extend(video_files)
            
            subtitle_files = []
            if self.subtitle_filter.isChecked():
                subtitle_files = sorted([
                    f for f in directory.iterdir()
                    if f.is_file()
                    and not f.name.startswith('.')
                    and f.name != 'rename_backup.txt'
                    and f.name.lower().endswith(('.ass', '.srt', '.sub'))
                ])
            
            # Update status bar with file count
            self.statusBar().showMessage(f"Found {len(files)} video files and {len(subtitle_files)} subtitle files")
            
            # Create preview list for video files
            for index, file in enumerate(files):
                # Get the file extension
                extension = file.suffix
                
                # Calculate the episode number
                episode_num = start_episode + index
                
                # Apply the selected pattern
                new_name = self.apply_naming_pattern(
                    pattern, 
                    show_name, 
                    season_num, 
                    str(episode_num).zfill(2), 
                    extension
                )
                
                # Add to preview list
                preview_list.append((file, new_name))
            
            # Add subtitle files to preview
            for index, subtitle_file in enumerate(subtitle_files):
                if index < len(files):  # Only if we have corresponding video files
                    episode_num = start_episode + index
                    
                    # Get subtitle extension
                    sub_extension = subtitle_file.suffix
                    
                    # Apply the selected pattern for subtitles
                    new_subtitle_name = self.apply_naming_pattern(
                        pattern, 
                        show_name, 
                        season_num, 
                        str(episode_num).zfill(2), 
                        sub_extension
                    )
                    
                    preview_list.append((subtitle_file, new_subtitle_name))
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error generating preview: {str(e)}")
        
        return preview_list
    
    def apply_naming_pattern(self, pattern, show, season, episode, extension):
        if pattern == "{show} {season}E{episode}":
            return f"{show} {season}E{episode}{extension}"
        elif pattern == "{show}.{season}x{episode}":
            return f"{show}.{season}x{episode}{extension}"
        elif pattern == "{show} - {season}{episode}":
            return f"{show} - {season}{episode}{extension}"
        else:
            # Custom pattern
            result = pattern.replace("{show}", show)
            result = result.replace("{season}", season)
            result = result.replace("{episode}", episode)
            return f"{result}{extension}"
    
    def update_preview_table(self):
        # Clear existing rows
        self.preview_table.setRowCount(0)
        
        # Add rows for preview data
        for i, (original_file, new_name) in enumerate(self.preview_data):
            self.preview_table.insertRow(i)
            self.preview_table.setItem(i, 0, QTableWidgetItem(original_file.name))
            self.preview_table.setItem(i, 1, QTableWidgetItem(new_name))
    
    def apply_renaming(self):
        
        if not self.preview_data:
            return
        
        # Confirm with user
        confirm = QMessageBox.question(
            self, 
            "Confirm Renaming",
            f"Are you sure you want to rename {len(self.preview_data)} files?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.No:
            return
        
        # Set up progress dialog
        self.progress_dialog = QProgressDialog("Renaming files...", "Cancel", 0, len(self.preview_data), self)
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.show()
        
        # Set up thread worker
        self.rename_worker = RenameWorker(self.preview_data, Path(self.directory_path))
        self.rename_worker.progress.connect(self.progress_dialog.setValue)
        self.rename_worker.finished.connect(self.on_rename_complete)
        
        # Disable UI while renaming
        self.apply_button.setEnabled(False)
        self.preview_button.setEnabled(False)
        self.statusBar().showMessage("Renaming files...")
        
        # Start the worker
        self.rename_worker.start()
    
    def on_rename_complete(self, backup, success_count, error_count):
        
        # Close the progress dialog first
        self.progress_dialog.close()
        
        # Re-enable UI
        self.apply_button.setEnabled(False)  # Keep disabled as preview data is now invalid
        self.preview_button.setEnabled(True)
        
        # Show results
        QMessageBox.information(
            self, 
            "Renaming Complete",
            f"Successfully renamed {success_count} files.\n"
            f"Encountered {error_count} errors.\n"
            f"A backup of the original filenames has been saved to 'rename_backup.txt'."
        )
        
        # Clear the preview data and update the table
        self.preview_data = []
        self.update_preview_table()
        
        # Update status bar
        self.statusBar().showMessage(f"Renamed {success_count} files successfully, {error_count} errors")
    
    def browse_restore_directory(self):
        
        directory = QFileDialog.getExistingDirectory(self, "Select Directory with Backup File")
        if directory:
            self.restore_dir_edit.setText(directory)
            self.add_to_recent(directory)
            # Check if backup file exists in this directory
            backup_file = Path(directory) / "rename_backup.txt"
            if backup_file.exists():
                self.load_backup_button.setEnabled(True)
                self.statusBar().showMessage(f"Found backup file in: {directory}")
            else:
                self.backup_text.setText("No backup file found in this directory.")
                self.load_backup_button.setEnabled(False)
                self.restore_button.setEnabled(False)
                self.statusBar().showMessage(f"No backup file found in: {directory}")
    
    def load_backup_file(self):
        
        directory = self.restore_dir_edit.text()
        if not directory:
            return
        
        backup_file = Path(directory) / "rename_backup.txt"
        if not backup_file.exists():
            self.backup_text.setText("Backup file not found!")
            return
        
        try:
            with open(backup_file, "r") as f:
                content = f.read()
                self.backup_text.setText(content)
                # Enable restore button if content is valid
                if " -> " in content:
                    self.restore_button.setEnabled(True)
                    self.statusBar().showMessage("Backup file loaded successfully")
                else:
                    self.backup_text.append("\nInvalid backup file format!")
                    self.restore_button.setEnabled(False)
                    self.statusBar().showMessage("Invalid backup file format")
        except Exception as e:
            self.backup_text.setText(f"Error reading backup file: {str(e)}")
            self.restore_button.setEnabled(False)
            self.statusBar().showMessage("Error reading backup file")
    
    def restore_filenames(self):
        
        directory = self.restore_dir_edit.text()
        if not directory:
            return
        
        # Confirm with user
        confirm = QMessageBox.question(
            self, 
            "Confirm Restoration",
            "Are you sure you want to restore files to their original names?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.No:
            return
        
        # Read the backup file and create restoration mapping
        backup_file = Path(directory) / "rename_backup.txt"
        restore_map = {}
        
        try:
            with open(backup_file, "r") as f:
                for line in f:
                    if " -> " in line:
                        old_path_str, new_path_str = line.strip().split(" -> ")
                        # Convert string paths to Path objects only after validating
                        try:
                            # Store as strings to avoid path parsing issues
                            restore_map[new_path_str] = old_path_str
                        except Exception:
                            # Skip invalid paths
                            continue
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error reading backup file: {str(e)}")
            return
        
        if not restore_map:
            QMessageBox.warning(self, "No Files to Restore", "No valid file paths found in backup file.")
            return
        
        # Set up progress dialog
        self.progress_dialog = QProgressDialog("Restoring files...", "Cancel", 0, len(restore_map), self)
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.show()
        
        # Disable UI while restoring
        self.restore_button.setEnabled(False)
        self.load_backup_button.setEnabled(False)
        
        # Perform direct restoration (no threading)
        restored_count = 0
        error_count = 0
        results = []
        
        try:
            # Process the files
            for i, (new_path_str, old_path_str) in enumerate(restore_map.items()):
                # Update progress
                self.progress_dialog.setValue(i)
                if self.progress_dialog.wasCanceled():
                    break
                    
                try:
                    # Create Path objects from strings
                    new_path = Path(new_path_str)
                    old_path = Path(old_path_str)
                    
                    # Only attempt rename if file exists
                    if new_path.exists():
                        new_path.rename(old_path)
                        results.append(f"Restored: {new_path.name} -> {old_path.name}")
                        restored_count += 1
                    else:
                        results.append(f"Skipped: {new_path.name} (file not found)")
                except Exception as e:
                    error_count += 1
                    results.append(f"Error: {os.path.basename(new_path_str)} - {str(e)}")
        finally:
            # Always close the progress dialog
            self.progress_dialog.close()
            
            # Re-enable buttons
            self.load_backup_button.setEnabled(True)
            # Keep restore button disabled
            
            # Update backup text with results
            result_text = "\n\n--- Restoration Results ---\n"
            result_text += "\n".join(results)
            result_text += f"\n\nRestoration complete! Restored {restored_count} files."
            result_text += f"\nEncountered {error_count} errors."
            self.backup_text.append(result_text)
            
            # Update status bar
            self.statusBar().showMessage(f"Restored {restored_count} files successfully, {error_count} errors")
        
        # Ask if user wants to delete the backup file
        if restored_count > 0:
            delete_confirm = QMessageBox.question(
                self,
                "Delete Backup",
                "Do you want to delete the backup file?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if delete_confirm == QMessageBox.StandardButton.Yes:
                try:
                    backup_file.unlink()
                    self.backup_text.append("\nBackup file deleted.")
                    self.restore_button.setEnabled(False)
                    self.statusBar().showMessage("Restoration complete, backup file deleted")
                except Exception as e:
                    self.backup_text.append(f"\nError deleting backup file: {str(e)}")
                    self.statusBar().showMessage("Error deleting backup file")


def main():
    app = QApplication(sys.argv)
    window = EpisodeRenamerApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()