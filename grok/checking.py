import importlib.util
import sys
from pathlib import Path

# Add the function to import GA scripts
def import_script(script_path):
    """Import a Python script as a module and return it"""
    try:
        script_path = Path(script_path)
        if not script_path.exists():
            # Try common paths
            base_dir = Path("E:/data science tool")
            possible_paths = [
                base_dir / script_path.name,
                base_dir / "GA1" / script_path.name,
                base_dir / "GA2" / script_path.name,
                base_dir / "GA3" / script_path.name,
                base_dir / "GA4" / script_path.name,
                Path(str(script_path).replace("//", "/"))
            ]
            
            for path in possible_paths:
                if path.exists():
                    script_path = path
                    break
            else:
                raise FileNotFoundError(f"Script not found: {script_path}")
        
        # Get the absolute path
        script_path = script_path.resolve()
        
        # Create a module name (must be unique)
        module_name = f"dynamic_module_{script_path.stem}_{hash(str(script_path))}"
        
        # Create the spec
        spec = importlib.util.spec_from_file_location(module_name, script_path)
        if spec is None:
            raise ImportError(f"Could not create spec for {script_path}")
            
        # Create the module
        module = importlib.util.module_from_spec(spec)
        
        # Add to sys.modules
        sys.modules[module_name] = module
        
        # Execute the module
        spec.loader.exec_module(module)
        
        return module
    except Exception as e:
        print(f"Error importing script {script_path}: {e}")
        return None