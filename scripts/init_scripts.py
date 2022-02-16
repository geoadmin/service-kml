import os
import sys
from pathlib import Path

# Add the parent directory to the module search path to allow to import the
# app package.
sys.path.append(Path(__file__).absolute().parent.parent.as_posix())

# Sets the default environment file in order to import the app.settings package.
os.environ['ENV_FILE'] = '.env.default'
