import sys
import os
import json
import re
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QLineEdit, QPushButton, QFileDialog, QTableWidget, 
                            QTableWidgetItem, QMessageBox, QSpinBox, QHeaderView, QTabWidget,
                            QTextEdit, QProgressDialog, QComboBox, QCheckBox, QMenu, QGroupBox,
                            QDialog, QDialogButtonBox, QFormLayout, QPlainTextEdit, QSplitter,
                            QFrame)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QDateTime, QUrl
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QAction, QFont

# ============== LLM Integration ==============

class LLMDetector:
    """Handles communication with local Ollama LLM for filename parsing."""
    
    DEFAULT_MODEL = "qwen3:8b"  # Can be changed to any Ollama model
    OLLAMA_URL = "http://localhost:11434/api/generate"
    
    def __init__(self, model=None):
        self.model = model or self.DEFAULT_MODEL
        self.last_prompt = ""
        self.last_raw_response = ""
        self.last_duration_ms = 0
    
    def detect_show_info(self, filenames: list[str]) -> dict:
        """
        Send filenames to LLM and get structured show information.
        Returns: {show_name: str, season: str, start_episode: int, confidence: str, _log: dict}
        """
        import urllib.request
        import urllib.error
        import time
        
        prompt = self._build_prompt(filenames)
        self.last_prompt = prompt
        
        try:
            request_data = json.dumps({
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "format": "json"  # Request JSON response
            }).encode('utf-8')
            
            req = urllib.request.Request(
                self.OLLAMA_URL,
                data=request_data,
                headers={'Content-Type': 'application/json'}
            )
            
            start_time = time.time()
            with urllib.request.urlopen(req, timeout=60) as response:
                result = json.loads(response.read().decode('utf-8'))
            elapsed_ms = int((time.time() - start_time) * 1000)
            
            raw_response = result.get('response', '')
            self.last_raw_response = raw_response
            self.last_duration_ms = elapsed_ms
            
            parsed = self._parse_response(raw_response)
            
            # Add log information to result
            parsed['_log'] = {
                'prompt': prompt,
                'raw_response': raw_response,
                'duration_ms': elapsed_ms,
                'model': self.model,
                'filenames': filenames,
                'eval_count': result.get('eval_count', 0),
                'prompt_eval_count': result.get('prompt_eval_count', 0),
            }
            
            return parsed
                
        except urllib.error.URLError as e:
            return {"error": f"Cannot connect to Ollama. Is it running? ({e})", "_log": {"error": str(e)}}
        except Exception as e:
            return {"error": f"LLM detection failed: {str(e)}", "_log": {"error": str(e)}}
    
    def _build_prompt(self, filenames: list[str]) -> str:
        """Build the prompt for the LLM."""
        files_list = "\n".join(f"- {f}" for f in filenames[:20])  # Limit to 20 files
        
        return f"""Analyze these TV show episode filenames and extract the show information.

Filenames:
{files_list}

Based on these filenames, determine:
1. The TV show name (clean, proper title case)
2. The season identifier (e.g., "S1", "S01", "Season 1" -> normalize to "S1" format)
3. The starting episode number from this batch

Common filename patterns include:
- Show.Name.S01E01.Title.Quality.mkv
- Show_Name_1x01_Title.mkv
- Show Name - 101 - Title.mkv
- [Group] Show Name - 01.mkv

Respond with ONLY a JSON object in this exact format:
{{"show_name": "The Show Name", "season": "S1", "start_episode": 1, "confidence": "high"}}

Use "high" confidence if patterns are clear, "medium" if some guessing was needed, "low" if very uncertain.
If you cannot determine a field, use null for that field."""
        
    def _parse_response(self, response_text: str) -> dict:
        """Parse the LLM's JSON response."""
        try:
            # Try to extract JSON from response
            # Sometimes LLM might wrap it in markdown code blocks
            json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return {"error": "Could not parse LLM response as JSON"}
        except json.JSONDecodeError as e:
            return {"error": f"Invalid JSON from LLM: {e}"}

    @staticmethod
    def is_ollama_available() -> bool:
        """Check if Ollama is running and accessible."""
        import urllib.request
        import urllib.error
        
        try:
            req = urllib.request.Request("http://localhost:11434/api/tags")
            with urllib.request.urlopen(req, timeout=2) as response:
                return response.status == 200
        except:
            return False
    
    @staticmethod
    def get_available_models() -> list[str]:
        """Get list of models available in Ollama."""
        import urllib.request
        
        try:
            req = urllib.request.Request("http://localhost:11434/api/tags")
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))
                return [m['name'] for m in data.get('models', [])]
        except:
            return []


class LLMWorker(QThread):
    """Background thread for LLM detection to avoid UI freezing."""
    finished = pyqtSignal(dict)
    
    def __init__(self, filenames: list[str], model: str = None):
        super().__init__()
        self.filenames = filenames
        self.model = model
    
    def run(self):
        detector = LLMDetector(self.model)
        result = detector.detect_show_info(self.filenames)
        self.finished.emit(result)


class LLMSettingsDialog(QDialog):
    """Dialog for configuring LLM settings."""
    
    def __init__(self, parent=None, current_model=None):
        super().__init__(parent)
        self.setWindowTitle("LLM Settings")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        # Status
        status_label = QLabel()
        if LLMDetector.is_ollama_available():
            status_label.setText("✅ Ollama is running")
            status_label.setStyleSheet("color: green;")
        else:
            status_label.setText("❌ Ollama is not running. Start it with: ollama serve")
            status_label.setStyleSheet("color: red;")
        layout.addWidget(status_label)
        
        # Model selection
        form_layout = QFormLayout()
        self.model_combo = QComboBox()
        
        available_models = LLMDetector.get_available_models()
        if available_models:
            self.model_combo.addItems(available_models)
            if current_model and current_model in available_models:
                self.model_combo.setCurrentText(current_model)
        else:
            self.model_combo.addItem("(No models found)")
            self.model_combo.setEnabled(False)
        
        form_layout.addRow("Model:", self.model_combo)
        layout.addLayout(form_layout)
        
        # Help text
        help_text = QLabel(
            "Tip: For best results, use models like gemma3:12b, llama3.1:8b, or mistral.\n"
            "Install models with: ollama pull <model_name>"
        )
        help_text.setStyleSheet("color: gray; font-size: 11px;")
        help_text.setWordWrap(True)
        layout.addWidget(help_text)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def get_selected_model(self) -> str:
        return self.model_combo.currentText()


# ============== Main Application ==============

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
        self.setMinimumSize(900, 800)  # Larger default size for log panel
        
        # Instance variables
        self.directory_path = None
        self.preview_data = []
        self.recent_directories = []
        self.llm_model = LLMDetector.DEFAULT_MODEL
        
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
        
        # Set up menus
        self.setup_menus()
        
    def setup_menus(self):
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        
        # Recent directories submenu
        self.recent_menu = QMenu('Recent Directories', self)
        file_menu.addMenu(self.recent_menu)
        
        file_menu.addSeparator()
        exit_action = QAction('Exit', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Tools menu (for LLM settings)
        tools_menu = menubar.addMenu('Tools')
        
        llm_settings_action = QAction('LLM Settings...', self)
        llm_settings_action.triggered.connect(self.show_llm_settings)
        tools_menu.addAction(llm_settings_action)
        
        # Update the recent directories menu
        self.update_recent_menu()
    
    def show_llm_settings(self):
        dialog = LLMSettingsDialog(self, self.llm_model)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.llm_model = dialog.get_selected_model()
            self.statusBar().showMessage(f"LLM model set to: {self.llm_model}")
    
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
        if directory in self.recent_directories:
            self.recent_directories.remove(directory)
        self.recent_directories.insert(0, directory)
        
        if len(self.recent_directories) > 5:
            self.recent_directories = self.recent_directories[:5]
            
        self.update_recent_menu()
    
    def setup_rename_tab(self):
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
        
        # ===== LLM Auto-Detect Section =====
        llm_group = QGroupBox("🤖 AI Auto-Detect")
        llm_layout = QHBoxLayout(llm_group)
        
        self.auto_detect_button = QPushButton("Auto-Detect from Filenames")
        self.auto_detect_button.clicked.connect(self.auto_detect_show_info)
        self.auto_detect_button.setToolTip(
            "Uses a local LLM to analyze filenames and automatically fill in show details"
        )
        
        self.llm_status_label = QLabel("")
        self.llm_status_label.setStyleSheet("color: gray; font-style: italic;")
        
        # Toggle log button
        self.toggle_log_button = QPushButton("Show Log ▼")
        self.toggle_log_button.setCheckable(True)
        self.toggle_log_button.setMaximumWidth(100)
        self.toggle_log_button.clicked.connect(self.toggle_llm_log)
        
        llm_layout.addWidget(self.auto_detect_button)
        llm_layout.addWidget(self.llm_status_label)
        llm_layout.addStretch()
        llm_layout.addWidget(self.toggle_log_button)
        
        # ===== LLM Log Panel (collapsible) =====
        self.llm_log_frame = QFrame()
        self.llm_log_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.llm_log_frame.setVisible(False)  # Hidden by default
        
        log_layout = QVBoxLayout(self.llm_log_frame)
        log_layout.setContentsMargins(5, 5, 5, 5)
        
        # Log text area
        self.llm_log_text = QPlainTextEdit()
        self.llm_log_text.setReadOnly(True)
        self.llm_log_text.setMaximumHeight(150)  # Slightly smaller
        self.llm_log_text.setMinimumHeight(100)
        self.llm_log_text.setStyleSheet("""
            QPlainTextEdit {
                font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
                font-size: 11px;
                background-color: #1e1e1e;
                color: #d4d4d4;
            }
        """)
        self.llm_log_text.setPlaceholderText("LLM interaction logs will appear here...")
        
        # Clear log button
        clear_log_btn = QPushButton("Clear Log")
        clear_log_btn.setMaximumWidth(80)
        clear_log_btn.clicked.connect(lambda: self.llm_log_text.clear())
        
        log_header = QHBoxLayout()
        log_header.addWidget(QLabel("📋 LLM Interaction Log"))
        log_header.addStretch()
        log_header.addWidget(clear_log_btn)
        
        log_layout.addLayout(log_header)
        log_layout.addWidget(self.llm_log_text)
        
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
        self.preview_table.setMinimumHeight(200)  # Ensure table has reasonable height
        
        # Apply button
        apply_layout = QHBoxLayout()
        self.apply_button = QPushButton("Apply Renaming")
        self.apply_button.clicked.connect(self.apply_renaming)
        self.apply_button.setEnabled(False)
        apply_layout.addStretch()
        apply_layout.addWidget(self.apply_button)
        
        # Add all layouts to tab layout
        rename_layout.addLayout(dir_layout)
        rename_layout.addWidget(llm_group)  # Add the LLM section
        rename_layout.addWidget(self.llm_log_frame)  # Add the collapsible log panel
        rename_layout.addLayout(show_layout)
        rename_layout.addLayout(season_layout)
        rename_layout.addLayout(episode_layout)
        rename_layout.addLayout(pattern_layout)
        rename_layout.addLayout(custom_pattern_layout)
        rename_layout.addLayout(filter_layout)
        rename_layout.addLayout(preview_layout)
        rename_layout.addWidget(self.preview_table)
        rename_layout.addLayout(apply_layout)
    
    def auto_detect_show_info(self):
        """Use LLM to auto-detect show information from filenames."""
        if not self.directory_path:
            QMessageBox.warning(self, "No Directory", "Please select a directory first.")
            return
        
        # Check if Ollama is available
        if not LLMDetector.is_ollama_available():
            QMessageBox.warning(
                self, 
                "Ollama Not Available",
                "Cannot connect to Ollama. Please ensure:\n\n"
                "1. Ollama is installed (https://ollama.ai)\n"
                "2. Ollama is running (run 'ollama serve')\n"
                "3. You have a model installed (run 'ollama pull gemma3:12b')"
            )
            return
        
        # Get filenames from directory
        directory = Path(self.directory_path)
        try:
            filenames = [
                f.name for f in directory.iterdir()
                if f.is_file() 
                and not f.name.startswith('.')
                and f.name.lower().endswith(('.mkv', '.mp4', '.avi', '.ass', '.srt', '.sub'))
            ]
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not read directory: {e}")
            return
        
        if not filenames:
            QMessageBox.warning(self, "No Files", "No video or subtitle files found in directory.")
            return
        
        # Update UI to show detection in progress
        self.auto_detect_button.setEnabled(False)
        self.llm_status_label.setText("🔄 Analyzing filenames...")
        self.statusBar().showMessage("Running LLM detection...")
        
        # Log the start of detection
        self.log_llm_message(f"Starting detection with {len(filenames)} files...", "info")
        self.log_llm_message(f"Files: {', '.join(filenames[:5])}{'...' if len(filenames) > 5 else ''}", "info")
        
        # Run detection in background thread
        self.llm_worker = LLMWorker(filenames, self.llm_model)
        self.llm_worker.finished.connect(self.on_llm_detection_complete)
        self.llm_worker.start()
    
    def toggle_llm_log(self):
        """Toggle visibility of the LLM log panel."""
        is_visible = self.llm_log_frame.isVisible()
        self.llm_log_frame.setVisible(not is_visible)
        self.toggle_log_button.setText("Hide Log ▲" if not is_visible else "Show Log ▼")
    
    def log_llm_message(self, message: str, level: str = "info"):
        """Add a timestamped message to the LLM log."""
        timestamp = QDateTime.currentDateTime().toString("hh:mm:ss")
        level_colors = {
            "info": "#d4d4d4",
            "success": "#4ec9b0",
            "error": "#f14c4c",
            "prompt": "#ce9178",
            "response": "#9cdcfe"
        }
        color = level_colors.get(level, "#d4d4d4")
        
        # Format the message
        formatted = f"[{timestamp}] {message}"
        self.llm_log_text.appendPlainText(formatted)
        
        # Auto-scroll to bottom
        scrollbar = self.llm_log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def on_llm_detection_complete(self, result: dict):
        """Handle LLM detection results."""
        self.auto_detect_button.setEnabled(True)
        
        # Extract log info
        log_info = result.pop('_log', {})
        
        if "error" in result:
            self.llm_status_label.setText(f"❌ {result['error']}")
            self.statusBar().showMessage("LLM detection failed")
            self.log_llm_message(f"ERROR: {result['error']}", "error")
            return
        
        # Log the interaction details
        self.log_llm_message("=" * 50, "info")
        self.log_llm_message(f"Model: {log_info.get('model', 'unknown')}", "info")
        self.log_llm_message(f"Files analyzed: {len(log_info.get('filenames', []))}", "info")
        self.log_llm_message(f"Duration: {log_info.get('duration_ms', 0)}ms", "info")
        
        # Log token counts if available
        eval_count = log_info.get('eval_count', 0)
        prompt_eval = log_info.get('prompt_eval_count', 0)
        if eval_count or prompt_eval:
            self.log_llm_message(f"Tokens - Prompt: {prompt_eval}, Generated: {eval_count}", "info")
        
        self.log_llm_message("", "info")
        self.log_llm_message("─── PROMPT SENT ───", "prompt")
        for line in log_info.get('prompt', '').split('\n'):
            self.log_llm_message(line, "prompt")
        
        self.log_llm_message("", "info")
        self.log_llm_message("─── RAW RESPONSE ───", "response")
        self.log_llm_message(log_info.get('raw_response', ''), "response")
        
        self.log_llm_message("", "info")
        self.log_llm_message("─── PARSED RESULT ───", "success")
        self.log_llm_message(f"Show: {result.get('show_name', 'N/A')}", "success")
        self.log_llm_message(f"Season: {result.get('season', 'N/A')}", "success")
        self.log_llm_message(f"Start Episode: {result.get('start_episode', 'N/A')}", "success")
        self.log_llm_message(f"Confidence: {result.get('confidence', 'N/A')}", "success")
        self.log_llm_message("=" * 50, "info")
        
        # Fill in the form with detected values
        if result.get("show_name"):
            self.show_edit.setText(result["show_name"])
        
        if result.get("season"):
            self.season_edit.setText(result["season"])
        
        if result.get("start_episode"):
            try:
                self.episode_spin.setValue(int(result["start_episode"]))
            except (ValueError, TypeError):
                pass
        
        # Show confidence level
        confidence = result.get("confidence", "unknown")
        confidence_icons = {"high": "✅", "medium": "⚠️", "low": "❓"}
        icon = confidence_icons.get(confidence, "❓")
        
        duration_str = f" ({log_info.get('duration_ms', 0)}ms)"
        self.llm_status_label.setText(f"{icon} Detected (confidence: {confidence}){duration_str}")
        self.statusBar().showMessage(
            f"Auto-detected: {result.get('show_name', '?')} - {result.get('season', '?')} "
            f"starting at episode {result.get('start_episode', '?')}"
        )
    
    def on_pattern_changed(self, index):
        if self.pattern_combo.currentText() == "Custom...":
            self.custom_pattern.setEnabled(True)
        else:
            self.custom_pattern.setEnabled(False)
    
    def setup_restore_tab(self):
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
            
            self.add_to_recent(directory)
    
    def browse_directory(self):
        dialog = QFileDialog(self, "Select Directory")
        dialog.setFileMode(QFileDialog.FileMode.Directory)
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
        
        # Add common locations including external drives
        sidebar_urls = [
            QUrl.fromLocalFile(str(Path.home())),
            QUrl.fromLocalFile(str(Path.home() / "Desktop")),
            QUrl.fromLocalFile(str(Path.home() / "Downloads")),
            QUrl.fromLocalFile("/Volumes"),  # External drives on macOS
        ]
        dialog.setSidebarUrls(sidebar_urls)
        
        # Start in last used directory or home
        if self.directory_path:
            dialog.setDirectory(str(Path(self.directory_path).parent))
        else:
            dialog.setDirectory(str(Path.home()))
        
        if dialog.exec() == QFileDialog.DialogCode.Accepted:
            directory = dialog.selectedFiles()[0]
            self.directory_path = directory
            self.dir_edit.setText(directory)
            self.statusBar().showMessage(f"Selected directory: {directory}")
            self.add_to_recent(directory)
    
    def preview_renaming(self):
        if not self.validate_inputs():
            return
        
        directory = Path(self.directory_path)
        show_name = self.show_edit.text()
        season_num = self.season_edit.text()
        start_episode = self.episode_spin.value()
        
        pattern = self.pattern_combo.currentText()
        if pattern == "Custom...":
            pattern = self.custom_pattern.text()
            if not pattern:
                QMessageBox.warning(self, "Missing Pattern", "Please enter a custom naming pattern.")
                return
        
        self.preview_data = self.generate_preview(directory, show_name, season_num, start_episode, pattern)
        self.update_preview_table()
        self.apply_button.setEnabled(len(self.preview_data) > 0)
        
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
            
            self.statusBar().showMessage(f"Found {len(files)} video files and {len(subtitle_files)} subtitle files")
            
            for index, file in enumerate(files):
                extension = file.suffix
                episode_num = start_episode + index
                
                new_name = self.apply_naming_pattern(
                    pattern, 
                    show_name, 
                    season_num, 
                    str(episode_num).zfill(2), 
                    extension
                )
                
                preview_list.append((file, new_name))
            
            for index, subtitle_file in enumerate(subtitle_files):
                if index < len(files):
                    episode_num = start_episode + index
                    sub_extension = subtitle_file.suffix
                    
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
            result = pattern.replace("{show}", show)
            result = result.replace("{season}", season)
            result = result.replace("{episode}", episode)
            return f"{result}{extension}"
    
    def update_preview_table(self):
        self.preview_table.setRowCount(0)
        
        for i, (original_file, new_name) in enumerate(self.preview_data):
            self.preview_table.insertRow(i)
            self.preview_table.setItem(i, 0, QTableWidgetItem(original_file.name))
            self.preview_table.setItem(i, 1, QTableWidgetItem(new_name))
    
    def apply_renaming(self):
        if not self.preview_data:
            return
        
        confirm = QMessageBox.question(
            self, 
            "Confirm Renaming",
            f"Are you sure you want to rename {len(self.preview_data)} files?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.No:
            return
        
        self.progress_dialog = QProgressDialog("Renaming files...", "Cancel", 0, len(self.preview_data), self)
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.show()
        
        self.rename_worker = RenameWorker(self.preview_data, Path(self.directory_path))
        self.rename_worker.progress.connect(self.progress_dialog.setValue)
        self.rename_worker.finished.connect(self.on_rename_complete)
        
        self.apply_button.setEnabled(False)
        self.preview_button.setEnabled(False)
        self.statusBar().showMessage("Renaming files...")
        
        self.rename_worker.start()
    
    def on_rename_complete(self, backup, success_count, error_count):
        self.progress_dialog.close()
        
        self.apply_button.setEnabled(False)
        self.preview_button.setEnabled(True)
        
        QMessageBox.information(
            self, 
            "Renaming Complete",
            f"Successfully renamed {success_count} files.\n"
            f"Encountered {error_count} errors.\n"
            f"A backup of the original filenames has been saved to 'rename_backup.txt'."
        )
        
        self.preview_data = []
        self.update_preview_table()
        
        self.statusBar().showMessage(f"Renamed {success_count} files successfully, {error_count} errors")
    
    def browse_restore_directory(self):
        dialog = QFileDialog(self, "Select Directory with Backup File")
        dialog.setFileMode(QFileDialog.FileMode.Directory)
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
        
        # Add common locations including external drives
        sidebar_urls = [
            QUrl.fromLocalFile(str(Path.home())),
            QUrl.fromLocalFile(str(Path.home() / "Desktop")),
            QUrl.fromLocalFile(str(Path.home() / "Downloads")),
            QUrl.fromLocalFile("/Volumes"),  # External drives on macOS
        ]
        dialog.setSidebarUrls(sidebar_urls)
        dialog.setDirectory(str(Path.home()))
        
        if dialog.exec() == QFileDialog.DialogCode.Accepted:
            directory = dialog.selectedFiles()[0]
            self.restore_dir_edit.setText(directory)
            self.add_to_recent(directory)
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
        
        confirm = QMessageBox.question(
            self, 
            "Confirm Restoration",
            "Are you sure you want to restore files to their original names?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.No:
            return
        
        backup_file = Path(directory) / "rename_backup.txt"
        restore_map = {}
        
        try:
            with open(backup_file, "r") as f:
                for line in f:
                    if " -> " in line:
                        old_path_str, new_path_str = line.strip().split(" -> ")
                        try:
                            restore_map[new_path_str] = old_path_str
                        except Exception:
                            continue
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error reading backup file: {str(e)}")
            return
        
        if not restore_map:
            QMessageBox.warning(self, "No Files to Restore", "No valid file paths found in backup file.")
            return
        
        self.progress_dialog = QProgressDialog("Restoring files...", "Cancel", 0, len(restore_map), self)
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.show()
        
        self.restore_button.setEnabled(False)
        self.load_backup_button.setEnabled(False)
        
        restored_count = 0
        error_count = 0
        results = []
        
        try:
            for i, (new_path_str, old_path_str) in enumerate(restore_map.items()):
                self.progress_dialog.setValue(i)
                if self.progress_dialog.wasCanceled():
                    break
                    
                try:
                    new_path = Path(new_path_str)
                    old_path = Path(old_path_str)
                    
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
            self.progress_dialog.close()
            
            self.load_backup_button.setEnabled(True)
            
            result_text = "\n\n--- Restoration Results ---\n"
            result_text += "\n".join(results)
            result_text += f"\n\nRestoration complete! Restored {restored_count} files."
            result_text += f"\nEncountered {error_count} errors."
            self.backup_text.append(result_text)
            
            self.statusBar().showMessage(f"Restored {restored_count} files successfully, {error_count} errors")
        
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
