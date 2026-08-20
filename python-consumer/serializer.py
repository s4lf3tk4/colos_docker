import numpy as np

def convert_to_serializable(obj):
    """сериализует размеры возвращаемые от yolo"""
    if isinstance(obj, (np.integer, np.int64)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float32, np.float64)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif hasattr(obj, 'content'):
        return obj.content
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
