import yaml


def read_yaml(file_path):
    """
    Reads a YAML file and returns its contents as a dictionary.

    This function will propagate exceptions like:
    - FileNotFoundError: If the file doesn't exist.
    - yaml.YAMLError: If the file is malformed.
    """
    with open(file_path, 'r') as file:
        try:
            config = yaml.safe_load(file)
            return config
        except yaml.YAMLError as exc:
            # Re-raise the exception to be handled by the calling script
            print(f"Error parsing YAML file: {file_path}")
            raise exc