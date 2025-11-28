"""
This is a setup.py script generated for packaging the Episode Renamer app with py2app.
Usage:
    python setup.py py2app
"""

from setuptools import setup

APP = ['episode_renamer_app.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': False,  # Changed to False as it can cause issues
    'iconfile': 'app_icon.icns',  # You can replace this with your own icon
    'plist': {
        'CFBundleName': 'Episode Renamer',
        'CFBundleDisplayName': 'Episode Renamer',
        'CFBundleGetInfoString': 'Rename TV show episodes with ease',
        'CFBundleIdentifier': 'com.yourdomain.episoderenamer',
        'CFBundleVersion': '0.1.0',
        'CFBundleShortVersionString': '0.1.0',
        'NSHumanReadableCopyright': '© 2025',
        'NSPrincipalClass': 'NSApplication',
        'NSHighResolutionCapable': True,
    },
    'packages': ['PyQt6'],
    'includes': ['PyQt6.QtCore', 'PyQt6.QtWidgets', 'PyQt6.QtGui'],
    'excludes': ['tkinter', 'matplotlib', 'numpy', 'scipy'],
    'qt_plugins': ['platforms'],  # This is important for PyQt
}

setup(
    name='EpisodeRenamer',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)